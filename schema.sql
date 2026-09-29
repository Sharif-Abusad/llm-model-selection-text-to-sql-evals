-- Schema for Text-to-SQL generation prompt
-- Source DB: ipl_2021_2024.db

CREATE TABLE "matches" (
"id" INTEGER,
  "season" TEXT,
  "city" TEXT,
  "date" TIMESTAMP,
  "match_type" TEXT,
  "player_of_match" TEXT,
  "venue" TEXT,
  "team1" TEXT,
  "team2" TEXT,
  "toss_winner" TEXT,
  "toss_decision" TEXT,
  "winner" TEXT,
  "result" TEXT,
  "result_margin" REAL,
  "target_runs" REAL,
  "target_overs" REAL,
  "super_over" TEXT,
  "method" TEXT,
  "umpire1" TEXT,
  "umpire2" TEXT
);

CREATE TABLE "deliveries" (
"match_id" INTEGER,
  "inning" INTEGER,
  "batting_team" TEXT,
  "bowling_team" TEXT,
  "over" INTEGER,
  "ball" INTEGER,
  "batter" TEXT,
  "bowler" TEXT,
  "non_striker" TEXT,
  "batsman_runs" INTEGER,
  "extra_runs" INTEGER,
  "total_runs" INTEGER,
  "extras_type" TEXT,
  "is_wicket" INTEGER,
  "player_dismissed" TEXT,
  "dismissal_kind" TEXT,
  "fielder" TEXT
);

