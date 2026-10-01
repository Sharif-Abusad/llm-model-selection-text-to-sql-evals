# HARD-TIER golden dataset (20 questions) for the IPL 2021-2024 Text-to-SQL eval.
# A stress test - runs alongside the 30-question set for when models saturate it.
#
# Path A convention: "who/which" questions include name + value in gold; the
# evaluator tolerates name-only OR name+value.
#
# Internal gradient by number of COMPOUNDING traps:
#   hard    (1-2 traps)  : #1-8    - ratio OR null-filter OR threshold OR self-join
#   brutal  (3+ traps)   : #9-20   - ratios + null-handling + HAVING + subquery + domain
#
# Trap vocabulary (what separates models):
#   - NULL-sensitive filtering (extras_type IS NULL OR ... - the #22 killer)
#   - rates/ratios (strike rate, economy, average, %)
#   - HAVING thresholds (min balls / min innings)
#   - legal-ball counting (exclude wides/noballs correctly)
#   - wicket attribution (exclude run outs etc.)
#   - multi-level subqueries / CTEs
#   - self-referential team logic (team1/team2/winner)
#   - innings / phase logic (powerplay overs 0-5, death overs 15-19)

GOLDEN = [
 # ================= HARD (1-2 traps) =================
 dict(id=1, diff="hard",
   q="What is the average number of runs scored per match (total runs across all deliveries divided by number of matches)? Give a single number.",
   sql="""SELECT (SELECT SUM(total_runs) FROM deliveries) * 1.0 /
                 (SELECT COUNT(*) FROM matches) AS avg_runs_per_match"""),

 dict(id=2, diff="hard",
   q="Which batter has the highest boundary percentage - the share of their runs that came from fours and sixes - among batters with at least 500 total runs? Give the batter and the percentage.",
   sql="""SELECT batter,
                 100.0 * SUM(CASE WHEN batsman_runs IN (4,6) THEN batsman_runs ELSE 0 END)
                       / SUM(batsman_runs) AS boundary_pct
          FROM deliveries GROUP BY batter
          HAVING SUM(batsman_runs) >= 500
          ORDER BY boundary_pct DESC LIMIT 1"""),

 dict(id=3, diff="hard",
   q="How many players have scored at least 1000 total runs across these seasons?",
   sql="""SELECT COUNT(*) FROM (
             SELECT batter FROM deliveries GROUP BY batter
             HAVING SUM(batsman_runs) >= 1000) t"""),

 dict(id=4, diff="hard",
   q="Which bowler bowled the most legal deliveries (exclude wides and no-balls)? Give the bowler and the ball count.",
   sql="""SELECT bowler, COUNT(*) AS legal_balls FROM deliveries
          WHERE extras_type IS NULL OR extras_type NOT IN ('wides','noballs')
          GROUP BY bowler ORDER BY legal_balls DESC LIMIT 1"""),

 dict(id=5, diff="hard",
   q="What is the highest individual score by a batter in a single match? Give the batter and the runs.",
   sql="""SELECT batter, SUM(batsman_runs) AS match_runs
          FROM deliveries GROUP BY match_id, batter
          ORDER BY match_runs DESC LIMIT 1"""),

 dict(id=6, diff="hard",
   q="Which team has the most wins when batting second (i.e. the team that did NOT bat first won)? For each match the first-innings batting team is the batting_team in inning 1. Give the team and the wins.",
   sql="""SELECT m.winner AS team, COUNT(*) AS wins
          FROM matches m
          WHERE m.winner IS NOT NULL
            AND m.winner != (SELECT DISTINCT d.batting_team FROM deliveries d
                             WHERE d.match_id = m.id AND d.inning = 1)
          GROUP BY m.winner ORDER BY wins DESC LIMIT 1"""),

 dict(id=7, diff="hard",
   q="How many total runs were scored in the powerplay (overs 0 to 5 inclusive) across all matches?",
   sql="""SELECT SUM(total_runs) AS powerplay_runs
          FROM deliveries WHERE over BETWEEN 0 AND 5"""),

 dict(id=8, diff="hard",
   q="Which batter scored the most runs in the death overs (overs 15 to 19 inclusive)? Give the batter and the runs.",
   sql="""SELECT batter, SUM(batsman_runs) AS death_runs
          FROM deliveries WHERE over BETWEEN 15 AND 19
          GROUP BY batter ORDER BY death_runs DESC LIMIT 1"""),

 # ================= BRUTAL (3+ traps) =================
 dict(id=9, diff="brutal",
   q="Among batters with at least 300 runs, who has the highest strike rate? Strike rate = runs off the bat / legal balls faced * 100, where legal balls exclude wides. Give the batter and the strike rate.",
   sql="""SELECT batter, 100.0 * SUM(batsman_runs) /
                 SUM(CASE WHEN extras_type IS NULL OR extras_type != 'wides' THEN 1 ELSE 0 END) AS strike_rate
          FROM deliveries GROUP BY batter
          HAVING SUM(batsman_runs) >= 300
          ORDER BY strike_rate DESC LIMIT 1"""),

 dict(id=10, diff="brutal",
   q="Which bowler has the best economy rate (runs conceded per over of six legal balls) among bowlers who bowled at least 1000 legal balls? Legal balls exclude wides and no-balls. Give the bowler and the economy.",
   sql="""SELECT bowler, 6.0 * SUM(total_runs) /
                 SUM(CASE WHEN extras_type IS NULL OR extras_type NOT IN ('wides','noballs') THEN 1 ELSE 0 END) AS economy
          FROM deliveries GROUP BY bowler
          HAVING SUM(CASE WHEN extras_type IS NULL OR extras_type NOT IN ('wides','noballs') THEN 1 ELSE 0 END) >= 1000
          ORDER BY economy ASC LIMIT 1"""),

 dict(id=11, diff="brutal",
   q="Which bowler has the best bowling average (runs conceded per wicket) among bowlers with at least 30 wickets? A wicket excludes run outs, retired hurt, retired out, and obstructing the field. Give the bowler and the average.",
   sql="""SELECT bowler,
                 SUM(total_runs) * 1.0 /
                 SUM(CASE WHEN is_wicket = 1 AND dismissal_kind NOT IN
                     ('run out','retired hurt','retired out','obstructing the field') THEN 1 ELSE 0 END) AS bowl_avg
          FROM deliveries GROUP BY bowler
          HAVING SUM(CASE WHEN is_wicket = 1 AND dismissal_kind NOT IN
                     ('run out','retired hurt','retired out','obstructing the field') THEN 1 ELSE 0 END) >= 30
          ORDER BY bowl_avg ASC LIMIT 1"""),

 dict(id=12, diff="brutal",
   q="For each season, which team scored the most total runs? Give season, team, and runs, one row per season, ordered by season.",
   sql="""SELECT season, batting_team AS team, runs FROM (
             SELECT m.season, d.batting_team, SUM(d.total_runs) AS runs,
                    RANK() OVER (PARTITION BY m.season ORDER BY SUM(d.total_runs) DESC) AS rk
             FROM deliveries d JOIN matches m ON d.match_id = m.id
             GROUP BY m.season, d.batting_team) t
          WHERE rk = 1 ORDER BY season"""),

 dict(id=13, diff="brutal",
   q="Which batter has the highest average runs per match (total runs / matches they batted in) among batters who played at least 30 matches? Give the batter and the average.",
   sql="""SELECT batter, SUM(batsman_runs) * 1.0 / COUNT(DISTINCT match_id) AS avg_per_match
          FROM deliveries GROUP BY batter
          HAVING COUNT(DISTINCT match_id) >= 30
          ORDER BY avg_per_match DESC LIMIT 1"""),

 dict(id=14, diff="brutal",
   q="What is the highest successful run chase? Among matches won by the team batting second, find the largest second-innings total. Give the winning team and the runs.",
   sql="""SELECT m.winner AS team, t.runs FROM (
             SELECT match_id, SUM(total_runs) AS runs
             FROM deliveries WHERE inning = 2 GROUP BY match_id) t
          JOIN matches m ON t.match_id = m.id
          WHERE m.winner IS NOT NULL
            AND m.winner = (SELECT DISTINCT batting_team FROM deliveries
                            WHERE match_id = m.id AND inning = 2)
          ORDER BY t.runs DESC LIMIT 1"""),

 dict(id=15, diff="brutal",
   q="Which bowler took the most wickets in the death overs (overs 15 to 19 inclusive)? Wickets exclude run outs, retired hurt, retired out, obstructing the field. Give the bowler and the count.",
   sql="""SELECT bowler, COUNT(*) AS death_wickets FROM deliveries
          WHERE over BETWEEN 15 AND 19 AND is_wicket = 1
            AND dismissal_kind NOT IN ('run out','retired hurt','retired out','obstructing the field')
          GROUP BY bowler ORDER BY death_wickets DESC LIMIT 1"""),

 dict(id=16, diff="brutal",
   q="Which batter faced the most balls without ever being dismissed (i.e. balls where they were the batter and never appear as player_dismissed anywhere)? Give the batter and the balls faced. Consider only batters who never got out.",
   sql="""SELECT batter, COUNT(*) AS balls FROM deliveries
          WHERE batter NOT IN (SELECT DISTINCT player_dismissed FROM deliveries WHERE player_dismissed IS NOT NULL)
          GROUP BY batter ORDER BY balls DESC LIMIT 1"""),

 dict(id=17, diff="brutal",
   q="What percentage of all matches were won by the team that won the toss and chose to field? Give a single percentage of all matches.",
   sql="""SELECT 100.0 * SUM(CASE WHEN toss_decision = 'field' AND toss_winner = winner THEN 1 ELSE 0 END)
                 / COUNT(*) AS pct FROM matches"""),

 dict(id=18, diff="brutal",
   q="Which team had the highest win percentage in the 2023 season among teams that played at least 5 matches that season? Give the team and the win percentage.",
   sql="""SELECT team, 100.0 * SUM(won) / COUNT(*) AS win_pct FROM (
             SELECT m.id, t.team, CASE WHEN m.winner = t.team THEN 1 ELSE 0 END AS won
             FROM matches m
             JOIN (SELECT id, team1 AS team FROM matches WHERE season='2023'
                   UNION ALL SELECT id, team2 AS team FROM matches WHERE season='2023') t
               ON m.id = t.id
             WHERE m.season = '2023') x
          GROUP BY team HAVING COUNT(*) >= 5
          ORDER BY win_pct DESC LIMIT 1"""),

 dict(id=19, diff="brutal",
   q="Among bowler-batter pairs, which bowler dismissed a specific batter the most times (bowler-credited dismissals only)? Give the bowler, the batter, and the count.",
   sql="""SELECT bowler, player_dismissed AS batter, COUNT(*) AS times
          FROM deliveries
          WHERE is_wicket = 1 AND player_dismissed IS NOT NULL
            AND dismissal_kind NOT IN ('run out','retired hurt','retired out','obstructing the field')
          GROUP BY bowler, player_dismissed
          ORDER BY times DESC LIMIT 1"""),

 dict(id=20, diff="brutal",
   q="What is the average first-innings total in matches that were won by the team batting second (a successful chase)? Give a single number.",
   sql="""SELECT AVG(inn1.runs) AS avg_first_innings FROM (
             SELECT match_id, SUM(total_runs) AS runs FROM deliveries
             WHERE inning = 1 GROUP BY match_id) inn1
          JOIN matches m ON inn1.match_id = m.id
          WHERE m.winner IS NOT NULL
            AND m.winner = (SELECT DISTINCT batting_team FROM deliveries
                            WHERE match_id = m.id AND inning = 2)"""),
]

if __name__ == "__main__":
    import sqlite3
    DB = "ipl_2021_2024.db"
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    print(f"Validating {len(GOLDEN)} HARD golden queries against {DB}\n")
    ok = 0
    for g in GOLDEN:
        try:
            rows = cur.execute(g["sql"]).fetchall()
            preview = rows[0] if rows else "(empty)"
            print(f"[{g['diff']:6}] #{g['id']:2}  OK  rows={len(rows):<3} sample={str(preview)[:55]}")
            ok += 1
        except Exception as e:
            print(f"[{g['diff']:6}] #{g['id']:2}  FAIL  {e}")
    print(f"\n{ok}/{len(GOLDEN)} passed")
    from collections import Counter
    print("spread:", dict(Counter(g["diff"] for g in GOLDEN)))
    conn.close()