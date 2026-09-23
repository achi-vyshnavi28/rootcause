"""3-scenario, 36-month financial model for a marketplace like Olist, as a live Excel workbook.

Starting point = Olist's actual last full month (orders, AOV) from the database. Every other cell is an
Excel formula, so assumptions can be edited in Excel and the model recalculates.

    python -m analytics.financial_model
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from analytics.product_analytics import unit_economics

OUTPUT = Path(__file__).parent / "output" / "marketplace_financial_model.xlsx"
MONTHS = 36
INPUT = PatternFill("solid", fgColor="FFF2CC")  # yellow = editable assumption
BOLD = Font(bold=True)

ASSUMPTIONS = [  # name, bear, base, bull, format
    ("Monthly order growth", 0.01, 0.03, 0.05, "0.0%"),
    ("Monthly AOV growth", 0.000, 0.002, 0.004, "0.0%"),
    ("Take rate (commission on GMV)", 0.10, 0.12, 0.14, "0.0%"),
    ("Payment + fraud cost (% of GMV)", 0.025, 0.022, 0.020, "0.0%"),
    ("Share of orders from new customers", 0.97, 0.95, 0.92, "0%"),
    ("CAC per new customer (BRL)", 45, 35, 28, "#,##0"),
    ("Fixed costs per month (BRL)", 450_000, 420_000, 400_000, "#,##0"),
    ("Fixed cost growth per month", 0.02, 0.015, 0.01, "0.0%"),
    ("Starting cash (BRL)", 15_000_000, 15_000_000, 15_000_000, "#,##0"),
]


def build(start_orders: float, start_aov: float, start_label: str) -> Path:
    wb = Workbook()
    a = wb.active
    a.title = "Assumptions"
    a["A1"], a["A1"].font = "Marketplace financial model (BRL)", Font(bold=True, size=14)
    a["A2"] = f"Starting point: Olist actuals for {start_label}. Yellow cells are editable."
    a["A4"], a["B4"] = "Selected scenario", "Base"
    a["B4"].fill, a["A4"].font = INPUT, BOLD
    dv = DataValidation(type="list", formula1='"Bear,Base,Bull"', allow_blank=False)
    a.add_data_validation(dv)
    dv.add("B4")
    a["A5"], a["B5"] = "Starting monthly orders", round(start_orders)
    a["A6"], a["B6"] = "Starting AOV (BRL)", round(start_aov, 2)
    for cell in ("B5", "B6"):
        a[cell].fill = INPUT
    for col, head in zip("ABCDE", ["Assumption", "Bear", "Base", "Bull", "Selected"]):
        a[f"{col}8"], a[f"{col}8"].font = head, BOLD
    for i, (name, bear, base, bull, fmt) in enumerate(ASSUMPTIONS, start=9):
        a[f"A{i}"] = name
        for col, v in zip("BCD", (bear, base, bull)):
            a[f"{col}{i}"], a[f"{col}{i}"].number_format, a[f"{col}{i}"].fill = v, fmt, INPUT
        a[f"E{i}"] = f'=INDEX(B{i}:D{i},MATCH($B$4,$B$8:$D$8,0))'
        a[f"E{i}"].number_format = fmt
    a.column_dimensions["A"].width = 38
    sel = {name: f"Assumptions!$E${i}" for i, (name, *_rest) in enumerate(ASSUMPTIONS, start=9)}

    m = wb.create_sheet("Model")
    headers = ["Month", "Orders", "AOV", "GMV", "Net revenue", "Payment costs", "New customers",
               "Marketing (CAC)", "Contribution", "Fixed costs", "EBITDA", "Cash (end)"]
    for c, h in enumerate(headers, start=1):
        m.cell(row=1, column=c, value=h).font = BOLD
    for r in range(2, MONTHS + 2):
        first = r == 2
        m[f"A{r}"] = r - 1
        m[f"B{r}"] = f"=Assumptions!$B$5*(1+{sel['Monthly order growth']})" if first else f"=B{r-1}*(1+{sel['Monthly order growth']})"
        m[f"C{r}"] = f"=Assumptions!$B$6*(1+{sel['Monthly AOV growth']})" if first else f"=C{r-1}*(1+{sel['Monthly AOV growth']})"
        m[f"D{r}"] = f"=B{r}*C{r}"
        m[f"E{r}"] = f"=D{r}*{sel['Take rate (commission on GMV)']}"
        m[f"F{r}"] = f"=D{r}*{sel['Payment + fraud cost (% of GMV)']}"
        m[f"G{r}"] = f"=B{r}*{sel['Share of orders from new customers']}"
        m[f"H{r}"] = f"=G{r}*{sel['CAC per new customer (BRL)']}"
        m[f"I{r}"] = f"=E{r}-F{r}-H{r}"
        m[f"J{r}"] = f"={sel['Fixed costs per month (BRL)']}" if first else f"=J{r-1}*(1+{sel['Fixed cost growth per month']})"
        m[f"K{r}"] = f"=I{r}-J{r}"
        m[f"L{r}"] = f"={sel['Starting cash (BRL)']}+K{r}" if first else f"=L{r-1}+K{r}"
        for col in "BCDEFGHIJKL":
            m[f"{col}{r}"].number_format = "#,##0"
    for col, w in zip("ABCDEFGHIJKL", [7, 10, 9, 14, 13, 13, 13, 14, 13, 13, 13, 15]):
        m.column_dimensions[col].width = w

    s = wb.create_sheet("Summary")
    last = MONTHS + 1
    rows = [
        ("Scenario", "=Assumptions!B4"),
        ("GMV, month 12", "=Model!D13"),
        ("GMV, month 36", f"=Model!D{last}"),
        ("Contribution margin, month 12", "=Model!I13/Model!E13"),
        ("First month with positive EBITDA", f'=IFERROR(INDEX(Model!A2:A{last},MATCH(TRUE,INDEX(Model!K2:K{last}>0,0),0)),"not within 36 months")'),
        ("Lowest cash balance", f"=MIN(Model!L2:L{last})"),
        ("Months of runway (cash > 0)", f"=COUNTIF(Model!L2:L{last},\">0\")"),
    ]
    for i, (label, formula) in enumerate(rows, start=1):
        s[f"A{i}"], s[f"B{i}"] = label, formula
        s[f"A{i}"].font = BOLD
        s[f"B{i}"].number_format = "0.0%" if "margin" in label else "#,##0"
    s.column_dimensions["A"].width = 36
    s.column_dimensions["B"].width = 22

    OUTPUT.parent.mkdir(exist_ok=True)
    wb.save(OUTPUT)
    return OUTPUT


def main() -> None:
    ue = unit_economics()
    last = ue.iloc[-1]
    print(f"Wrote {build(float(last['orders']), float(last['avg_order_value']), str(last['month']))}")


if __name__ == "__main__":
    main()
