<div align="center">

# 🏏 Custom Model Evals: Text-to-SQL for IPL (Cricinfo-style "Ask" feature)

### A custom evaluation pipeline to choose the best LLM for an IPL cricket "Ask" feature

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![OpenRouter](https://img.shields.io/badge/LLM%20Gateway-OpenRouter-6467F2)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Methodology](#-methodology)
- [Results](#-results)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Usage](#-usage)
- [How the Evaluation Works](#-how-the-evaluation-works)
- [Extending the Project](#-extending-the-project)
- [Future Improvements](#-future-improvements)
- [Acknowledgements](#-acknowledgements)
- [License](#-license)
- [Author](#-author)

---

## 🎯 Overview

Picking an LLM because it is "the top model right now" is not an engineering decision. This project demonstrates a repeatable, data-driven way to choose a model for **your own** application.

**Scenario:** You are an AI engineer at a Cricinfo-style website. Fans type cricket questions in plain English (for example, *"Who has the best economy rate among bowlers with at least 500 legal balls?"*). An LLM converts each question into a SQL query, the query runs on the IPL database, and the result is shown to the user.

**Goal:** Select the single best LLM to power this text-to-SQL system under real-world constraints on cost, latency and correctness.

---

## ✨ Key Features

- **Requirement-driven selection:** cost ceiling, latency, context, deployment and correctness defined before any model is tested
- **Leaderboard shortlisting:** cost filtering plus a weighted score (coding ability and speed) to narrow 146 models down to a candidate list
- **Custom golden dataset:** hand-verified question and SQL pairs covering hard analytical queries
- **Execution-based evaluation:** compares result tables rather than SQL strings, so semantically correct queries are not penalized
- **Multi-model support:** one codebase evaluates any model available on OpenRouter
- **Reproducible runs:** per-question results and logs saved to disk

---

## 🧠 Methodology

The project follows a three-step framework:

| Step | Stage | Description | Output |
|:---:|-------|-------------|--------|
| 1 | **Requirements** | Define task, budget, latency, context, deployment and correctness needs | Requirement sheet |
| 2 | **Shortlisting** | Use public leaderboards to filter by cost and capability | 5-10 candidate models |
| 3 | **Custom Evaluation** | Run candidates on a domain-specific golden dataset | Winning model |

### 📋 Step 1: Requirements

| Requirement | Decision |
|-------------|----------|
| Task | Text-to-SQL (SQLite dialect, IPL domain) |
| Monthly cost ceiling | ₹3 lakh |
| Latency target | 2-3 seconds per answer |
| Context window | Not critical (single-turn, no chat history) |
| Deployment | Public APIs acceptable (no privacy constraint) |
| Correctness | Critical, since cricket fans scrutinize every statistic |

**Cost model (token-based pricing):**

- About 400 input tokens (system prompt, schema, question) and 100 output tokens per query, a 4:1 ratio
- Assumed volume of about 50,000 queries per day, over 30 days, at ₹95 per USD
- Example: a frontier model priced at $10 / $50 per million input / output tokens costs roughly ₹12.8 lakh per month, far above budget
- **Prompt caching** can reduce cost significantly because the system prompt and schema are identical for every request

### 🔎 Step 2: Shortlisting

Dedicated text-to-SQL leaderboards (BIRD-SQL, Spider, Live SQL Bench) were outdated or unclear, so a **coding leaderboard** was used as a proxy for SQL generation ability.

1. Download leaderboard data (coding rating, blended price, speed).
2. Compute monthly cost per model and drop those above budget.
3. Min-max normalize coding rating and speed to the 0-1 range.
4. Compute `score = 0.9 × coding_score + 0.1 × speed_score`. Speed has a low weight because the output is only a short SQL query.
5. Select the top-ranked models as candidates.

**Finalists evaluated:** GPT-5.6 Tera, Kimi K3, Grok 4.5, Claude Sonnet 5, MiniMax M3

### 🧪 Step 3: Custom Evaluation

1. Load IPL data (2021-2024) into SQLite.
2. Extract the database schema and inject it into the system prompt.
3. Build a golden dataset of 20 hard questions with validated reference SQL.
4. For every model and question: generate SQL, execute it, execute the golden SQL, and compare the two result tables.
5. Accuracy is the number of matching results divided by the total questions.

---

## 📊 Results

Results from the live evaluation run on 20 difficult questions:

| Rank | Model | Approx. Accuracy | Observations |
|:----:|-------|:----------------:|--------------|
| 1 | Grok 4.5 | ~90% | Strong accuracy, low cost, fast |
| 2 | Claude Sonnet 5 | ~85% | Very fast, reliable API |
| 3 | GPT-5.6 Tera | ~80% | Highest cost of the group |
| 4 | MiniMax M3 | ~65% | Multiple SQL syntax errors |
| 5 | Kimi K3 | ~55% | Slow, SQL syntax errors |

**Key takeaways**

- A model that leads public leaderboards or headlines does not necessarily lead on **your** task.
- The final decision balances accuracy, cost, latency and provider reliability. Here it came down to Grok 4.5 versus Claude Sonnet 5.
- With only 20 questions, each question is worth 5%. Larger datasets and repeated runs give stronger statistical confidence.

> Accuracy varies between runs. Your own numbers are saved in `eval_results.csv`.

---

## 📁 Project Structure

```
llm-sql-eval/
│
├── data/                           # Raw IPL datasets (Kaggle)
│   ├── deliveries.csv              #   Ball-by-ball data
│   └── matches.csv                 #   Match-level data
│
├── .env                            # API keys (not committed)
├── .gitignore                      # Git ignore rules
├── LICENSE                         # MIT License
├── README.md                       # Project documentation
│
├── db.py                           # Builds the SQLite database from the CSVs
├── ipl_2021_2024.db                # Generated SQLite database (IPL 2021-2024)
│
├── schema_extractor.py             # Extracts tables, columns and types
├── schema.sql                      # Generated schema used in the system prompt
│
├── golden_dataset_generator.py     # Question and golden SQL pairs, with validation
├── make_golden_dataset.py          # Exports the pairs to CSV
├── golden_dataset.csv              # Golden dataset used for evaluation
│
├── first_test.py                   # Smoke test for the OpenRouter connection
├── model_openrouter_slug.py        # Candidate models and their OpenRouter slugs
├── evaluator.py                    # Result-table comparison logic
├── main.py                         # Orchestrates the full evaluation loop
│
├── eval_results.csv                # Per-question evaluation results (generated)
└── eval.log                        # Run log (generated)
```

---

## 🚀 Getting Started

### ✅ Prerequisites

- Python 3.10 or higher
- An [OpenRouter](https://openrouter.ai) account and API key (free credits are available; a full 5-model run costs only a few dollars)

### 📦 Installation

```bash
git clone https://github.com/Sharif-Abusad/llm-model-selection-text-to-sql-evals.git
cd llm-model-selection-text-to-sql-evals

python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install pandas python-dotenv langchain-openai
```

### ⚙️ Configuration

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_api_key_here
```

### 🗂️ Data

Download the IPL dataset from Kaggle and place `matches.csv` and `deliveries.csv` in the `data/` folder. The project trims the data to **IPL 2021-2024** to keep evaluation fast.

---

## 💻 Usage

Run the scripts in this order:

```bash
# 1. Build the SQLite database from the CSVs
python db.py

# 2. Extract the schema (creates schema.sql)
python schema_extractor.py

# 3. Validate that every golden SQL query executes
python golden_dataset_generator.py

# 4. Export the golden dataset to CSV
python make_golden_dataset.py

# 5. (Optional) Smoke-test the OpenRouter connection
python first_test.py

# 6. Run the full evaluation across all candidate models
python main.py
```

Outputs:

- `eval_results.csv`: per-question, per-model results
- `eval.log`: execution log

---

## 🔍 How the Evaluation Works

```
golden_dataset.csv
        │
        ▼
 for each model ─────────────────────────────────────────┐
   for each question:                                    │
     1. prompt        = system prompt + schema + question│
     2. generated_sql = LLM(prompt)                      │
     3. df_generated  = run(generated_sql)  on SQLite    │
     4. df_golden     = run(golden_sql)     on SQLite    │
     5. match         = compare(df_generated, df_golden) │
 accuracy = matches / total questions  ──► eval_results.csv
```

**Why compare result tables instead of SQL text?**
The same answer can be produced by many different queries. String matching would wrongly mark correct queries as failures, so the evaluator compares what the queries return.

The comparator in `evaluator.py`:

- Verifies the **row counts** match
- **Normalizes values** (for example `2.0` vs `2`, and minor floating-point differences)
- **Sorts rows** before comparing, unless the question is order-sensitive (`ORDER BY` or top-N), in which case row order must match exactly

---

## 🧩 Extending the Project

**Add a new model:** append a `(display_name, openrouter_slug)` tuple in `model_openrouter_slug.py`. The slug is on the model's OpenRouter page.

**Add new questions:** add entries to `golden_dataset_generator.py`, validate them, and regenerate the CSV with `make_golden_dataset.py`.

**Adapt to another task:** the same framework works for RAG, summarization or classification. Replace the golden dataset and the comparison logic.

---

## 🔮 Future Improvements

- [ ] Expand the golden dataset to 50-500 questions with an easy / medium / hard mix
- [ ] Run each model multiple times and average accuracy
- [ ] Track latency and actual token cost per model
- [ ] Add prompt caching to reduce cost
- [ ] Add few-shot examples and column descriptions to the prompt
- [ ] Migrate to an evaluation framework such as DeepEval

---

## 🙏 Acknowledgements

- [CampusX](https://www.youtube.com/@campusx-official) LLM Evals course for the methodology and case study
- IPL ball-by-ball and match datasets from Kaggle
- [OpenRouter](https://openrouter.ai) for unified model access

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 👤 Author

<div align="center">

**Sharif Abusad**

[![GitHub](https://img.shields.io/badge/GitHub-Sharif--Abusad-181717?style=for-the-badge&logo=github)](https://github.com/Sharif-Abusad)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Sharif--Abusad-0A66C2?style=for-the-badge&logo=linkedin)](https://linkedin.com/in/sharif-abusad)

*If you found this project useful, consider giving it a ⭐ on GitHub.*

</div>