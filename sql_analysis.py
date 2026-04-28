"""
sql_analysis.py
Runs analytical SQL queries on math_tracker.db and prints results.
All queries written in pure SQL — pandas used only for display/export.
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect("math_tracker.db")

queries = {

    # ── Q1: Overall stats by subject ───────────────────────────────────────
    "q1_subject_overview": """
        SELECT
            s.subject,
            COUNT(DISTINCT s.student_id)                        AS students,
            COUNT(r.record_id)                                  AS total_tests,
            ROUND(AVG(r.pct), 1)                                AS avg_pct,
            ROUND(100.0 * SUM(CASE WHEN r.pct >= 76 THEN 1 ELSE 0 END)
                  / COUNT(r.record_id), 1)                      AS mastery_rate_pct
        FROM students s
        JOIN test_records r ON s.student_id = r.student_id
        GROUP BY s.subject
        ORDER BY avg_pct DESC
    """,

    # ── Q2: Chapter difficulty — hardest chapters ─────────────────────────
    "q2_hardest_chapters": """
        SELECT
            c.subject,
            c.chapter_num,
            c.chapter_name,
            ROUND(AVG(r.pct), 1)                                AS avg_pct,
            COUNT(r.record_id)                                  AS attempts
        FROM chapters c
        JOIN test_records r ON c.chapter_id = r.chapter_id
        WHERE r.attempt = 1
        GROUP BY c.chapter_id
        ORDER BY avg_pct ASC
        LIMIT 10
    """,

    # ── Q3: Control vs Treatment — final (best) score per chapter ─────────
    "q3_ab_raw": """
        SELECT
            s.student_id,
            s.name,
            s.subject,
            s.retake_group,
            c.chapter_id,
            c.chapter_name,
            MAX(r.pct)                                          AS best_pct,
            COUNT(r.record_id)                                  AS attempts_taken
        FROM students s
        JOIN test_records r ON s.student_id = r.student_id
        JOIN chapters c     ON r.chapter_id = c.chapter_id
        GROUP BY s.student_id, c.chapter_id
    """,

    # ── Q4: Group summary — Control vs Treatment ──────────────────────────
    "q4_group_summary": """
        SELECT
            s.retake_group,
            COUNT(DISTINCT s.student_id)                        AS students,
            COUNT(r.record_id)                                  AS total_records,
            ROUND(AVG(r.pct), 1)                                AS avg_all_attempts_pct,
            ROUND(100.0 * SUM(CASE WHEN r.pct >= 76 THEN 1 ELSE 0 END)
                  / COUNT(r.record_id), 1)                      AS mastery_rate_pct
        FROM students s
        JOIN test_records r ON s.student_id = r.student_id
        GROUP BY s.retake_group
    """,

    # ── Q5: Score trend over time (monthly average) ───────────────────────
    "q5_monthly_trend": """
        SELECT
            SUBSTR(r.test_date, 1, 7)                           AS month,
            s.retake_group,
            ROUND(AVG(r.pct), 1)                                AS avg_pct,
            COUNT(r.record_id)                                  AS tests_taken
        FROM test_records r
        JOIN students s ON r.student_id = s.student_id
        GROUP BY month, s.retake_group
        ORDER BY month
    """,

    # ── Q6: MCQ vs FRQ gap per subject ────────────────────────────────────
    "q6_mcq_frq_gap": """
        SELECT
            s.subject,
            ROUND(AVG(r.mcq_score / r.mcq_max * 100), 1)       AS avg_mcq_pct,
            ROUND(AVG(r.frq_score / r.frq_max * 100), 1)       AS avg_frq_pct,
            ROUND(AVG(r.mcq_score / r.mcq_max * 100)
                - AVG(r.frq_score / r.frq_max * 100), 1)        AS mcq_minus_frq
        FROM test_records r
        JOIN students s ON r.student_id = s.student_id
        GROUP BY s.subject
        ORDER BY mcq_minus_frq DESC
    """,

    # ── Q7: Retake improvement detail (treatment group only) ──────────────
    "q7_retake_improvement": """
        SELECT
            s.name,
            s.subject,
            c.chapter_name,
            first_try.pct                                       AS first_pct,
            retake.pct                                          AS retake_pct,
            ROUND(retake.pct - first_try.pct, 1)               AS improvement
        FROM test_records first_try
        JOIN test_records retake
          ON first_try.student_id = retake.student_id
         AND first_try.chapter_id = retake.chapter_id
         AND first_try.attempt    = 1
         AND retake.attempt       = 2
        JOIN students s ON first_try.student_id = s.student_id
        JOIN chapters c ON first_try.chapter_id = c.chapter_id
        ORDER BY improvement DESC
    """,
}

results = {}
for name, sql in queries.items():
    df = pd.read_sql_query(sql, conn)
    results[name] = df
    print(f"\n{'='*60}")
    print(f"  {name.upper()}")
    print('='*60)
    print(df.to_string(index=False))

conn.close()

# Export CSVs for Tableau
import os
os.makedirs("tableau_exports", exist_ok=True)

conn2 = sqlite3.connect("math_tracker.db")
export_queries = {
    "students":        "SELECT * FROM students",
    "chapters":        "SELECT * FROM chapters",
    "test_records":    """
        SELECT r.*, s.name, s.subject, s.grade, s.retake_group,
               c.chapter_name, c.chapter_num, c.difficulty
        FROM test_records r
        JOIN students s ON r.student_id = s.student_id
        JOIN chapters c ON r.chapter_id = c.chapter_id
    """,
    "ab_best_scores":  """
        SELECT s.student_id, s.name, s.subject, s.retake_group,
               c.chapter_id, c.chapter_name, c.difficulty,
               MAX(r.pct) AS best_pct,
               COUNT(r.record_id) AS attempts_taken,
               CASE WHEN MAX(r.pct) >= 76 THEN 1 ELSE 0 END AS mastered
        FROM students s
        JOIN test_records r ON s.student_id = r.student_id
        JOIN chapters c     ON r.chapter_id = c.chapter_id
        GROUP BY s.student_id, c.chapter_id
    """,
}

for fname, sql in export_queries.items():
    df = pd.read_sql_query(sql, conn2)
    path = f"tableau_exports/{fname}.csv"
    df.to_csv(path, index=False)
    print(f"Exported: {path}  ({len(df)} rows)")

conn2.close()
print("\nAll exports done.")
