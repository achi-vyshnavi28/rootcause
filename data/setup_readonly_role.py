"""Create a read-only database user for the AI agent.

Even if the agent writes a harmful query (DELETE, DROP...), the database itself
will refuse it, because this user can only read the olist tables.

Run from the project root (after load_olist):
    python -m data.setup_readonly_role
"""

import os

from sqlalchemy import text

from backend.config import DATA_SCHEMA, admin_engine, readonly_engine


def setup() -> None:
    user = os.environ["READONLY_DB_USER"]
    password = os.environ["READONLY_DB_PASSWORD"]
    database = os.getenv("PGDATABASE", "rootcause")

    with admin_engine().begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :u"), {"u": user}).scalar()
        # Passwords can't be sent as query parameters in CREATE/ALTER ROLE, so quote them safely.
        quoted_password = conn.execute(text("SELECT quote_literal(:p)"), {"p": password}).scalar()
        action = "ALTER" if exists else "CREATE"
        conn.execute(text(f'{action} ROLE "{user}" WITH LOGIN PASSWORD {quoted_password}'))

        conn.execute(text(f'GRANT CONNECT ON DATABASE "{database}" TO "{user}"'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA {DATA_SCHEMA} TO "{user}"'))
        conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA {DATA_SCHEMA} TO "{user}"'))
        # Tables created later in this schema are readable too.
        conn.execute(
            text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA {DATA_SCHEMA} GRANT SELECT ON TABLES TO "{user}"')
        )
        # Extra safety: every session of this user starts in read-only mode, with a query time limit.
        conn.execute(text(f'ALTER ROLE "{user}" SET default_transaction_read_only = on'))
        conn.execute(text(f'ALTER ROLE "{user}" SET statement_timeout = \'15s\''))
    print(f"Read-only user '{user}' is ready.")

    # Prove it: reading works, writing is refused.
    with readonly_engine().connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {DATA_SCHEMA}.orders")).scalar()
        print(f"Read test passed: {count:,} orders visible.")
        try:
            conn.execute(text(f"DELETE FROM {DATA_SCHEMA}.orders"))
            print("WARNING: delete was allowed - check the role setup!")
        except Exception:
            print("Write test passed: DELETE was refused.")


if __name__ == "__main__":
    setup()
