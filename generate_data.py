import sqlite3
import random
import numpy as np
from datetime import date, timedelta

random.seed(7)
np.random.seed(7)

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id   INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    grade        TEXT NOT NULL,
    subject      TEXT NOT NULL,
    retake_group TEXT NOT NULL,
    ability_tier TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chapters (
    chapter_id   INTEGER PRIMARY KEY,
    subject      TEXT NOT NULL,
    chapter_num  INTEGER NOT NULL,
    chapter_name TEXT NOT NULL,
    difficulty   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS test_records (
    record_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL,
    chapter_id   INTEGER NOT NULL,
    attempt      INTEGER NOT NULL,
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

COURSES = {
    "Algebra 1": {
        "grade": "G9", "base_avg": 82, "base_std": 8,
        "chapters": [
            ("Linear Equations & Inequalities", 0.88),
            ("Functions & Graphs",              0.95),
            ("Systems of Equations",            1.05),
            ("Polynomials",                     1.00),
            ("Factoring",                       1.12),
            ("Quadratic Equations",             1.18),
            ("Exponential Functions",           1.10),
            ("Statistics & Data Analysis",      0.92),
        ],
    },
    "Algebra 2": {
        "grade": "G10", "base_avg": 76, "base_std": 10,
        "chapters": [
            ("Polynomial Functions",            0.95),
            ("Rational Functions",              1.12),
            ("Exponential & Logarithmic",       1.15),
            ("Sequences & Series",              1.08),
            ("Trigonometry Basics",             1.22),
            ("Conic Sections",                  1.10),
            ("Probability & Statistics",        0.90),
            ("Complex Numbers",                 1.18),
        ],
    },
    "Precalculus": {
        "grade": "G10", "base_avg": 73, "base_std": 10,
        "chapters": [
            ("Review of Functions",             0.90),
            ("Polynomial & Rational Functions", 1.05),
            ("Exponential Functions",           1.00),
            ("Trigonometric Functions",         1.22),
            ("Trigonometric Identities",        1.38),
            ("Vectors & Parametric Equations",  1.28),
            ("Limits Introduction",             1.32),
        ],
    },
    "AP Precalculus": {
        "grade": "G11", "base_avg": 71, "base_std": 11,
        "chapters": [
            ("Polynomial & Rational Functions", 1.00),
            ("Exponential & Logarithmic",       1.05),
            ("Trigonometric Functions",         1.22),
            ("Functions Involving Parameters",  1.30),
            ("Polar Coordinates",               1.38),
        ],
    },
    "AP Calculus AB": {
        "grade": "G11", "base_avg": 69, "base_std": 12,
        "chapters": [
            ("Limits & Continuity",             0.98),
            ("Differentiation: Definition",     1.10),
            ("Differentiation: Composite",      1.22),
            ("Contextual Applications",         1.15),
            ("Analytical Applications",         1.32),
            ("Integration & Accumulation",      1.38),
            ("Differential Equations",          1.42),
            ("Applications of Integration",     1.35),
        ],
    },
    "AP Calculus BC": {
        "grade": "G12", "base_avg": 65, "base_std": 13,
        "chapters": [
            ("Limits & Continuity",             0.95),
            ("Differentiation",                 1.05),
            ("Integration Techniques",          1.22),
            ("Parametric & Polar Functions",    1.35),
            ("Infinite Sequences & Series",     1.52),
            ("Vector-Valued Functions",         1.42),
            ("Differential Equations",          1.48),
        ],
    },
}

# 4 students per course: control=high+mid, treatment=mid+low
ABILITY_PATTERN = [
    ("control",   "high"),
    ("control",   "mid"),
    ("treatment", "mid"),
    ("treatment", "low"),
]

STUDENT_ROSTER = []
for ci, subject in enumerate(COURSES):
    for slot, (group, tier) in enumerate(ABILITY_PATTERN):
        num = ci * 4 + slot + 1
        STUDENT_ROSTER.append({"name": f"Student_{num:02d}",
                                "subject": subject,
                                "group": group, "tier": tier})

TIER_OFFSET    = {"high": +9,  "mid":  0,  "low": -10}
TIER_STD_SCALE = {"high": 0.8, "mid": 1.0, "low": 1.2}
TIER_FLOOR     = {"high": 48,  "mid": 30,  "low": 20}

COURSE_OFFSETS_DAYS = {
    "Algebra 1": 0, "Algebra 2": 10, "Precalculus": 5,
    "AP Precalculus": 0, "AP Calculus AB": 18, "AP Calculus BC": 12,
}
START_DATE = date(2024, 10, 1)


def tdate(ch_num, course, attempt=1):
    base = START_DATE + timedelta(days=COURSE_OFFSETS_DAYS[course])
    d = base + timedelta(days=(ch_num - 1) * 22
                              + (8 if attempt == 2 else 0)
                              + random.randint(-4, 4))
    return d.isoformat()


def gen_score(base_avg, base_std, diff, tier, retake=False, first_pct=None):
    offset = TIER_OFFSET[tier]
    std    = base_std * TIER_STD_SCALE[tier]
    if retake:
        pct = min(100.0, first_pct + max(0, np.random.normal(9, 4)))
    else:
        pct = np.random.normal(base_avg + offset - (diff - 1.0) * 18, std)
    pct = float(np.clip(pct, TIER_FLOOR[tier], 100.0))
    mm, fm = 30.0, 20.0
    mcq = round(np.clip(pct + np.random.normal(1.5, 2.0), 0, 100) / 100 * mm, 1)
    frq = round(np.clip(pct - np.random.normal(1.5, 2.5), 0, 100) / 100 * fm, 1)
    tot = round(mcq + frq, 1)
    return mcq, mm, frq, fm, tot, mm + fm, round(tot / (mm + fm) * 100, 1)


def note(pct, retake=False):
    if retake:
        if pct >= 80: return "Retake — strong improvement"
        if pct >= 76: return "Retake — passed mastery threshold"
        return "Retake — further review recommended"
    if pct >= 90: return "Excellent work"
    if pct >= 80: return "Good understanding"
    if pct >= 76: return "Meets mastery threshold"
    if pct >= 65: return "Review key concepts before next chapter"
    return "Needs additional practice — retake recommended"


def build_database(db_path="math_tracker.db"):
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    cur.executescript(SCHEMA)

    ch_map = {}
    cid = 1
    for subj, info in COURSES.items():
        for i, (nm, diff) in enumerate(info["chapters"], 1):
            cur.execute("INSERT INTO chapters VALUES (?,?,?,?,?)",
                        (cid, subj, i, nm, diff))
            ch_map[(subj, i)] = cid
            cid += 1

    for sid, s in enumerate(STUDENT_ROSTER, 1):
        grade = COURSES[s["subject"]]["grade"]
        cur.execute("INSERT INTO students VALUES (?,?,?,?,?,?)",
                    (sid, s["name"], grade, s["subject"], s["group"], s["tier"]))

    for sid, s in enumerate(STUDENT_ROSTER, 1):
        info = COURSES[s["subject"]]
        for chi, (_, diff) in enumerate(info["chapters"], 1):
            cid2 = ch_map[(s["subject"], chi)]
            mc, mm, fr, fm, tot, tmax, pct = gen_score(
                info["base_avg"], info["base_std"], diff, s["tier"])
            cur.execute(
                "INSERT INTO test_records VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, cid2, 1, tdate(chi, s["subject"], 1),
                 mc, mm, fr, fm, tot, tmax, pct, note(pct)))
            if s["group"] == "treatment" and pct < 80:
                mc2, mm2, fr2, fm2, tot2, tmax2, pct2 = gen_score(
                    info["base_avg"], info["base_std"], diff, s["tier"],
                    retake=True, first_pct=pct)
                cur.execute(
                    "INSERT INTO test_records VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (sid, cid2, 2, tdate(chi, s["subject"], 2),
                     mc2, mm2, fr2, fm2, tot2, tmax2, pct2, note(pct2, retake=True)))

    conn.commit()
    n_s  = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    n_ch = cur.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]
    n_r  = cur.execute("SELECT COUNT(*) FROM test_records").fetchone()[0]
    ret  = cur.execute("SELECT COUNT(*) FROM test_records WHERE attempt=2").fetchone()[0]
    print(f"{n_s} students | {n_ch} chapters | {n_r} records ({ret} retakes)")
    conn.close()


if __name__ == "__main__":
    build_database()
