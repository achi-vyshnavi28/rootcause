"""Low-fidelity wireframes as SVG (pasted into Figma as editable layers).

    python design/make_wireframes.py

01-02 show v1.2 as built; 03-04 are design proposals for the v1.3 backlog (RC-125, RC-126) drawn before building.
"""

from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).parent / "wireframes"
W, H = 1280, 800
INK, MUTED, LINE, FILL, ACCENT, BAD, OK = "#1c2330", "#6b7280", "#d0d5dd", "#f2f4f7", "#ff4b4b", "#b42318", "#1a7f4b"


class Frame:
    def __init__(self, title: str, user: str = "", height: int = H):
        self.h, self.title = height, title
        self.parts = [f'<rect width="{W}" height="{height}" fill="#ffffff"/>',
                      f'<rect width="300" height="{height}" fill="#f0f2f6"/>']
        self.text(330, 70, "RootCause", 34, weight=700)
        self.text(330, 98, "Ask why a metric changed. Every number links to the SQL that produced it.", 13, MUTED)
        for x, t in ((330, "Ask"), (380, "History"), (455, "Evals")):
            self.text(x, 135, t, 14, INK)
        if user:
            self.text(W - 24, 32, user, 13, MUTED, anchor="end")

    def text(self, x, y, s, size=14, color=INK, weight=400, anchor="start"):
        self.parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" '
                          f'text-anchor="{anchor}" font-family="Inter, Arial">{escape(s)}</text>')

    def box(self, x, y, w, h, fill=FILL, stroke=LINE, r=8):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>')

    def tab_underline(self, x, w):
        self.parts.append(f'<rect x="{x}" y="142" width="{w}" height="3" fill="{ACCENT}"/>')
        self.parts.append(f'<line x1="330" y1="146" x2="1250" y2="146" stroke="{LINE}"/>')

    def banner(self, y, text, good=True):
        self.box(330, y, 920, 44, "#e2f0d9" if good else "#fce4e4", OK if good else BAD, 6)
        self.text(348, y + 28, text, 14, OK if good else BAD, 600)

    def button(self, x, y, label, primary=True, w=None):
        w = w or 20 + 8 * len(label)
        self.box(x, y, w, 36, ACCENT if primary else "#fff", ACCENT if primary else LINE, 6)
        self.text(x + w / 2, y + 23, label, 14, "#fff" if primary else INK, 600, "middle")

    def table(self, x, y, cols, rows, widths, colors=None):
        self.box(x, y, sum(widths), 36 + 34 * len(rows), "#fff")
        cx = x
        for c, w in zip(cols, widths):
            self.text(cx + 10, y + 23, c, 12, MUTED, 600)
            cx += w
        for i, row in enumerate(rows):
            ry = y + 36 + 34 * i
            self.parts.append(f'<line x1="{x}" y1="{ry}" x2="{x + sum(widths)}" y2="{ry}" stroke="{LINE}"/>')
            cx = x
            for j, (cell, w) in enumerate(zip(row, widths)):
                self.text(cx + 10, ry + 22, cell, 12, (colors or {}).get((i, j), INK))
                cx += w

    def note(self, x, y, lines):
        self.box(x, y, 300, 26 + 20 * len(lines), "#fffbe6", "#f5c542", 6)
        for i, line in enumerate(lines):
            self.text(x + 12, y + 22 + 20 * i, line, 12, "#7a5c00")

    def sidebar(self, items):
        self.text(24, 60, "Dataset", 13, MUTED)
        self.box(24, 70, 250, 36, "#fff")
        self.text(36, 93, "Olist lab (planted anomalies)", 13)
        for i, t in enumerate(items):
            self.box(24, 140 + 60 * i, 250, 48, "#fff")
            self.text(36, 169 + 60 * i, t, 12)

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{self.h}" viewBox="0 0 {W} {self.h}">'
                f"<title>{escape(self.title)}</title>" + "".join(self.parts) + "</svg>")


RUNS = [["10:41", "Why did orders drop in April?", "olist_lab", "ok", "gemini-3.6-flash", "21.7"],
        ["10:12", "How many orders were canceled?", "olist", "ok", "gemini-3.6-flash", "14.1"],
        ["09:58", "Why did revenue jump in October?", "olist_lab", "ok", "gemini-3.6-flash", "48.2"]]


def history_intact():
    f = Frame("01 History: audit trail intact (v1.2, built)")
    f.sidebar(["Why did orders drop in April 2018?", "Why did revenue jump in Oct 2017?"])
    f.tab_underline(380, 58)
    f.banner(170, "✔ Audit trail intact: 67 hash-chained entries verified; every stored answer matches what was recorded.")
    f.table(330, 240, ["Time", "Question", "Dataset", "Status", "Model", "Seconds"], RUNS, [70, 340, 100, 80, 200, 80])
    f.note(950, 400, ["Runs on every visit: recomputes the", "SHA-256 chain AND re-reads each run.",
                      "Part 11 §11.10(e), ALCOA+ Original."])
    return f


def history_tampered():
    f = Frame("02 History: tampering detected (v1.2, built)")
    f.sidebar(["Why did orders drop in April 2018?", "Why did revenue jump in Oct 2017?"])
    f.tab_underline(380, 58)
    f.banner(170, "✖ Audit trail problem: 2 issue(s). Stored answers may have been changed outside the app.", good=False)
    f.table(330, 240, ["Entry", "Run", "Problem"],
            [["seq 41", "b5fb73fc…", "run or its queries changed after they were recorded"],
             ["–", "x-1", "run has no audit entry (inserted outside the app?)"]], [90, 160, 670],
            colors={(0, 2): BAD, (1, 2): BAD})
    f.table(330, 370, ["Time", "Question", "Dataset", "Status", "Model", "Seconds"], RUNS, [70, 340, 100, 80, 200, 80])
    f.note(950, 520, ["Names the exact run and what changed,", "so QA can open an investigation.",
                      "Tested: 7 tamper scenarios."])
    return f


def sign_in():
    f = Frame("03 RC-125 Sign-in and attributed answers (v1.3 proposal)", user="Signed in: Priya Nair · QA analyst · Log out")
    f.sidebar(["Why did the deviation rate rise in June?", "Why did batch yield drop in Q3?"])
    f.tab_underline(330, 30)
    f.text(330, 190, "Your question", 13, MUTED)
    f.box(330, 200, 920, 40, FILL)
    f.text(345, 226, "Why did the deviation rate rise in June compared to May?", 14)
    f.button(330, 256, "Investigate")
    f.text(330, 330, "Deviation rate 2.1% → 3.4% (+62%). Top candidate: Line 3, granulation step [Q2].", 15)
    f.box(330, 350, 920, 60, "#fff")
    f.text(345, 374, "Asked by Priya Nair (priya.nair@site) · 2026-10-02 09:14 UTC · model gemini-3.6-flash", 13, MUTED)
    f.text(345, 396, "Audit entry #212 · hash 9f3c…e1a0", 13, MUTED)
    f.note(950, 440, ["G1: every question is attributable to", "a signed-in person (ALCOA+).",
                      "No sign-in → 401, nothing stored."])
    return f


def review_report():
    f = Frame("04 RC-126 Monthly audit-trail review (v1.3 proposal)", user="Signed in: Arjun Rao · QA manager · Log out")
    f.sidebar(["Why did the deviation rate rise in June?"])
    f.tab_underline(380, 58)
    f.text(330, 190, "Audit-trail review: September 2026", 22, weight=700)
    f.table(330, 210, ["Check", "Result"],
            [["Entries verified", "212"], ["Chain intact", "Yes"], ["Runs changed after recording", "0"],
             ["Runs without an audit entry", "0"], ["Models used", "gemini-3.6-flash (212)"],
             ["Generated", "2026-10-01 06:00 UTC (scheduled)"]], [320, 600], colors={(1, 1): OK})
    f.button(330, 480, "Download PDF")
    f.button(480, 480, "File in QMS", primary=False)
    f.note(950, 530, ["G3: evidence for the periodic review", "our procedures require.",
                      "Problem found → owner emailed ≤ 15 min."])
    return f


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (history_intact(), history_tampered(), sign_in(), review_report()):
        name = f.title.split(" (")[0].replace(": ", "_").replace(" ", "_").lower()
        (OUT / f"{name}.svg").write_text(f.svg(), encoding="utf-8")
        print(OUT / f"{name}.svg")


if __name__ == "__main__":
    main()
