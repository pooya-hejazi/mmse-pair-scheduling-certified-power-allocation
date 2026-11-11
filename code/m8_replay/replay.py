"""Replay immutable scientific records for the 32 stored M=8 networks."""
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
from statistics import median
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CODE = HERE.parent
CERT = Path("research/manuscript-refinement-20261106/certification")
VENDOR = Path("output/TCOM-Submission-2026-11-06-R4/legacy-method/CR033/method/core/vendor")
OUTER = "output/TCOM-Submission-2026-11-06-R4/Supplementary_Materials.zip"
NESTED = "baseline_R1/Supplementary_Materials.zip"
FREEZE_HASH = "091def5fa532e48c536306e8e33f65dd80d3696e9ab7e3d9099e35aef7a36ee4"
OUTPUT_HASH = "9bbfd58577d3071128a15ccb27e77e2b1089eb872df1284d1f6923a5bdbe8d25"

def require(ok, message):
    if not ok:
        raise ValueError(message)

def checked(path, digest):
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == digest, f"SHA-256 mismatch: {path}")
    return raw

def read(path):
    return json.loads(path.read_bytes())

def bindings(code):
    """Derive the complete extraction allowlist from pinned manifests."""
    cert = code/CERT
    frozen = json.loads(checked(cert/"FROZEN.json", FREEZE_HASH))
    outputs = json.loads(checked(cert/"final/OUTPUT_MANIFEST.json", OUTPUT_HASH))
    require(outputs["freeze_sha256"] == FREEZE_HASH, "Freeze/outputs binding")
    for folder, records in [(cert, frozen["source_sha256"]), (cert/"final", outputs["files"]),
                            (code/VENDOR, frozen["vendor_sha256"])]:
        for name, digest in records.items():
            checked(folder/name, digest)
    inputs = read(cert/"INPUT_MANIFEST.json")
    require(len(inputs["cases"]) == len({r["name"] for r in inputs["cases"]}) == 32, "Case count")
    allowed = {}
    for case in inputs["cases"]:
        name, b = case["name"], case["binding"]
        require((b["outer_sha256"], b["nested_sha256"], b["nested_member"]) ==
                (inputs["outer_sha256"], inputs["nested_sha256"], NESTED), "Original archive binding")
        entries = []
        for field, filename in [("case","case.json"),("grid","grid-result.json"),("dual","grid-duals.json")]:
            member, digest = b[field+"_member"], b[field+"_file_sha256"]
            if member is None:
                require(field == "dual" and digest is None, "Missing bound member")
            else:
                entries.append(("nested", member, digest, filename))
        for h in case["history"]:
            entries.append((h["container"], h["member"], h["sha256"], h["file"]))
            if "input_member" in h:
                entries.append((h["container"], h["input_member"], h["input_sha256"], h["input_file"]))
        for container, member, digest, filename in entries:
            require(container in {"outer","nested"} and member.endswith(".json"), "Scientific JSON members only")
            require(Path(filename).name == filename, "Unsafe payload basename")
            item = dict(container=container, member=member, sha256=digest, file=f"inputs/corrected/{name}/{filename}")
            key = (container, member)
            require(allowed.setdefault(key,item) == item, "Repeated member binding differs")
    return inputs, allowed

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    cert = CODE/CERT
    inputs, allowed = bindings(CODE)
    manifest = read(HERE/"members.json")
    require(manifest["format"] == "m8-scientific-members-v1" and manifest["outer_member"] == OUTER and
            manifest["outer_sha256"] == inputs["outer_sha256"] and
            manifest["nested_sha256"] == inputs["nested_sha256"] and manifest["nested_member"] == NESTED,
            "Raw-member manifest provenance")
    records = {(item["container"],item["member"]):item for item in manifest["members"]}
    require(len(records)==len(manifest["members"]) and set(records)==set(allowed), "Raw-member inventory")
    for key,item in allowed.items():
        record = records[key]
        require({k:record[k] for k in item} == item, "Raw-member source/path binding")
        require(len(checked(cert/item["file"],item["sha256"]))==record["bytes"], "Raw-member length")
    def member(container,name):
        item = allowed[(container,name)]
        return json.loads(checked(cert/item["file"],item["sha256"]))

    sys.path.insert(0,str(cert))
    checker = load_module("frozen_m8_checker",cert/"checker.py")
    baseline = load_module("frozen_m8_baseline",CODE/VENDOR/"verify_upper.py")
    final = cert/"final"
    rows = read(final/"rows.json")
    results = {r["name"]:r for r in rows}
    require(len(rows)==len(results)==32 and set(results)=={r["name"] for r in inputs["cases"]},"Output population")
    counts = {"new":0, "baseline":0}
    reductions = []
    histories = 0
    for source in inputs["cases"]:
        name, b = source["name"], source["binding"]
        row = results[name]
        folder = final/name
        require(row==read(folder/"row.json") and b==row["binding"], name+" result row")
        case = member("nested",b["case_member"])
        anchor = member("nested",b["grid_member"])["schedule"]
        dual = member("nested",b["dual_member"]) if b["dual_member"] else None
        require(case["M"]==8 and case["name"]==name, name+" identity/dimension")
        for method in counts:
            fallback = folder/f"{method}-retained-fallback.json"
            witness = read(fallback if fallback.exists() else folder/f"{method}-witness.json")
            saved = read(folder/f"{method}-checked.json")
            if method=="new":
                receipt = checker.verify(case,witness,anchor,b,dual,seconds=None)
            else:
                baseline.clear_caches()
                receipt = baseline.verify(case,witness,seconds=None)
            for field in saved:
                if field.endswith("_nats"):
                    require(F(receipt[field])==F(saved[field]), f"{name} {method} {field}")
                elif field.endswith("_sha256") or field in {"valid","certificate_mathematical"}:
                    require(receipt[field]==saved[field], f"{name} {method} {field}")
            for field in ("lower_nats","upper_nats","gap_nats"):
                require(F(receipt[field])==F(row[method+"_"+field]),f"{name} {method} row endpoints")
            require(receipt["valid"],f"{name} {method}: independent verification failed")
            hit = F(receipt["gap_nats"]) <= F(1,100)
            require(hit==row[method+"_certificate"], f"{name} {method} target")
            counts[method] += hit
            if method=="new":
                require(F(row["anchor_lower_nats"])==F(receipt["anchor_lower_nats"]),name+" common lower bound")
        anchor_lower = F(row["anchor_lower_nats"])
        reductions.append(1-(F(row["new_upper_nats"])-anchor_lower)/(F(row["baseline_upper_nats"])-anchor_lower))
        model = checker.reconstruct(case)
        history = read(folder/"historical-checks.json")
        require(len(history)==len(source["history"]),name+" historical record count")
        for h,registered in zip(history,source["history"]):
            require(all(h[k]==v for k,v in registered.items()),name+" historical provenance")
            require(h["valid_schedule"],name+" invalid archived schedule")
            if "input_member" in h:
                other = member(h["container"],h["input_member"])
                require(other["channels_re"]==case["channels_re"] and other["channels_im"]==case["channels_im"]
                        and checker.reconstruct(other)==model,name+" historical physical input")
            schedule = member(h["container"],h["member"])["schedule"]
            lo,hi = checker.check_schedule(schedule,model)
            require(lo==F(h["checked_lower_nats"]) and hi==F(h["checked_upper_nats"]),name+" historical rate")
            histories += 1
    reduction = float(100*median(reductions))
    require(histories==84 and counts=={"new":27,"baseline":0} and round(reduction,2)==97.82,
            "Unexpected aggregate")
    print(json.dumps(dict(valid=True, cases=len(rows), checked_bound_witnesses=2*len(rows),
                          historical_schedules=histories, verified_raw_members=len(allowed),
                          gap_target_nats="1/100", cases_at_target=counts,
                          median_common_grid_gap_reduction_percent=reduction,
                          container_hash_validation="offline extraction; this replay verifies raw members",
                          verification_clock="unlimited independent replay, no optimizer invoked"), indent=2))

if __name__=="__main__":
    main()

