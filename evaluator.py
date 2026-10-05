"""
evaluator.py - evaluation logic, separate from orchestration (main.py).

EXECUTION ACCURACY, VALUE-ONLY comparison with FLEXIBLE COLUMN COUNT (Path A):
compares the DATA in the result sets, ignores column names, AND tolerates the
model returning an EXTRA count column (or one FEWER) than the gold.

Why flexible column count:
  For "who scored the most?" some models return just the name, others return
  name + count. Both are correct. So instead of requiring identical shape, we
  check whether the smaller result set's columns appear (by value) as a subset
  within the larger one, row by row.

  - numbers compared numerically (24395 == 24395.0), float noise tolerated
  - row order ignored by default; order_sensitive=True preserves it
"""

import pandas as pd


def _canon_cell(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "∅"
    if isinstance(v, bool):
        return f"str:{v}"
    if isinstance(v, (int, float)):
        f = float(v)
        return f"num:{int(f)}" if f.is_integer() else f"num:{round(f, 4)}"
    s = str(v).strip()
    try:
        f = float(s)
        return f"num:{int(f)}" if f.is_integer() else f"num:{round(f, 4)}"
    except ValueError:
        return f"str:{s}"


def _rows_as_sets(df):
    """Each row becomes a frozenset of canonical cell values (column-position agnostic)."""
    return [frozenset(_canon_cell(v) for v in row) for row in df.values.tolist()]


def _rows_as_tuples(df, order_sensitive):
    rows = [tuple(_canon_cell(v) for v in row) for row in df.values.tolist()]
    return rows if order_sensitive else sorted(rows)


def compare_dataframes(gold_df, generated_df, order_sensitive=False):
    gold_df = gold_df.copy()
    generated_df = generated_df.copy()

    # rows must match in count
    if len(gold_df) != len(generated_df):
        return False

    gcols = gold_df.shape[1]
    xcols = generated_df.shape[1]

    # ---- SAME column count: strict value comparison ----
    if gcols == xcols:
        return _rows_as_tuples(gold_df, order_sensitive) == _rows_as_tuples(generated_df, order_sensitive)

    # ---- DIFFERENT column count (Path A leniency) ----
    # Allow a difference of exactly ONE column (model added/omitted the count).
    if abs(gcols - xcols) != 1:
        return False

    # Identify the smaller (fewer columns) and larger result.
    small, large = (gold_df, generated_df) if gcols < xcols else (generated_df, gold_df)

    small_rows = _rows_as_sets(small)
    large_rows = _rows_as_sets(large)
    if not order_sensitive:
        small_rows = sorted(small_rows, key=lambda s: sorted(s))
        large_rows = sorted(large_rows, key=lambda s: sorted(s))

    # every small-row's values must be a subset of the aligned large-row's values
    return all(s.issubset(l) for s, l in zip(small_rows, large_rows))


def evaluate_one(gold_df, generated_df, order_sensitive=False):
    if generated_df is None:
        return {"correct": False, "reason": "sql_error"}
    try:
        ok = compare_dataframes(gold_df, generated_df, order_sensitive)
        return {"correct": ok, "reason": "match" if ok else "mismatch"}
    except Exception as e:
        return {"correct": False, "reason": f"compare_error: {e}"}