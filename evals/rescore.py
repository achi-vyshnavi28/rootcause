"""Re-check saved SQL answers with the current scorer (no LLM calls).

Each SQL question's most recent run is looked up in the audit trail, its final executed query is
re-run on the read-only connection, and the result is compared with the gold answer(s).

    python -m evals.rescore
"""

import json
from pathlib import Path

import pandas as pd
import yaml
from sqlalchemy import text

from backend.config import APP_SCHEMA, admin_engine, readonly_engine
from evals.scoring import results_match

HERE = Path(__file__).parent
REPORT = HERE / "reports" / "latest.json"


def _frame(sql: str) -> pd.DataFrame:
    with readonly_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


def main() -> None:
    suite = {q["id"]: q for q in yaml.safe_load((HERE / "questions.yaml").read_text(encoding="utf-8"))["sql"]}
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    changed = []
    with admin_engine().connect() as conn:
        for row in report["results"]:
            if row["category"] != "sql" or row["status"] != "ok":
                continue
            item = suite[row["id"]]
            run_id = conn.execute(text(f"SELECT run_id FROM {APP_SCHEMA}.runs WHERE question = :q AND status = 'ok' "
                                       "ORDER BY created_at DESC LIMIT 1"), {"q": item["question"]}).scalar()
            sql = conn.execute(text(f"SELECT sql_executed FROM {APP_SCHEMA}.queries WHERE run_id = :r AND error IS NULL "
                                    "AND sql_executed IS NOT NULL ORDER BY query_id DESC LIMIT 1"), {"r": run_id}).scalar()
            got = _frame(sql)
            correct = any(results_match(_frame(g), got) for g in [item["gold"], *item.get("alt_gold", [])])
            if correct != row["correct"]:
                changed.append((row["id"], row["correct"], correct))
                row["correct"] = correct
    sql_rows = [r for r in report["results"] if r["category"] == "sql"]
    report["summary"]["sql_execution_accuracy_pct"] = round(100 * sum(r["correct"] for r in sql_rows) / len(sql_rows), 1)
    report["summary"]["rescored_with_scorer_fixes"] = True
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    for qid, before, after in changed:
        print(f"{qid}: {before} -> {after}")
    print("SQL execution accuracy:", report["summary"]["sql_execution_accuracy_pct"], "%")


if __name__ == "__main__":
    main()
