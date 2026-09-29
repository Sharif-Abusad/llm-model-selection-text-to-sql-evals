"""
Build a SQLite DB of IPL 2021-24 from the Kaggle IPL complete dataset.
Expects matches.csv and deliveries.csv in the same folder.
Produces: ipl_2021_2024.db with two linked tables: matches, deliveries.
"""

import sqlite3
import pandas as pd


MATCHES_CSV = "data/matches.csv"
DELIVERIES_CSV = "data/deliveries.csv"
DB_PATH = "ipl_2021_2024.db"
YEARS = {2021, 2022, 2023, 2024}

# ---------- 1. Load matches ----------
matches = pd.read_csv(MATCHES_CSV)

# The 'season' column in this dataset is messy: some rows are "2021",
# others are like "2020/21" or "2009/10". Safest filter is the match DATE,
# not the season string. Parse date and extract the year.
matches["date"] = pd.to_datetime(matches["date"], errors="coerce", dayfirst=False)

# a few rows may fail to parse depending on format; try dayfirst as fallback
if matches["date"].isna().any():
    fallback = pd.to_datetime(
        matches.loc[matches["date"].isna(), "date"] if False else
        pd.read_csv(MATCHES_CSV)["date"],
        errors="coerce", dayfirst=True
    )
    matches["date"] = matches["date"].fillna(fallback)

matches["year"] = matches["date"].dt.year
matches_filtered = matches[matches["year"].isin(YEARS)].copy()

# The match identifier column is named 'id' in this dataset.
match_ids = set(matches_filtered["id"].unique())
print(f"Matches in 2021-2024: {len(matches_filtered)}")


# ---------- 2. Load deliveries, filter to those matches ----------
# deliveries.csv is large (~260k rows); read then filter on match_id.
deliveries = pd.read_csv(DELIVERIES_CSV)

# The FK column linking deliveries -> matches is 'match_id'
deliveries_filtered = deliveries[deliveries["match_id"].isin(match_ids)].copy()
print(f"Deliviries for those matches: {len(deliveries_filtered)}")


# ---------- 3. Write to SQLite ----------
conn = sqlite3.connect(DB_PATH)

# drop the helper 'year' column before saving if you want a clean schema
matches_to_save = matches_filtered.drop(columns=['year'])

matches_to_save.to_sql("matches", conn, if_exists="replace", index=False)
deliveries_filtered.to_sql("deliveries", conn, if_exists="replace", index=False)


# ---------- 4. Add indexes so JOINs/queries are fast ----------
cur = conn.cursor()
cur.execute("CREATE INDEX IF NOT EXISTS idx_deliveries_match ON deliveries(match_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_matches_id ON matches(id)")
conn.commit()


# ---------- 5. Sanity checks ----------
print("\n--- Verification ---")
print("matches rows:", cur.execute("SELECT COUNT(*) FROM matches").fetchone()[0])
print("deliveries rows:", cur.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0])

# confirm no orphan deliveries (every delivery links to a real match)
orphans = cur.execute("""
    SELECT COUNT(*) FROM deliveries d
    LEFT JOIN matches m 
        ON d.match_id = m.id
    WHERE m.id IS NULL
""").fetchone()[0]
print("orphan deliveries (should be 0):", orphans)

# show the season/year range actually captured
yr = cur.execute("""
    SELECT MIN(date), MAX(date) FROM matches
""").fetchone()
print("date range:", yr)

conn.close()
print(f"\nDone. Wrote {DB_PATH}")