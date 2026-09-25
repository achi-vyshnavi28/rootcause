"""Model change-control gate: does a benchmark report meet the acceptance criteria? (docs/gxp/04)

    python -m evals.check_thresholds                      # checks evals/reports/latest.json
    python -m evals.check_thresholds path/to/report.json

Exit code 0 = accept, 1 = reject. The same thresholds are asserted by the Postman suite (request 13).
"""

import json
import sys
from pathlib import Path

REPORT = Path(__file__).resolve().parent / "reports" / "latest.json"
THRESHOLDS = [  # (summary key, comparison, limit, label)
    ("sql_execution_accuracy_pct", ">=", 95.0, "SQL execution accuracy"),
    ("root_cause_hit_at_1_pct", ">=", 85.0, "Root-cause Hit@1"),
    ("correct_refusal_pct", ">=", 100.0, "Correct refusals"),
    ("answers_with_unsupported_numbers_pct", "<=", 2.0, "Answers with unsupported numbers"),
]


def check(summary: dict) -> list[tuple[str, float, str, float, bool]]:
    rows = []
    for key, op, limit, label in THRESHOLDS:
        value = float(summary[key])
        rows.append((label, value, op, limit, value >= limit if op == ">=" else value <= limit))
    return rows


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPORT
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = check(report["summary"])
    print(f"Model {report['model']} · {report['summary']['questions']} questions · {report['finished_at']}")
    for label, value, op, limit, ok in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}: {value:g}% (must be {op} {limit:g}%)")
    accepted = all(r[-1] for r in rows)
    print("ACCEPT: model meets the change-control criteria" if accepted else "REJECT: do not switch to this model")
    return 0 if accepted else 1


if __name__ == "__main__":
    sys.exit(main())
