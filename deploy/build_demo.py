"""Build the hosted-demo bundle (Streamlit Community Cloud, or a Docker host such as a Hugging Face Space) (demo mode: DuckDB + SQLite, no database server).

Run locally (needs your PostgreSQL with olist, olist_lab and indexed documents):
    python -m deploy.build_demo

Produces dist/hf_space/, ready to push to its own GitHub repo (Streamlit Cloud) or a Docker host:
    backend/ frontend/ data/demo/{rootcause_demo.duckdb, doc_chunks.npz} requirements.txt Dockerfile README.md
"""

import shutil
from pathlib import Path

import duckdb
import pandas as pd
from sqlalchemy import text

from backend.config import DATA_SCHEMA, LAB_SCHEMA, readonly_engine
from backend.rag.store import export_chunks

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "data" / "demo"
DIST = ROOT / "dist" / "hf_space"
TABLES = ["customers", "orders", "order_items", "order_payments", "order_reviews", "products", "sellers", "category_translation"]

SPACE_REQUIREMENTS = """pandas==2.3.3
SQLAlchemy==2.0.36
python-dotenv==1.0.1
PyYAML==6.0.3
litellm==1.102.1
langgraph==1.2.12
pydantic==2.13.5
sqlglot==30.19.0
rank-bm25==0.2.2
numpy==2.5.3
duckdb==1.5.5
streamlit==1.64.0
plotly==7.1.0
httpx==0.28.1
"""

DOCKERFILE = """FROM python:3.12-slim
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH ROOTCAUSE_DEMO=1 \\
    ROOTCAUSE_APP_DB=/tmp/rootcause_app.sqlite3 PYTHONUNBUFFERED=1
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
COPY --chown=user . .
EXPOSE 7860
CMD ["streamlit", "run", "frontend/app.py", "--server.port", "7860", "--server.address", "0.0.0.0", "--server.headless", "true"]
"""

SPACE_README = """# RootCause (live demo)

Ask why a metric changed. RootCause plans the investigation, runs validated read-only SQL, ranks the
segments that changed abnormally, checks for data bugs, pulls related incident documents, and cites
the query behind every number.

**Try:** "Why did the number of orders drop in April 2018 compared to March 2018?" on the *Olist lab*
dataset (real Olist e-commerce data with 5 planted problems whose causes are known).

Demo mode: data is a bundled read-only DuckDB file; the LLM is Gemini (free tier), so an investigation
takes 1-3 minutes. Source code, tests and benchmark: see the main RootCause repository.

## Deploy (Streamlit Community Cloud, free)
1. share.streamlit.io → Create app → this repository, branch `main`, main file `frontend/app.py`
2. Advanced settings → Python 3.12 → Secrets: `GEMINI_API_KEY = "..."`
3. Deploy. Demo mode switches on automatically (no database password, bundled DuckDB file present).

Data: Olist Brazilian E-Commerce Public Dataset (CC BY-NC-SA 4.0), with 5 documented planted anomalies in `olist_lab`.
"""


def build_duckdb() -> Path:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    path = DEMO_DIR / "rootcause_demo.duckdb"
    path.unlink(missing_ok=True)
    con = duckdb.connect(str(path))
    with readonly_engine().connect() as pg:
        for schema in (DATA_SCHEMA, LAB_SCHEMA):
            con.execute(f"CREATE SCHEMA {schema}")
            for table in TABLES:
                df = pd.read_sql(text(f"SELECT * FROM {schema}.{table}"), pg)
                con.register("tmp", df)
                con.execute(f"CREATE TABLE {schema}.{table} AS SELECT * FROM tmp")
                con.unregister("tmp")
            print(f"  {schema}: {con.execute(f'SELECT COUNT(*) FROM {schema}.orders').fetchone()[0]:,} orders")
    con.close()
    return path


def assemble() -> Path:
    if DIST.exists():
        shutil.rmtree(DIST)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for folder in ("backend", "frontend"):
        shutil.copytree(ROOT / folder, DIST / folder, ignore=ignore)
    shutil.copytree(DEMO_DIR, DIST / "data" / "demo", ignore=shutil.ignore_patterns("*.sqlite3"))
    (DIST / "requirements.txt").write_text(SPACE_REQUIREMENTS, encoding="utf-8")
    (DIST / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
    (DIST / "README.md").write_text(SPACE_README, encoding="utf-8")
    (DIST / ".gitignore").write_text("__pycache__/\n*.pyc\n*.sqlite3\n.env\n", encoding="utf-8")
    return DIST


def main() -> None:
    print("Building DuckDB demo database...")
    db = build_duckdb()
    print(f"  {db} ({db.stat().st_size / 1e6:.1f} MB)")
    n = export_chunks(DEMO_DIR / "doc_chunks.npz")
    print(f"Exported {n} document chunks")
    out = assemble()
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 1e6
    print(f"Space bundle ready: {out} ({size:.1f} MB)")


if __name__ == "__main__":
    main()
