"""
Extract schema from the IPL 2021-2024 SQLite DB.
- Print extract CREATE TABLE statements (the text you'll paste into the prompt)
- Prints a clean column inventory per table
- Shows 3 sample rows per table so you can see real values
- SAVES the schema to disk (schema.sql) so the generation prompt can load it
- OPTIONAL: rename tables/colunms to a novel schema (contamination-avoidance)

Run against a DB you already built: ipl_2021_2024.db
"""

import sqlite3
import pandas as pd


DB_PATH = 'ipl_2021_2024.db'
SCHEMA_OUT = "schema.sql"   # <-- schema text written here, for the prompt

# ----- toggle this -----
RENAME = False   # set True to produce a renamed, "de-memorized" schema copy
RENAMED_DB_PATH = "ipl_eval.db"
RENAMED_SCHEMA_OUT = "schema_renamed.sql"


def get_create_statements(db_path):
    """
    Return a dict {table_name: CREATE TABLE text} for all user tables.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]

    ddls = {}

    for t in tables:
        ddl = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone()[0]
        ddls[t] = ddl
    conn.close()

    return ddls


def save_schema(db_path, out_path):
    """
    Write the exact CREATE TABLE statements to a file for the prompts.
    """
    ddls = get_create_statements(db_path)

    with open(out_path, "w", encoding="utf-8") as f:

        f.write("-- Schema for Text-to-SQL generation prompt\n")
        f.write(f"-- Source DB: {db_path}\n\n")

        for t, ddl in ddls.items():
            f.write(ddl.strip())
            f.write(";\n\n")   # terminate each statement cleanlyn

    print(f"Saved schema ({len(ddls)} tables) -> {out_path}")
    return out_path


def show_schema(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]

    print("=" * 70)
    print(f"SCHEMA FOR: {db_path}")
    print("=" * 70)

    for t in tables:
        ddl = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone()[0]

        print(f"\n--- CREATE statement: {t} ---")
        print(ddl)

        cols = cur.execute(f"PRAGMA table_info({t})").fetchall()
        print(f"\n--- Columns in {t} ({len(cols)}) ---")

        for c in cols:
            pk = "  <-- PK" if c[5] else ""
            print(f"  {c[1]:30s} {c[2] or 'TEXT':10s}{pk}")

        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"\n--- {t}: {n} rows | 3 samples ---")
        sample = pd.read_sql(f"SELECT * FROM {t} LIMIT 3", conn)

        with pd.option_context("display.max_columns", None,
                               "display.width", 200,
                               "display.max_colwidth", 25):
            print(sample.to_string(index=False))
        print()

    conn.close()


def make_renamed_copy(src_db, dst_db):
    """
    Create a renamed copy of the schema so models can't learn on the
    memorized Kaggle column names. Edit the maps below to taste.
    """
    table_rename = {
        "matches": "fixtures",
        "deliveries": "ball_events"
    }
    column_rename = {
        "matches": {
            "id": "fixture_id",
            "team1": "home_side",
            "team2": "away_side",
            "winner": "winning_side",
            "player_of_match": "top_performer", 
        },
        "deliveries": {
            "match_id": "fixture_id",
            "batter": "striker",
            "bowler": "bowling_player",
            "batsman_runs": "runs_off_bat",
            "total_runs": "runs_total",
        },
    }

    src = sqlite3.connect(src_db)
    tables = [r[0] for r in src.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]
    dst = sqlite3.connect(dst_db)

    for t in tables:
        df = pd.read_sql(f"SELECT * FROM {t}", src)
        cmap = column_rename.get(t, {})
        df = df.rename(columns={k: v for k, v in cmap.items() if k in df.columns})
        new_table = table_rename.get(t, t)
        df.to_sql(new_table, dst, if_exists="replace", index=False)

    cur = dst.cursor()
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_be_fixtures ON ball_events(fixtures_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fx_id ON fixtures(fixtures_id)")
    except sqlite3.OperationalError as e:
        print("Index note (adjust column names):", e)

    dst.commit()
    src.close()
    dst.close()

    print(f"\nWrote renamed copy -> {dst_db}")


if __name__ == '__main__':
    # Show original schema on screen
    show_schema(DB_PATH)
    # Save it to the disk for prompt
    save_schema(DB_PATH, SCHEMA_OUT)

    if RENAME:
        make_renamed_copy(DB_PATH, RENAMED_DB_PATH)
        print("\n" + "=" * 70)
        print("RENAMED SCHEMA")
        show_schema(RENAMED_DB_PATH)
        save_schema(RENAMED_SCHEMA_OUT)