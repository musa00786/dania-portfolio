"""
database.py
Handles SQLite connection, schema creation, and initial (editable) seed data
for the Dania Amjad recruitment portfolio + CMS.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "database.db")


def get_db():
    """Return a sqlite3 connection with row factory set to dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    title TEXT,
    subtitle TEXT,
    intro TEXT,
    about_text TEXT,
    location TEXT,
    email TEXT,
    phone TEXT,
    whatsapp TEXT,
    linkedin TEXT,
    photo_path TEXT,
    cv_path TEXT,
    industries TEXT
);

CREATE TABLE IF NOT EXISTS statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL,
    title TEXT NOT NULL,
    icon TEXT DEFAULT 'target',
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    icon TEXT DEFAULT 'briefcase',
    display_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    logo_path TEXT,
    website TEXT,
    description TEXT,
    is_visible INTEGER DEFAULT 1,
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title TEXT NOT NULL,
    company_id INTEGER,
    company_name_text TEXT,
    start_date TEXT,
    end_date TEXT,
    is_current INTEGER DEFAULT 0,
    location TEXT,
    description TEXT,
    bullet_points TEXT,
    display_order INTEGER DEFAULT 0,
    is_visible INTEGER DEFAULT 1,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    degree TEXT NOT NULL,
    institution TEXT,
    start_year TEXT,
    end_year TEXT,
    description TEXT,
    logo_path TEXT,
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT DEFAULT 'technical',
    proficiency INTEGER DEFAULT 80,
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS languages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    proficiency TEXT DEFAULT 'Fluent',
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    icon TEXT DEFAULT 'award',
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT
);
"""


def init_db(reset_admin_password=None):
    """Create tables if they do not exist and seed initial editable content."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()

    # --- Seed admin account (only if none exists) ---
    cur = conn.execute("SELECT COUNT(*) as c FROM admin")
    if cur.fetchone()["c"] == 0:
        default_user = os.environ.get("ADMIN_USERNAME", "admin")
        default_pass = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
        conn.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            (default_user, generate_password_hash(default_pass)),
        )
        conn.commit()
        print("=" * 60)
        print(" ADMIN ACCOUNT CREATED")
        print(f" Username: {default_user}")
        print(f" Password: {default_pass}")
        print(" Please log in and change these credentials immediately.")
        print("=" * 60)

    # --- Seed profile (only if empty) ---
    cur = conn.execute("SELECT COUNT(*) as c FROM profile")
    if cur.fetchone()["c"] == 0:
        conn.execute(
            """INSERT INTO profile
            (full_name, title, subtitle, intro, about_text, location, email, phone,
             whatsapp, linkedin, photo_path, cv_path, industries)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Dania Amjad",
                "Recruitment Manager",
                "HR Professional",
                "Results-driven HR professional and recruiter with a global perspective, "
                "specializing in end-to-end talent acquisition, employer branding, and "
                "performance management.",
                "Dania Amjad is a results-driven HR professional and recruiter with a global "
                "perspective, specializing in end-to-end talent acquisition, employer branding, "
                "and performance management. She partners with organizations to identify, attract, "
                "and retain top talent across a wide range of industries, helping build "
                "high-performing teams and lasting employer reputations.",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "Healthcare, Hospitality, IT, Real Estate, Construction, Labor, Automotive, "
                "Technology, Streaming",
            ),
        )
        conn.commit()

    # --- Seed services ---
    cur = conn.execute("SELECT COUNT(*) as c FROM services")
    if cur.fetchone()["c"] == 0:
        services = [
            ("End-to-End Recruitment",
             "Manage complete hiring processes from sourcing, screening, interviewing and onboarding.",
             "workflow", 1),
            ("Boolean Search",
             "Advanced Boolean search techniques to identify high-quality and hard-to-find candidates.",
             "search", 2),
            ("Headhunting",
             "Identify and attract passive candidates for senior and niche positions.",
             "target", 3),
            ("Bulk Hiring",
             "Develop and execute high-volume recruitment strategies efficiently.",
             "users", 4),
            ("Employer Branding",
             "Build employer reputation and maintain a strong talent pipeline.",
             "badge-check", 5),
            ("Performance Management",
             "Align employee goals with organizational objectives and improve performance.",
             "trending-up", 6),
        ]
        conn.executemany(
            "INSERT INTO services (title, description, icon, display_order) VALUES (?, ?, ?, ?)",
            services,
        )
        conn.commit()

    # --- Seed statistics ---
    cur = conn.execute("SELECT COUNT(*) as c FROM statistics")
    if cur.fetchone()["c"] == 0:
        stats = [
            ("1,000+", "Blue-Collar Professionals Placed", "hard-hat", 1),
            ("250+", "White-Collar Professionals Placed", "briefcase", 2),
            ("30%", "Team Performance Improvement", "trending-up", 3),
            ("75%", "Employee Retention Achieved", "shield-check", 4),
        ]
        conn.executemany(
            "INSERT INTO statistics (number, title, icon, display_order) VALUES (?, ?, ?, ?)",
            stats,
        )
        conn.commit()

    # --- Seed skills (technical skills only — from provided info) ---
    cur = conn.execute("SELECT COUNT(*) as c FROM skills")
    if cur.fetchone()["c"] == 0:
        skills = [
            ("Boolean Search", "technical", 1),
            ("Head-Hunting", "technical", 2),
            ("Bulk Hiring", "technical", 3),
            ("Paid Ads (Hiring)", "technical", 4),
        ]
        conn.executemany(
            "INSERT INTO skills (name, category, display_order) VALUES (?, ?, ?)",
            skills,
        )
        conn.commit()

    # --- Seed languages ---
    cur = conn.execute("SELECT COUNT(*) as c FROM languages")
    if cur.fetchone()["c"] == 0:
        langs = [("Urdu", "Native", 1), ("English", "Fluent", 2)]
        conn.executemany(
            "INSERT INTO languages (name, proficiency, display_order) VALUES (?, ?, ?)",
            langs,
        )
        conn.commit()

    # --- Seed achievements / awards / activities ---
    cur = conn.execute("SELECT COUNT(*) as c FROM achievements")
    if cur.fetchone()["c"] == 0:
        ach = [
            ("Research Publications", "Contributor to published HR / recruitment research.", "book-open", 1),
            ("LinkedIn Community Admin", "Admin of a 100k-member LinkedIn community.", "users", 2),
        ]
        conn.executemany(
            "INSERT INTO achievements (title, description, icon, display_order) VALUES (?, ?, ?, ?)",
            ach,
        )
        conn.commit()

    # --- Seed settings ---
    cur = conn.execute("SELECT COUNT(*) as c FROM settings")
    if cur.fetchone()["c"] == 0:
        defaults = [
            ("site_title", "Dania Amjad | Recruitment Manager & Talent Acquisition Professional"),
            ("meta_description",
             "Dania Amjad is a results-driven Recruitment Manager and HR professional "
             "specializing in end-to-end talent acquisition, employer branding, and "
             "performance management across Healthcare, IT, Hospitality, Real Estate, "
             "Construction and more."),
        ]
        conn.executemany("INSERT INTO settings (key, value) VALUES (?, ?)", defaults)
        conn.commit()

    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)
