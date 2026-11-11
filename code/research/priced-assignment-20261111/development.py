"""Development only: all nine cells of November 10 blocks 0 and 1; old controls."""
import json
import math
from pathlib import Path
import method

def main():
    previous = method.ORIGINAL.parent
    destination = Path(__file__).resolve().parent / "development"
    destination.mkdir(exist_ok=True)
    method_sha = method.original.sha(Path(method.__file__))
    warmup_seconds = method.warmup()
    method.self_check()
    records = []
    for b in (0, 1):
        for profile in "ABC":
            for snr in (0, 10, 20):
                name = f"native-b{b:02d}-{profile}-snr{snr:02d}"
                case_path = previous/"cases"/(name+".json")
                case = json.loads(case_path.read_text())
                problem = method.original.Problem(case)
                starts = method.original.starts_for(problem, case["metadata"]["initialization_seed"])
                result = method.solve(problem, starts)
                result.update(case=name, case_sha256=method.original.sha(case_path), method_sha256=method_sha)
                method.original.dump(destination/(name+".json"), result)
                old = {arm: json.loads((previous/"runs/main"/f"{name}-{arm}.json").read_text())["se_bits"]
                       for arm in ("DP-SQP", "DP-Fu-SCA", "DP-Thu-IDE")}
                advantage = result["se_bits"]-max(old.values())
                headroom = result["numerical_upper_nats"]/(problem.s*math.log(2))-result["se_bits"]
                row = dict(case=name, se_bits=result["se_bits"], prior_se=old, gain_over_best_old=advantage,
                           search_seconds=result["elapsed_seconds"], counts=result["counts"],
                           numerical_headroom=headroom)
                records.append(row)
                print(f"{name}  delta={advantage:+.7f}  numeric_gap={headroom:.7f}  "
                      f"t={row['search_seconds']:.3f}s  priced={result['counts']['price_schedules']}", flush=True)
    method.original.dump(destination/"summary.json", dict(method_sha256=method_sha,
                         warmup_seconds=warmup_seconds, controls="November 10 archived timings", cases=records))

if __name__ == "__main__":
    main()

