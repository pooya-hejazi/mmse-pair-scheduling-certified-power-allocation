"""Compare all audited allocations from the original search and computational repeat."""
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ARMS = ("Price-DP-SQP","DP-SQP","DP-Fu-SCA","DP-Thu-IDE")
BAND = 1e-5


def read(path):
    return json.loads(path.read_bytes())


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),
                                     ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def check(ok, message):
    if not ok:
        raise ValueError(message)


def write_rows(path, rows):
    with path.open("x",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def wtl(values):
    return dict(wins=sum(x>BAND for x in values),ties=sum(-BAND<=x<=BAND for x in values),
                losses=sum(x < -BAND for x in values))


def compare(original, fresh, lock, output):
    audits = [read(root/"audit_study.json") for root in (original,fresh)]
    analyses = [read(root/"analysis/results.json") for root in (original,fresh)]
    check(file_sha(original/"audit_study.json")==lock["original_audit_sha256"] and
          file_sha(original/"analysis/results.json")==lock["original_analysis_sha256"], "Original evidence hash changed")
    source_hash=lock["source_manifest_sha256"]
    for root,audit,results in zip((original,fresh),audits,analyses):
        check(audit["status"]=="PASS" and audit["final_allocations"]==720 and
              len(audit["runs_sha256"])==720 and results["n_allocations"]==720, "Incomplete independent audit")
        check(results["bootstrap_seed"]==lock["bootstrap_seed"] and results["bootstrap_draws"]==20000 and
              results["n_independent_blocks"]==20 and results["source_manifest_sha256"]==source_hash,
              "Bootstrap or source binding changed")
        check(results["audit_sha256"]==file_sha(root/"audit_study.json"),"Summary was not derived from the current audit")
        check(results["tie_band_bpshz"]==BAND and results["primary_margin_bpshz"]==.01 and
              results["secondary_floor_bpshz"]==-.001 and results["secondary_time_ratio_threshold"]==.5,
              "Changed decision boundaries")
    old_manifest=read(original/"runs/main/manifest.json")
    new_manifest=read(fresh/"runs/main/manifest.json")
    check(new_manifest==old_manifest and new_manifest["cases"]==lock["cases"],"Case, order, or stage manifest changed")
    records=[]
    endpoints=[]
    fresh_processes=set()
    old_processes=set()
    row_keys=("case","case_sha256","source_manifest_sha256","stage","block","profile","snr_db","initialization_seed",
              "search_seed","order","position","offered_start_ids","starts_sha256","cap_seconds","block_seconds")
    for i,(case_path,case_hash) in enumerate(new_manifest["cases"].items()):
        case=Path(case_path).stem
        starts=Path("runs/main")/(case+"-starts.json")
        check(file_sha(original/starts)==file_sha(fresh/starts), "Offered starts differ "+case)
        old_case={}
        new_case={}
        for arm in ARMS:
            relative=f"runs/main/{case}-{arm}.json"
            old,new=read(original/relative),read(fresh/relative)
            old_hash,new_hash=file_sha(original/relative),file_sha(fresh/relative)
            check(old_hash==audits[0]["runs_sha256"][relative] and new_hash==audits[1]["runs_sha256"][relative],
                  "Changed audited arm result "+relative)
            check(old_hash!=new_hash and old["process"]!=new["process"],"Prior run reused "+relative)
            check(all(old[k]==new[k] for k in row_keys) and new["case_sha256"]==case_hash,
                  "Case, starts, random stream or timing design changed "+relative)
            check(new["order"]==list(ARMS[i%4:]+ARMS[:i%4]),"Cyclic order changed "+case)
            old_processes.add(old["process"]);fresh_processes.add(new["process"])
            old_case[arm]=old;new_case[arm]=new
            records.append(dict(case=case,block=new["block"],profile=new["profile"],snr_db=new["snr_db"],arm=arm,
                case_sha256=case_hash,starts_sha256=new["starts_sha256"],initialization_seed=new["initialization_seed"],
                search_seed=new["search_seed"],order=" | ".join(new["order"]),position=new["position"],
                source_manifest_sha256=source_hash,original_process=old["process"],
                repeat_process=new["process"],original_se=old["se_bits"],repeat_se=new["se_bits"],
                delta_se=new["se_bits"]-old["se_bits"],original_seconds=old["elapsed_seconds"],repeat_seconds=new["elapsed_seconds"],
                delta_seconds=new["elapsed_seconds"]-old["elapsed_seconds"],original_status=old["status"],repeat_status=new["status"],
                original_history_length=len(old["history"]),repeat_history_length=len(new["history"]),
                original_allocation_sha256=object_sha(old["schedule"]),repeat_allocation_sha256=object_sha(new["schedule"]),
                original_history_sha256=object_sha(old["history"]),repeat_history_sha256=object_sha(new["history"]),
                original_record_sha256=old_hash,repeat_record_sha256=new_hash))
        def metrics(rows):
            return (rows[ARMS[0]]["se_bits"]-max(rows[a]["se_bits"] for a in ARMS[1:]),
                    math.log(rows[ARMS[0]]["elapsed_seconds"]/min(rows[a]["elapsed_seconds"] for a in ARMS[1:])))
        old_rate,old_log=metrics(old_case)
        new_rate,new_log=metrics(new_case)
        endpoints.append(dict(case=case,block=new["block"],profile=new["profile"],snr_db=new["snr_db"],
            original_rate=old_rate,repeat_rate=new_rate,delta_rate=new_rate-old_rate,
            original_log_time_ratio=old_log,repeat_log_time_ratio=new_log,delta_log_time_ratio=new_log-old_log))
    check(len(records)==720 and len(endpoints)==180 and not (old_processes&fresh_processes), "Invalid repeat coverage")
    process_files={p.stem for p in (fresh/"runs/processes").glob("*.json")}
    check(process_files==fresh_processes, "Unbound or missing fresh process")
    for proc in process_files:
        evidence=read(fresh/"runs/processes"/(proc+".json"))
        check(evidence["numba_threads"]==1 and all(p["num_threads"]==1 for p in evidence["thread_pools"]),
              "Warmup recorded a multi-thread numerical pool")
    arm_results={}
    for arm in ARMS:
        rows=[r for r in records if r["arm"]==arm]
        changes=[r["delta_se"] for r in rows]
        absolutes=list(map(abs,changes))
        times={}
        for key in ("original","repeat"):
            values=[r[key+"_seconds"] for r in rows]
            times[key]=dict(mean=statistics.mean(values),median=statistics.median(values))
        arm_results[arm]=dict(n=len(rows),mean_se_delta=statistics.mean(changes),
            median_abs_se_delta=statistics.median(absolutes),max_abs_se_delta=max(absolutes),
            max_abs_cases=[r["case"] for r in rows if abs(r["delta_se"])==max(absolutes)],
            count_abs_above_band=sum(d>BAND for d in absolutes),repeat_vs_original=wtl(changes),
            elapsed_seconds=times,exact_same_schedule_count=sum(r["original_allocation_sha256"]==r["repeat_allocation_sha256"] for r in rows))
    summary={"scope":"Computational sensitivity on the same 180 inputs, without added independent channel blocks",
             "source_commit":lock["commit"],"protocol_sha256":lock["protocol_sha256"],"cases":180,"allocations":720,
             "independent_blocks":20,"tie_tolerance_bpshz":BAND,"bootstrap_seed":lock["bootstrap_seed"],
             "processes":{"original":sorted(old_processes),"repeat":sorted(fresh_processes)},"arms":arm_results}
    for which,analysis,audit in zip(("original","repeat"),analyses,audits):
        entry={k:analysis[k] for k in ("primary_rate","secondary_rate","secondary_log_time_ratio","geometric_time_ratio","decisions")}
        entry["within_run_wtl"]={k:v["case_wtl"] for k,v in analysis["contrasts"].items()}
        entry["audit"]={k:audit[k] for k in ("final_allocations","retained_history_allocations","offered_starts_checked",
                                             "unique_schedules_evaluated","max_scalar_error_nats","max_matrix_error_nats")}
        summary[which]=entry
    summary["endpoint_differences"]={field:{k:analyses[1][field][k]-analyses[0][field][k]
                                          for k in ("mean","low","high")}
                                     for field in ("primary_rate","secondary_rate","secondary_log_time_ratio","geometric_time_ratio")}
    summary["decision_changed"]={k:analyses[0]["decisions"][k]!=v for k,v in analyses[1]["decisions"].items()}
    output.mkdir(parents=True,exist_ok=False)
    write_rows(output/"allocation_pairs.csv",records)
    write_rows(output/"case_endpoints.csv",endpoints)
    (output/"comparison.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return summary
