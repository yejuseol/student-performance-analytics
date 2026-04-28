"""
generate_data.py
Creates a SQLite database (math_tracker.db) with realistic synthetic student
performance data based on the Math Tracker web app schema.

Data is synthetic but grounded in real tutoring context:
- 25 students across 6 math courses
- ~14 months of test records (Oct 2024 – Dec 2025)
- Retake policy introduced for half the students (A/B test natural experiment)
- Score distributions calibrated per course difficulty
"""

import sqlite3
import random
import numpy as np
from datetime import date, timedelta

random.seed(42)
np.random.seed(42)

# ── Schema ────────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id   INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    grade        TEXT NOT NULL,
    subject      TEXT NOT NULL,
    retake_group TEXT NOT NULL  -- 'control' or 'treatment'
);

CREATE TABLE IF NOT EXISTS chapters (
    chapter_id   INTEGER PRIMARY KEY,
    subject      TEXT NOT NULL,
    chapter_num  INTEGER NOT NULL,
    chapter_name TEXT NOT NULL,
    difficulty   REAL NOT NULL  -- 1.0 = baseline, >1 = harder
);

CREATE TABLE IF NOT EXISTS test_records (
    record_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL,
    chapter_id   INTEGER NOT NULL,
    attempt      INTEGER NOT NULL,  -- 1 = first, 2 = retake
    test_date    TEXT NOT NULL,
    mcq_score    REAL NOT NULL,
    mcq_max      REAL NOT NULL,
    frq_score    REAL NOT NULL,
    frq_max      REAL NOT NULL,
    total_score  REAL NOT NULL,
    total_max    REAL NOT NULL,
    pct          REAL NOT NULL,
    note         TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (chapter_id) REFERENCES chapters(chapter_id)
);
"""

# ── Course definitions ─────────────────────────────────────────────────────
COURSES = {
    "Algebra 1": {
        "grade": "G9",
        "base_avg": 81, "base_std": 9,
        "chapters": [
            ("Linear Equations & Inequalities", 0.85),
            ("Functions & Graphs",              0.95),
            ("Systems of Equations",            1.05),
            ("Polynomials",                     1.00),
            ("Factoring",                       1.10),
            ("Quadratic Equations",             1.20),
            ("Exponential Functions",           1.15),
            ("Statistics & Data Analysis",      0.90),
        ]
    },
    "Algebra 2": {
        "grade": "G10",
        "base_avg": 76, "base_std": 10,
        "chapters": [
            ("Polynomial Functions",            0.95),
            ("Rational Functions",              1.10),
            ("Exponential & Logarithmic",       1.15),
            ("Sequences & Series",              1.05),
            ("Trigonometry Basics",             1.20),
            ("Conic Sections",                  1.10),
            ("Probability & Statistics",        0.90),
            ("Complex Numbers",                 1.15),
        ]
    },
    "Precalculus": {
        "grade": "G10",
        "base_avg": 74, "base_std": 10,
        "chapters": [
            ("Review of Functions",             0.90),
            ("Polynomial & Rational Functions", 1.05),
            ("Exponential Functions",           1.00),
            ("Trigonometric Functions",         1.20),
            ("Trigonometric Identities",        1.35),
            ("Vectors & Parametric Equations",  1.25),
            ("Limits Introduction",             1.30),
        ]
    },
    "AP Precalculus": {
        "grade": "G11",
        "base_avg": 72, "base_std": 11,
        "chapters": [
            ("Polynomial & Rational Functions", 1.00),
            ("Exponential & Logarithmic",       1.05),
            ("Trigonometric Functions",         1.20),
            ("Functions Involving Parameters",  1.30),
            ("Polar Coordinates",               1.35),
        ]
    },
    "AP Calculus AB": {
        "grade": "G11",
        "base_avg": 70, "base_std": 12,
        "chapters": [
            ("Limits & Continuity",             1.00),
            ("Differentiation: Definition",     1.10),
            ("Differentiation: Composite",      1.20),
            ("Contextual Applications",         1.15),
            ("Analytical Applications",         1.30),
            ("Integration & Accumulation",      1.35),
            ("Differential Equations",          1.40),
            ("Applications of Integration",     1.35),
        ]
    },
    "AP Calculus BC": {
        "grade": "G12",
        "base_avg": 67, "base_std": 13,
        "chapters": [
            ("Limits & Continuity",             0.95),
            ("Differentiation",                 1.05),
            ("Integration Techniques",          1.20),
            ("Parametric & Polar Functions",    1.35),
            ("Infinite Sequences & Series",     1.50),
            ("Vector-Valued Functions",         1.40),
            ("Differential Equations",          1.45),
        ]
    },
}

# ── Student roster ─────────────────────────────────────────────────────────
# 24 students: 4 per course, each course has 2 control + 2 treatment
# This ensures difficulty is balanced across groups (no confounding)
STUDENT_NAMES = [
    "Aiden Park",    "Brianna Kim",   "Connor Lee",    "Diana Choi",   # Algebra 1
    "Ethan Jung",    "Fiona Yoon",    "George Han",    "Hannah Seo",   # Algebra 2
    "Ivan Kwon",     "Julia Shin",    "Kevin Oh",      "Laura Lim",    # Precalculus
    "Mason Bae",     "Nora Cho",      "Oscar Jang",    "Priya Min",    # AP Precalculus
    "Quinn Song",    "Rachel Moon",   "Samuel Hong",   "Tina Ahn",     # AP Calc AB
    "Uma Kang",      "Victor Yoo",    "Wendy Im",      "Xavier Nam",   # AP Calc BC
]

# Each group of 4: index 0,1 = control; index 2,3 = treatment
STUDENT_COURSES = (
    ["Algebra 1"]     * 4 +
    ["Algebra 2"]     * 4 +
    ["Precalculus"]   * 4 +
    ["AP Precalculus"]* 4 +
    ["AP Calculus AB"]* 4 +
    ["AP Calculus BC"]* 4
)

# Ability modifier per student (persistent talent effect)
ABILITY = {name: np.random.normal(0, 5) for name in STUDENT_NAMES}

# ── Date helpers ───────────────────────────────────────────────────────────
START_DATE = date(2024, 10, 1)

def chapter_date(chapter_num, subject_start_offset_days=0, attempt=1):
    """Each chapter ~3 weeks apart; retake ~1 week after first attempt."""
    base = START_DATE + timedelta(days=subject_start_offset_days)
    chapter_offset = (chapter_num - 1) * 21
    attempt_offset = 7 if attempt == 2 else 0
    jitter = random.randint(-3, 3)
    return base + timedelta(days=chapter_offset + attempt_offset + jitter)

COURSE_OFFSETS = {
    "Algebra 1":     0,
    "Algebra 2":     14,
    "Precalculus":   7,
    "AP Precalculus": 0,
    "AP Calculus AB": 21,
    "AP Calculus BC": 14,
}

# ── Score generator ────────────────────────────────────────────────────────
def generate_score(base_avg, base_std, difficulty, ability_mod,
                   is_retake=False, first_pct=None):
    """
    Returns (mcq_score, mcq_max, frq_score, frq_max, total, max, pct).
    Retake: scores improve by ~8-12 points on average with some variance.
    """
    if is_retake:
        # Retake improves from first attempt; regression to mean capped at 100
        improvement = np.random.normal(10, 4)
        pct = min(100, first_pct + improvement)
        pct = max(0, pct)
    else:
        raw = base_avg - (difficulty - 1) * 15 + ability_mod
        pct = np.random.normal(raw, base_std)
        pct = max(20, min(100, pct))

    # Split into MCQ (60%) and FRQ (40%)
    mcq_max = 30
    frq_max = 20
    total_max = 50

    mcq_score = round(min(mcq_max, max(0, pct / 100 * mcq_max + np.random.normal(0, 1.5))), 1)
    frq_score = round(min(frq_max, max(0, pct / 100 * frq_max + np.random.normal(0, 1.2))), 1)
    total = mcq_score + frq_score
    actual_pct = round(total / total_max * 100, 1)

    return mcq_score, mcq_max, frq_score, frq_max, total, total_max, actual_pct

# ── Main build ─────────────────────────────────────────────────────────────
def build_database(db_path="math_tracker.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    # 1. Insert chapters
    chapter_map = {}  # (subject, chapter_num) -> chapter_id
    chapter_id = 1
    for subject, info in COURSES.items():
        for i, (name, diff) in enumerate(info["chapters"], 1):
            cur.execute(
                "INSERT INTO chapters VALUES (?,?,?,?,?)",
                (chapter_id, subject, i, name, diff)
            )
            chapter_map[(subject, i)] = chapter_id
            chapter_id += 1

    # 2. Insert students (balanced: positions 0,1 in each group of 4 = control; 2,3 = treatment)
    for i, name in enumerate(STUDENT_NAMES):
        pos_in_group = i % 4
        group = "control" if pos_in_group < 2 else "treatment"
        subject = STUDENT_COURSES[i]
        grade = COURSES[subject]["grade"]
        cur.execute(
            "INSERT INTO students VALUES (?,?,?,?,?)",
            (i + 1, name, grade, subject, group)
        )

    # 3. Insert test records
    for i, name in enumerate(STUDENT_NAMES):
        student_id = i + 1
        pos_in_group = i % 4
        group = "control" if pos_in_group < 2 else "treatment"
        subject = STUDENT_COURSES[i]
        course = COURSES[subject]
        ability_mod = ABILITY[name]
        offset = COURSE_OFFSETS[subject]

        for ch_num, (ch_name, diff) in enumerate(course["chapters"], 1):
            ch_id = chapter_map[(subject, ch_num)]

            # First attempt
            mcq, mmax, frq, fmax, total, tmax, pct = generate_score(
                course["base_avg"], course["base_std"], diff, ability_mod
            )
            d = chapter_date(ch_num, offset, attempt=1)
            note = "Great effort!" if pct >= 76 else "Review recommended"
            cur.execute(
                "INSERT INTO test_records VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)",
                (student_id, ch_id, 1, d.isoformat(),
                 mcq, mmax, frq, fmax, total, tmax, pct, note)
            )

            # Treatment group: retake if first attempt < 80%
            if group == "treatment" and pct < 80:
                mcq2, mmax2, frq2, fmax2, tot2, tmax2, pct2 = generate_score(
                    course["base_avg"], course["base_std"], diff, ability_mod,
                    is_retake=True, first_pct=pct
                )
                d2 = chapter_date(ch_num, offset, attempt=2)
                cur.execute(
                    "INSERT INTO test_records VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (student_id, ch_id, 2, d2.isoformat(),
                     mcq2, mmax2, frq2, fmax2, tot2, tmax2, pct2,
                     "Retake — improvement noted")
                )

    conn.commit()

    # Verify
    n_students = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    n_records  = cur.execute("SELECT COUNT(*) FROM test_records").fetchone()[0]
    n_chapters = cur.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]
    print(f"DB built: {n_students} students | {n_chapters} chapters | {n_records} test records")
    conn.close()

if __name__ == "__main__":
    build_database("math_tracker.db")
