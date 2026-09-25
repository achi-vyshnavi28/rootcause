"""Build the Excel test & quality workbook (python docs/quality/build_workbook.py).

Sources are the files that are already the truth: test_cases.md, bug_reports.md, docs/gxp/, and the latest benchmark
report. Summary figures are live Excel formulas over the raw rows, cross-checked against the report's own summary.
"""

import json
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "quality" / "test_library_v1.2.xlsx"
GREEN, RED, GREY = (PatternFill("solid", fgColor=c) for c in ("E2F0D9", "FCE4E4", "EDEDED"))
BOLD = Font(bold=True)

# Last execution per test case, with the evidence. Only cases actually executed for v1.2 are marked.
RESULTS = {
    "TC01": ("Pass", "Benchmark rc01 (Hit@1)"), "TC02": ("Pass", "Benchmark rc04 (Hit@1)"),
    "TC03": ("Pass", "Benchmark rc13 (Hit@1)"), "TC04": ("Pass", "Playwright + Postman 05 (answer 625, cites Q1)"),
    "TC05": ("Pass", "Benchmark rf01"), "TC06": ("Pass", "Playwright: SQL with LIMIT shown in audit trail"),
    "TC07": ("Pass", "pytest tests/test_sql_validator.py"), "TC08": ("Not run in v1.2", ""),
    "TC09": ("Pass", "Postman 08-09 (invalid rating 422, valid saved)"), "TC10": ("Pass", "Playwright History tab"),
    "TC11": ("Pass", "Playwright Evals tab"), "TC12": ("Not run in v1.2", ""),
    "TC13": ("Pass", "pytest integrations (03)"), "TC14": ("Pass", "pytest integrations (08)"),
    "TC15": ("Not run in v1.2", ""), "TC16": ("Pass", "Playwright + Postman 12"),
    "TC17": ("Pass", "pytest tests/test_audit_log.py (edit, delete, insert, log rewrite)"),
    "TC18": ("Pass", "Postman 06, 11"), "TC19": ("Pass", "pytest + production DB: 64 runs baselined, intact"),
    "TC20": ("Pass", "Postman 13 (latest report meets thresholds)"),
}


def md_table(text: str, first_col: str) -> list[list[str]]:
    rows = [line for line in text.splitlines() if line.startswith(f"| {first_col}")]
    return [[c.strip().replace("`", "") for c in r.strip().strip("|").split("|")] for r in rows]


def sheet(wb, title, header, rows, widths, table=True):
    ws = wb.create_sheet(title)
    ws.append(header)
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    if table and rows:
        ref = f"A1:{get_column_letter(len(header))}{len(rows) + 1}"
        t = Table(displayName=re.sub(r"\W", "", title), ref=ref)
        t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(t)
    return ws


def color_status(ws, col: str, n: int) -> None:
    rng = f"{col}2:{col}{n + 1}"
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Pass"'], fill=GREEN))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Fail"'], fill=RED))
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT({col}2,3)="Not"'], fill=GREY))


def main() -> None:
    wb = Workbook()
    wb.remove(wb.active)

    sheet(wb, "Change log", ["Version", "Date", "Change"], [
        ["1.0", "2026-09-23", "15 manual/UAT cases (TC01-TC15) for the v1 agent"],
        ["1.2", "2026-09-25", "GxP readiness: TC16-TC20 (audit trail, tampering, model per answer, baselining, "
                              "model change control); 3 real bugs logged; results linked to Playwright, Postman, "
                              "pytest and benchmark evidence"],
    ], [9, 12, 100])

    cases = md_table((ROOT / "docs/quality/test_cases.md").read_text(encoding="utf-8"), "TC")
    rows = [c[:6] + list(RESULTS.get(c[0], ("Not run in v1.2", ""))) + ["2026-09-25" if RESULTS.get(c[0], ("",))[0] == "Pass" else ""]
            for c in cases]
    ws = sheet(wb, "Test cases", ["ID", "Title", "Preconditions", "Steps", "Expected result", "Automated by",
                                  "Result", "Evidence", "Executed on"], rows, [7, 26, 22, 45, 50, 30, 14, 40, 12])
    color_status(ws, "G", len(rows))

    gxp = md_table((ROOT / "docs/gxp/04_validation_approach_and_traceability.md").read_text(encoding="utf-8"), "GR")
    ws = sheet(wb, "Traceability", ["Requirement", "Text", "Risk", "Verified by", "Status"], gxp, [9, 55, 9, 60, 16])
    ws.conditional_formatting.add(f"E2:E{len(gxp) + 1}", FormulaRule(formula=['LEFT(E2,4)="Pass"'], fill=GREEN))
    ws.conditional_formatting.add(f"E2:E{len(gxp) + 1}", FormulaRule(formula=['ISNUMBER(SEARCH("Open",E2))'], fill=RED))

    risks = md_table((ROOT / "docs/gxp/02_risk_assessment.md").read_text(encoding="utf-8"), "R")
    risk_rows = [[r[0], r[1], r[2], int(r[3]), int(r[4]), int(r[5]), None, r[7], r[8]] for r in risks]
    ws = sheet(wb, "Risk register", ["#", "Hazard", "Effect", "S", "P", "D", "RPN", "Control", "Evidence"],
               risk_rows, [5, 30, 32, 5, 5, 5, 7, 45, 45])
    for i in range(2, len(risk_rows) + 2):
        ws[f"G{i}"] = f"=D{i}*E{i}*F{i}"
    ws.conditional_formatting.add(f"G2:G{len(risk_rows) + 1}",
                                  CellIsRule(operator="greaterThanOrEqual", formula=["12"], fill=RED))

    report = json.loads((ROOT / "evals/reports/latest.json").read_text(encoding="utf-8"))
    bench = [[r["id"], r["category"], r["status"],
              bool(r["hit_at_1"] if r["category"] == "root_cause" else r["correct"]),
              r.get("hit_at_3", ""), r["duration_s"], r["cost_usd"], r["llm_calls"], r["sql_errors"],
              r["unsupported_numbers"]] for r in report["results"]]
    n = len(bench) + 1
    ws = sheet(wb, "Benchmark", ["Question", "Category", "Status", "Pass", "Hit@3", "Seconds", "Cost USD", "LLM calls",
                                 "SQL errors", "Unsupported numbers"], bench, [10, 12, 14, 8, 8, 10, 10, 10, 10, 12])
    ws.conditional_formatting.add(f"D2:D{n}", CellIsRule(operator="equal", formula=["FALSE"], fill=RED))

    s = report["summary"]
    ws = wb.create_sheet("Benchmark summary")
    ws.append([f"Model: {report['model']}  ·  run finished {report['finished_at']}"])
    ws["A1"].font = BOLD
    ws.append(["Metric", "Formula over the raw rows", "Report says", "Match"])
    B = "Benchmark!"
    metrics = [
        ("SQL execution accuracy %", f'=100*COUNTIFS({B}B2:B{n},"sql",{B}D2:D{n},TRUE)/COUNTIF({B}B2:B{n},"sql")',
         s["sql_execution_accuracy_pct"]),
        ("Root-cause Hit@1 %", f'=100*COUNTIFS({B}B2:B{n},"root_cause",{B}D2:D{n},TRUE)/COUNTIF({B}B2:B{n},"root_cause")',
         s["root_cause_hit_at_1_pct"]),
        ("Root-cause Hit@3 %", f'=100*COUNTIFS({B}B2:B{n},"root_cause",{B}E2:E{n},TRUE)/COUNTIF({B}B2:B{n},"root_cause")',
         s["root_cause_hit_at_3_pct"]),
        ("Correct refusals %", f'=100*COUNTIFS({B}B2:B{n},"refusal",{B}D2:D{n},TRUE)/COUNTIF({B}B2:B{n},"refusal")',
         s["correct_refusal_pct"]),
        ("Answers with unsupported numbers %", f'=100*COUNTIF({B}J2:J{n},">0")/COUNTA({B}A2:A{n})',
         s["answers_with_unsupported_numbers_pct"]),
        ("Median latency (s)", f"=MEDIAN({B}F2:F{n})", s["median_latency_s"]),
        ("Average cost per question (USD)", f"=AVERAGE({B}G2:G{n})", s["avg_cost_usd"]),
        ("Questions", f"=COUNTA({B}A2:A{n})", s["questions"]),
    ]
    for i, (name, formula, reported) in enumerate(metrics, start=3):
        # the report rounds to 1-2 decimals, so allow rounding differences only
        ws.append([name, formula, reported, f"=IF(ABS(B{i}-C{i})<=0.05,\"yes\",\"CHECK\")"])
        ws[f"B{i}"].number_format = "0.00" if "USD" not in name else "0.000000"
    ws.append([])
    ws.append(["Model change control (docs/gxp/04): accept a new model only if all hold"])
    ws[f"A{ws.max_row}"].font = BOLD
    for name, cell, rule in [("SQL accuracy ≥ 95%", "B3", ">=95"), ("Hit@1 ≥ 85%", "B4", ">=85"),
                             ("Refusals = 100%", "B6", "=100"), ("Unsupported numbers ≤ 2%", "B7", "<=2")]:
        ws.append([name, f'=IF({cell}{rule},"meets","FAILS")'])
    for col, w in zip("ABCD", (38, 22, 14, 9)):
        ws.column_dimensions[col].width = w
    for c in ws[2]:
        c.font = BOLD

    bugs = re.findall(r"## (BUG-\d+): (.+?)\n.*?\| Severity \| (S\d)[^|]*\|.*?\*\*Status:\*\* (\w+)",
                      (ROOT / "docs/quality/bug_reports.md").read_text(encoding="utf-8"), re.S)
    sheet(wb, "Bugs", ["ID", "Title", "Severity", "Status"], [list(b) for b in bugs], [10, 70, 9, 10])

    wb.move_sheet("Benchmark summary", offset=-(len(wb.sheetnames) - 2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"{OUT.relative_to(ROOT)}: {len(rows)} test cases, {len(gxp)} requirements, {len(risk_rows)} risks, "
          f"{len(bench)} benchmark rows, {len(bugs)} bugs")


if __name__ == "__main__":
    main()
