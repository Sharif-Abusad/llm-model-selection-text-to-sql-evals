"""
main.py - controls the entire eval flow (ChatOpenRouter Version)

for each model:
    1. load the model (via OpenRouter, through ChatOpenRouter)
    2. run the golden dataset (generate SQL for each question)
    3. run the generated SQL on the DB (get a result)
    4. evaluate (compare to gold, using evaluator.py)
    5. log the score

Files it depends on:
    - schema.sql                (the schema, for the prompt)
    - golden_dataset.csv        (questions + gold_sql + order_sensitive)
    - model_openrouter_slug.py  (the 5 models under test -> MODELS)
    - evaluator.py              (the comparison logic)

Setup: 
    pip install langchain-openrouter python-dotenv pandas
    .env file with:  OPENROUTER_API_KEY=sk-or-...
"""

import os
import re
import json
import sqlite3
import logging
import pandas as pd

from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import SystemMessage, HumanMessage
from model_openrouter_slug import MODELS
from evaluator import evaluate_one
from dotenv import load_dotenv


# ---------- CONFIG ----------

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

DB_PATH = "ipl_2021_2024.db"
SCHEMA_PATH = "schema.sql"
GOLDEN_PATH = "golden_dataset.csv"
RESULTS_PATH = "eval_results.csv"
LOG_PATH = "eval.log"


# ---------- LOGGING ----------

# ---------- LOGGING ----------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Hide HTTP request logs from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------- helpers ----------

def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return f.read().strip()


def load_golden():
    return pd.read_csv(GOLDEN_PATH)


def make_llm(slug):
    """
    Create a ChatOpenRouter model for one OpenRouter slug.
    """
    return ChatOpenRouter(
        model=slug,
        openrouter_api_key=API_KEY,
        temperature=0,
        max_tokens=800
    )


def clean_sql(raw):
    """
    Strip markdown fences/prose, return runnable SQL.
    """
    if not raw:
        return ""

    text = raw.strip()

    fence = re.search(
        r"```(?:sql)?\s*(.*?)```",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if fence:
        text = fence.group(1).strip()

    text = re.sub(
        r"^\s*sql\s*\n?",
        "",
        text,
        flags=re.IGNORECASE
    )

    m = re.search(r"\b(SELECT|WITH)\b", text, re.IGNORECASE)

    if m:
        text = text[m.start():]

    return text.strip().strip("`").rstrip(";").strip("`").strip()


def generate_sql(question, schema, llm):
    """
    Ask one model for SQL via ChatOpenRouter.
    Returns cleaned SQL string.
    """

    system_msg = (
        "You are a text-to-SQL generator. Given a database schema and a question, "
        "return a single SQL query that answers it. Use SQLite syntax. "
        "Return only the SQL query."
    )

    user_msg = f"Schema:\n{schema}\n\nQuestion: {question}\n\nSQL:"

    response = llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content=user_msg)
    ])

    raw = response.content
    cleaned = clean_sql(raw)

    if not cleaned:
        logger.warning(
            "Model returned empty SQL. Raw response: %r",
            raw[:300] if raw else raw
        )

    return cleaned


def run_sql(conn, sql):
    """
    Run SQL on the DB.
    Returns a DataFrame, or None if it errored.
    """

    try:
        return pd.read_sql_query(sql, conn)

    except Exception as e:
        logger.error("SQL ERROR: %s", e)
        logger.error("SQL: %s", sql)

        return None


def gold_result_to_df(gold_result_json):
    """
    Rebuild the gold result DataFrame from the stored JSON.
    """

    obj = json.loads(gold_result_json)

    return pd.DataFrame(
        obj["rows"],
        columns=obj["columns"]
    )


# ---------- the main flow ----------

def run_eval():

    logger.info("=" * 60)
    logger.info("Starting Text-to-SQL evaluation")
    logger.info("=" * 60)

    schema = load_schema()
    golden = load_golden()

    logger.info("Loaded schema from: %s", SCHEMA_PATH)
    logger.info("Loaded golden dataset: %s", GOLDEN_PATH)
    logger.info("Total questions: %d", len(golden))

    conn = sqlite3.connect(DB_PATH)

    all_rows = []
    scoreboard = {}

    for name, slug in MODELS:

        logger.info("")
        logger.info("=" * 60)
        logger.info("MODEL: %s (%s)", name, slug)
        logger.info("=" * 60)

        llm = make_llm(slug)

        correct = 0

        for _, g in golden.iterrows():

            qid = g["id"]
            question = g["question"]

            order_sensitive = (
                str(g["order_sensitive"]).upper() == "TRUE"
            )

            gold_df = gold_result_to_df(
                g["gold_result_json"]
            )

            # ---------- 2. Generate SQL ----------

            try:

                sql = generate_sql(
                    question,
                    schema,
                    llm
                )

            except Exception as e:

                logger.error(
                    "#%s [%s] GEN-ERROR: %s",
                    qid,
                    g["difficulty"],
                    e
                )

                all_rows.append({
                    "model": name,
                    "id": qid,
                    "difficulty": g["difficulty"],
                    "correct": False,
                    "reason": "gen_error",
                    "sql": ""
                })

                continue

            # ---------- 3. Run SQL ----------

            gen_df = run_sql(
                conn,
                sql
            )

            # ---------- 4. Evaluate ----------

            verdict = evaluate_one(
                gold_df,
                gen_df,
                order_sensitive
            )

            if verdict["correct"]:
                correct += 1

                logger.info(
                    "#%s [%s] OK | %s",
                    qid,
                    g["difficulty"],
                    verdict["reason"]
                )

            else:

                logger.warning(
                    "#%s [%s] XX | %s",
                    qid,
                    g["difficulty"],
                    verdict["reason"]
                )

            all_rows.append({
                "model": name,
                "id": qid,
                "difficulty": g["difficulty"],
                "correct": verdict["correct"],
                "reason": verdict["reason"],
                "sql": sql
            })

        # ---------- Model score ----------

        total = len(golden)

        scoreboard[name] = correct

        percentage = (
            100 * correct / total
            if total > 0
            else 0
        )

        logger.info("")
        logger.info(
            "SCORE: %d/%d = %.1f%%",
            correct,
            total,
            percentage
        )

    conn.close()

    # ---------- 5. Final scoreboard ----------

    logger.info("")
    logger.info("=" * 60)
    logger.info("FINAL SCOREBOARD (execution accuracy)")
    logger.info("=" * 60)

    total = len(golden)

    for name, _ in MODELS:

        c = scoreboard[name]

        percentage = (
            100 * c / total
            if total > 0
            else 0
        )

        logger.info(
            "%-18s %2d/%d = %5.1f%%",
            name,
            c,
            total,
            percentage
        )

    # ---------- Save detailed results ----------

    pd.DataFrame(all_rows).to_csv(
        RESULTS_PATH,
        index=False
    )

    logger.info("")
    logger.info(
        "Detailed results saved -> %s",
        RESULTS_PATH
    )

    logger.info(
        "Evaluation log saved -> %s",
        LOG_PATH
    )


# ---------- Entry point ----------

if __name__ == "__main__":

    if not API_KEY:

        logger.error(
            "Missing OPENROUTER_API_KEY - add it to your .env file"
        )

    else:

        run_eval()