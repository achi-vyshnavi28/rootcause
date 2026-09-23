"""Run the benchmark and write evals/reports/latest.json (+ a markdown summary).

    python -m evals.run_evals                  # all 50 questions
    python -m evals.run_evals --limit 5        # first 5 of each category (cheap smoke test)
    python -m evals.run_evals --only root_cause
    python -m evals.run_evals --baseline       # no self-correction (1 attempt) for comparison

Free-tier LLMs have rate limits; --pause adds a delay between questions.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml
from sqlalchemy import text

from backend import config
from backend.agent.runner import default_deps, run_question
from backend.config import DATA_SCHEMA, LAB_SCHEMA, readonly_engine
from evals.scoring import hit_rank, results_match

HERE = Path(__file__).parent
REPORTS = HERE / "reports"


def _gold(sql: str) -> pd.DataFrame:
    with readonly_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


def _agent_frame(result: dict) -> pd.DataFrame | None:
    ok = [q for q in result["queries"] if not q.get("error") and q.get("sql_executed")]
    if not ok:
        return None
    with readonly_engine().connect() as conn:  # re-run the agent's final query to get all rows, not just the preview
        return pd.read_sql(text(ok[-1]["sql_executed"]), conn)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", choices=["sql", "root_cause", "refusal"], default=None)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--pause", type=float, default=2.0)
    args = parser.parse_args()

    suite = yaml.safe_load((HERE / "questions.yaml").read_text(encoding="utf-8"))
    rows, total_cost, total_time = [], 0.0, 0.0

    for category in ("sql", "root_cause", "refusal"):
        if args.only and category != args.only:
            continue
        for item in suite[category][: args.limit]:
            deps = default_deps()
            if args.baseline:
                deps.max_retries = 1
            dataset = LAB_SCHEMA if category == "root_cause" else DATA_SCHEMA
            result = run_question(item["question"], dataset, deps, save=True)
            row = {"id": item["id"], "category": category, "status": result["status"],
                   "duration_s": result["duration_s"], "cost_usd": result["usage"]["cost_usd"],
                   "llm_calls": result["usage"]["calls"],
                   "sql_errors": sum(1 for q in result["queries"] if q.get("error")),
                   "unsupported_numbers": len((result["report"] or {}).get("unsupported_numbers", []))}
            if category == "sql":
                got = _agent_frame(result) if result["status"] == "ok" else None
                row["correct"] = bool(got is not None and results_match(_gold(item["gold"]), got))
            elif category == "root_cause":
                candidates = ((result["report"] or {}).get("evidence") or {}).get("top_candidates", [])
                rank = hit_rank(candidates, tuple(item["expected"]))
                row.update(rank=rank, hit_at_1=rank == 1, hit_at_3=rank is not None and rank <= 3)
            else:
                row["correct"] = result["status"] == "unanswerable"
            rows.append(row)
            total_cost += row["cost_usd"]
            total_time += row["duration_s"]
            print(f"{row['id']:<6} {row['status']:<22} " + ", ".join(f"{k}={row[k]}" for k in ("correct", "rank") if k in row))
            time.sleep(args.pause)

    df = pd.DataFrame(rows)

    def rate(cat: str, col: str) -> float | None:
        part = df[df["category"] == cat] if not df.empty else df
        return round(float(part[col].mean()) * 100, 1) if len(part) and col in part else None

    summary = {
        "sql_execution_accuracy_pct": rate("sql", "correct"),
        "root_cause_hit_at_1_pct": rate("root_cause", "hit_at_1"),
        "root_cause_hit_at_3_pct": rate("root_cause", "hit_at_3"),
        "correct_refusal_pct": rate("refusal", "correct"),
        "answers_with_unsupported_numbers_pct": round(float((df["unsupported_numbers"] > 0).mean()) * 100, 1) if len(df) else None,
        "avg_latency_s": round(total_time / len(df), 2) if len(df) else None,
        "avg_cost_usd": round(total_cost / len(df), 6) if len(df) else None,
        "questions": len(df),
        "mode": "baseline (no self-correction)" if args.baseline else "agent",
    }
    report = {"finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": config.LLM_MODEL,
              "summary": summary, "results": rows}
    REPORTS.mkdir(exist_ok=True)
    name = "baseline.json" if args.baseline else "latest.json"
    (REPORTS / name).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("\n" + "\n".join(f"{k:<40} {v}" for k, v in summary.items()))


if __name__ == "__main__":
    main()
