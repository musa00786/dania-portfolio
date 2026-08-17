"""
Dania Amjad — Recruitment Portfolio + Admin CMS
Flask application entry point.
"""

import os
import secrets
import functools
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort, jsonify, Response
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import get_db, init_db, DB_PATH

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, "static", "uploads")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload cap

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp", "svg"}
ALLOWED_DOC_EXT = {"pdf"}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


def save_upload(file_storage, subfolder, allowed_set, max_dim=1600):
    """Safely save an uploaded file with a random filename. Returns relative path or None."""
    if not file_storage or file_storage.filename == "":
        return None
    filename = secure_filename(file_storage.filename)
    if not allowed_file(filename, allowed_set):
        raise ValueError("File type not allowed.")
    ext = filename.rsplit(".", 1)[1].lower()
    new_name = f"{secrets.token_hex(12)}.{ext}"
    folder = os.path.join(UPLOAD_ROOT, subfolder)
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, new_name)
    file_storage.save(dest)

    # Compress / resize raster images (not SVG/PDF)
    if PIL_AVAILABLE and ext in {"png", "jpg", "jpeg", "webp"}:
        try:
            img = Image.open(dest)
            img.thumbnail((max_dim, max_dim))
            if ext in {"jpg", "jpeg"}:
                img = img.convert("RGB")
                img.save(dest, optimize=True, quality=85)
            else:
                img.save(dest, optimize=True)
        except Exception:
            pass  # if Pillow fails, keep the original saved file

    return f"uploads/{subfolder}/{new_name}"


def delete_upload(rel_path):
    if not rel_path:
        return
    full = os.path.join(BASE_DIR, "static", rel_path)
    if os.path.isfile(full):
        try:
            os.remove(full)
        except OSError:
            pass


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = generate_csrf_token


def validate_csrf():
    token = session.get("csrf_token")
    form_token = request.form.get("csrf_token")
    if not token or not form_token or not secrets.compare_digest(token, form_token):
        abort(400, description="Invalid CSRF token.")


@app.context_processor
def inject_settings():
    conn = get_db()
    settings_rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings = {row["key"]: row["value"] for row in settings_rows}
    conn.close()
    return {"site_settings": settings, "current_year": datetime.now().year}


# --------------------------------------------------------------------------
# Public routes
# --------------------------------------------------------------------------

@app.route("/")
def index():
    conn = get_db()
    profile = conn.execute("SELECT * FROM profile LIMIT 1").fetchone()
    stats = conn.execute("SELECT * FROM statistics ORDER BY display_order ASC").fetchall()
    services = conn.execute(
        "SELECT * FROM services WHERE is_active = 1 ORDER BY display_order ASC"
    ).fetchall()
    experiences = conn.execute(
        """SELECT e.*, c.name AS linked_company_name, c.logo_path AS linked_company_logo
           FROM experiences e LEFT JOIN companies c ON e.company_id = c.id
           WHERE e.is_visible = 1 ORDER BY e.display_order ASC"""
    ).fetchall()
    companies = conn.execute(
        "SELECT * FROM companies WHERE is_visible = 1 ORDER BY display_order ASC"
    ).fetchall()
    education = conn.execute("SELECT * FROM education ORDER BY display_order ASC").fetchall()
    skills = conn.execute("SELECT * FROM skills ORDER BY display_order ASC").fetchall()
    languages = conn.execute("SELECT * FROM languages ORDER BY display_order ASC").fetchall()
    achievements = conn.execute("SELECT * FROM achievements ORDER BY display_order ASC").fetchall()
    conn.close()

    return render_template(
        "index.html",
        profile=profile,
        stats=stats,
        services=services,
        experiences=experiences,
        companies=companies,
        education=education,
        skills=skills,
        languages=languages,
        achievements=achievements,
    )


@app.route("/robots.txt")
def robots_txt():
    content = "User-agent: *\nAllow: /\nSitemap: " + url_for("sitemap_xml", _external=True)
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    pages = [url_for("index", _external=True)]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        xml.append(f"<url><loc>{p}</loc></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/cv/download")
def download_cv():
    conn = get_db()
    profile = conn.execute("SELECT cv_path FROM profile LIMIT 1").fetchone()
    conn.close()
    if not profile or not profile["cv_path"]:
        abort(404)
    directory = os.path.join(BASE_DIR, "static")
    return send_from_directory(directory, profile["cv_path"], as_attachment=True,
                                download_name="Dania_Amjad_CV.pdf")


# --------------------------------------------------------------------------
# Admin auth
# --------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        admin = conn.execute("SELECT * FROM admin WHERE username = ?", (username,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            flash("Welcome back, " + admin["username"] + ".", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# --------------------------------------------------------------------------
# Admin dashboard
# --------------------------------------------------------------------------

@app.route("/admin")
@login_required
def admin_dashboard():
    conn = get_db()
    counts = {
        "experiences": conn.execute("SELECT COUNT(*) c FROM experiences").fetchone()["c"],
        "companies": conn.execute("SELECT COUNT(*) c FROM companies").fetchone()["c"],
        "services": conn.execute("SELECT COUNT(*) c FROM services").fetchone()["c"],
        "achievements": conn.execute("SELECT COUNT(*) c FROM achievements").fetchone()["c"],
        "education": conn.execute("SELECT COUNT(*) c FROM education").fetchone()["c"],
        "statistics": conn.execute("SELECT COUNT(*) c FROM statistics").fetchone()["c"],
    }
    conn.close()
    return render_template("admin/dashboard.html", counts=counts)


# ---- Profile ----

@app.route("/admin/profile", methods=["GET", "POST"])
@login_required
def admin_profile():
    conn = get_db()
    if request.method == "POST":
        validate_csrf()
        form = request.form
        profile = conn.execute("SELECT * FROM profile LIMIT 1").fetchone()

        photo_path = profile["photo_path"] if profile else None
        cv_path = profile["cv_path"] if profile else None

        if "photo" in request.files and request.files["photo"].filename:
            try:
                new_photo = save_upload(request.files["photo"], "profile", ALLOWED_IMAGE_EXT)
                if new_photo:
                    delete_upload(photo_path)
                    photo_path = new_photo
            except ValueError as e:
                flash(str(e), "error")

        if request.form.get("delete_photo") == "1":
            delete_upload(photo_path)
            photo_path = None

        if "cv" in request.files and request.files["cv"].filename:
            try:
                new_cv = save_upload(request.files["cv"], "cv", ALLOWED_DOC_EXT)
                if new_cv:
                    delete_upload(cv_path)
                    cv_path = new_cv
            except ValueError as e:
                flash(str(e), "error")

        data = (
            form.get("full_name", "").strip(),
            form.get("title", "").strip(),
            form.get("subtitle", "").strip(),
            form.get("intro", "").strip(),
            form.get("about_text", "").strip(),
            form.get("location", "").strip(),
            form.get("email", "").strip(),
            form.get("phone", "").strip(),
            form.get("whatsapp", "").strip(),
            form.get("linkedin", "").strip(),
            photo_path,
            cv_path,
            form.get("industries", "").strip(),
        )

        if profile:
            conn.execute(
                """UPDATE profile SET full_name=?, title=?, subtitle=?, intro=?, about_text=?,
                   location=?, email=?, phone=?, whatsapp=?, linkedin=?, photo_path=?, cv_path=?,
                   industries=? WHERE id=?""",
                data + (profile["id"],),
            )
        else:
            conn.execute(
                """INSERT INTO profile (full_name, title, subtitle, intro, about_text, location,
                   email, phone, whatsapp, linkedin, photo_path, cv_path, industries)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                data,
            )
        conn.commit()
        flash("Profile updated successfully.", "success")
        conn.close()
        return redirect(url_for("admin_profile"))

    profile = conn.execute("SELECT * FROM profile LIMIT 1").fetchone()
    conn.close()
    return render_template("admin/profile.html", profile=profile)


# ---- Statistics (achievement stats) ----

@app.route("/admin/statistics/save", methods=["POST"])
@login_required
def admin_statistics_save():
    validate_csrf()
    conn = get_db()
    stat_id = request.form.get("id")
    number = request.form.get("number", "").strip()
    title = request.form.get("title", "").strip()
    icon = request.form.get("icon", "target").strip() or "target"
    order = request.form.get("display_order", 0) or 0
    if stat_id:
        conn.execute(
            "UPDATE statistics SET number=?, title=?, icon=?, display_order=? WHERE id=?",
            (number, title, icon, order, stat_id),
        )
        flash("Statistic updated successfully.", "success")
    else:
        conn.execute(
            "INSERT INTO statistics (number, title, icon, display_order) VALUES (?,?,?,?)",
            (number, title, icon, order),
        )
        flash("Statistic added successfully.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_achievements"))


@app.route("/admin/statistics/delete/<int:stat_id>", methods=["POST"])
@login_required
def admin_statistics_delete(stat_id):
    validate_csrf()
    conn = get_db()
    conn.execute("DELETE FROM statistics WHERE id=?", (stat_id,))
    conn.commit()
    conn.close()
    flash("Statistic deleted.", "success")
    return redirect(url_for("admin_achievements"))


# ---- Achievements page also manages awards/activities list ----

@app.route("/admin/achievements")
@login_required
def admin_achievements():
    conn = get_db()
    stats = conn.execute("SELECT * FROM statistics ORDER BY display_order ASC").fetchall()
    achievements = conn.execute("SELECT * FROM achievements ORDER BY display_order ASC").fetchall()
    conn.close()
    return render_template("admin/achievements.html", stats=stats, achievements=achievements)


@app.route("/admin/achievements/save", methods=["POST"])
@login_required
def admin_achievement_save():
    validate_csrf()
    conn = get_db()
    item_id = request.form.get("id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    icon = request.form.get("icon", "award").strip() or "award"
    order = request.form.get("display_order", 0) or 0
    if item_id:
        conn.execute(
            "UPDATE achievements SET title=?, description=?, icon=?, display_order=? WHERE id=?",
            (title, description, icon, order, item_id),
        )
        flash("Achievement updated successfully.", "success")
    else:
        conn.execute(
            "INSERT INTO achievements (title, description, icon, display_order) VALUES (?,?,?,?)",
            (title, description, icon, order),
        )
        flash("Achievement added successfully.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_achievements"))


@app.route("/admin/achievements/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_achievement_delete(item_id):
    validate_csrf()
    conn = get_db()
    conn.execute("DELETE FROM achievements WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("Achievement deleted.", "success")
    return redirect(url_for("admin_achievements"))


# ---- Services / Expertise ----

@app.route("/admin/expertise")
@login_required
def admin_expertise():
    conn = get_db()
    services = conn.execute("SELECT * FROM services ORDER BY display_order ASC").fetchall()
    conn.close()
    return render_template("admin/expertise.html", services=services)


@app.route("/admin/expertise/save", methods=["POST"])
@login_required
def admin_expertise_save():
    validate_csrf()
    conn = get_db()
    service_id = request.form.get("id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    icon = request.form.get("icon", "briefcase").strip() or "briefcase"
    order = request.form.get("display_order", 0) or 0
    is_active = 1 if request.form.get("is_active") == "on" else 0
    if service_id:
        conn.execute(
            """UPDATE services SET title=?, description=?, icon=?, display_order=?, is_active=?
               WHERE id=?""",
            (title, description, icon, order, is_active, service_id),
        )
        flash("Service updated successfully.", "success")
    else:
        conn.execute(
            """INSERT INTO services (title, description, icon, display_order, is_active)
               VALUES (?,?,?,?,?)""",
            (title, description, icon, order, is_active),
        )
        flash("Service added successfully.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_expertise"))


@app.route("/admin/expertise/delete/<int:service_id>", methods=["POST"])
@login_required
def admin_expertise_delete(service_id):
    validate_csrf()
    conn = get_db()
    conn.execute("DELETE FROM services WHERE id=?", (service_id,))
    conn.commit()
    conn.close()
    flash("Service deleted.", "success")
    return redirect(url_for("admin_expertise"))


# ---- Companies ----

@app.route("/admin/companies")
@login_required
def admin_companies():
    conn = get_db()
    companies = conn.execute("SELECT * FROM companies ORDER BY display_order ASC").fetchall()
    conn.close()
    return render_template("admin/companies.html", companies=companies)


@app.route("/admin/companies/save", methods=["POST"])
@login_required
def admin_companies_save():
    validate_csrf()
    conn = get_db()
    company_id = request.form.get("id")
    name = request.form.get("name", "").strip()
    website = request.form.get("website", "").strip()
    description = request.form.get("description", "").strip()
    order = request.form.get("display_order", 0) or 0
    is_visible = 1 if request.form.get("is_visible") == "on" else 0

    logo_path = None
    if company_id:
        existing = conn.execute("SELECT logo_path FROM companies WHERE id=?", (company_id,)).fetchone()
        logo_path = existing["logo_path"] if existing else None

    if "logo" in request.files and request.files["logo"].filename:
        try:
            new_logo = save_upload(request.files["logo"], "companies", ALLOWED_IMAGE_EXT)
            if new_logo:
                delete_upload(logo_path)
                logo_path = new_logo
        except ValueError as e:
            flash(str(e), "error")

    if company_id:
        conn.execute(
            """UPDATE companies SET name=?, logo_path=?, website=?, description=?,
               is_visible=?, display_order=? WHERE id=?""",
            (name, logo_path, website, description, is_visible, order, company_id),
        )
        flash("Company updated successfully.", "success")
    else:
        conn.execute(
            """INSERT INTO companies (name, logo_path, website, description, is_visible, display_order)
               VALUES (?,?,?,?,?,?)""",
            (name, logo_path, website, description, is_visible, order),
        )
        flash("Company added successfully.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_companies"))


@app.route("/admin/companies/delete/<int:company_id>", methods=["POST"])
@login_required
def admin_companies_delete(company_id):
    validate_csrf()
    conn = get_db()
    existing = conn.execute("SELECT logo_path FROM companies WHERE id=?", (company_id,)).fetchone()
    if existing:
        delete_upload(existing["logo_path"])
    conn.execute("DELETE FROM companies WHERE id=?", (company_id,))
    conn.commit()
    conn.close()
    flash("Company deleted.", "success")
    return redirect(url_for("admin_companies"))


# ---- Experience ----

@app.route("/admin/experience")
@login_required
def admin_experience():
    conn = get_db()
    experiences = conn.execute(
        """SELECT e.*, c.name as linked_company_name FROM experiences e
           LEFT JOIN companies c ON e.company_id = c.id
           ORDER BY e.display_order ASC"""
    ).fetchall()
    companies = conn.execute("SELECT id, name FROM companies ORDER BY name ASC").fetchall()
    conn.close()
    return render_template("admin/experience.html", experiences=experiences, companies=companies)


@app.route("/admin/experience/save", methods=["POST"])
@login_required
def admin_experience_save():
    validate_csrf()
    conn = get_db()
    exp_id = request.form.get("id")
    job_title = request.form.get("job_title", "").strip()
    company_id = request.form.get("company_id") or None
    company_name_text = request.form.get("company_name_text", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    is_current = 1 if request.form.get("is_current") == "on" else 0
    location = request.form.get("location", "").strip()
    description = request.form.get("description", "").strip()
    bullet_points = request.form.get("bullet_points", "").strip()
    order = request.form.get("display_order", 0) or 0
    is_visible = 1 if request.form.get("is_visible") == "on" else 0

    if is_current:
        end_date = ""

    if exp_id:
        conn.execute(
            """UPDATE experiences SET job_title=?, company_id=?, company_name_text=?,
               start_date=?, end_date=?, is_current=?, location=?, description=?,
               bullet_points=?, display_order=?, is_visible=? WHERE id=?""",
            (job_title, company_id, company_name_text, start_date, end_date, is_current,
             location, description, bullet_points, order, is_visible, exp_id),
        )
        flash("Experience updated successfully.", "success")
    else:
        conn.execute(
            """INSERT INTO experiences (job_title, company_id, company_name_text, start_date,
               end_date, is_current, location, description, bullet_points, display_order, is_visible)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (job_title, company_id, company_name_text, start_date, end_date, is_current,
             location, description, bullet_points, order, is_visible),
        )
        flash("Experience added successfully.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_experience"))


@app.route("/admin/experience/delete/<int:exp_id>", methods=["POST"])
@login_required
def admin_experience_delete(exp_id):
    validate_csrf()
    conn = get_db()
    conn.execute("DELETE FROM experiences WHERE id=?", (exp_id,))
    conn.commit()
    conn.close()
    flash("Experience deleted.", "success")
    return redirect(url_for("admin_experience"))


# ---- Education ----

@app.route("/admin/education")
@login_required
def admin_education():
    conn = get_db()
    education = conn.execute("SELECT * FROM education ORDER BY display_order ASC").fetchall()
    conn.close()
    return render_template("admin/education.html", education=education)


@app.route("/admin/education/save", methods=["POST"])
@login_required
def admin_education_save():
    validate_csrf()
    conn = get_db()
    edu_id = request.form.get("id")
    degree = request.form.get("degree", "").strip()
    institution = request.form.get("institution", "").strip()
    start_year = request.form.get("start_year", "").strip()
    end_year = request.form.get("end_year", "").strip()
    description = request.form.get("description", "").strip()
    order = request.form.get("display_order", 0) or 0

    logo_path = None
    if edu_id:
        existing = conn.execute("SELECT logo_path FROM education WHERE id=?", (edu_id,)).fetchone()
        logo_path = existing["logo_path"] if existing else None

    if "logo" in request.files and request.files["logo"].filename:
        try:
            new_logo = save_upload(request.files["logo"], "education", ALLOWED_IMAGE_EXT)
            if new_logo:
                delete_upload(logo_path)
                logo_path = new_logo
        except ValueError as e:
            flash(str(e), "error")

    if edu_id:
        conn.execute(
            """UPDATE education SET degree=?, institution=?, start_year=?, end_year=?,
               description=?, logo_path=?, display_order=? WHERE id=?""",
            (degree, institution, start_year, end_year, description, logo_path, order, edu_id),
        )
        flash("Education record updated successfully.", "success")
    else:
        conn.execute(
            """INSERT INTO education (degree, institution, start_year, end_year, description,
               logo_path, display_order) VALUES (?,?,?,?,?,?,?)""",
            (degree, institution, start_year, end_year, description, logo_path, order),
        )
        flash("Education record added successfully.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_education"))


@app.route("/admin/education/delete/<int:edu_id>", methods=["POST"])
@login_required
def admin_education_delete(edu_id):
    validate_csrf()
    conn = get_db()
    existing = conn.execute("SELECT logo_path FROM education WHERE id=?", (edu_id,)).fetchone()
    if existing:
        delete_upload(existing["logo_path"])
    conn.execute("DELETE FROM education WHERE id=?", (edu_id,))
    conn.commit()
    conn.close()
    flash("Education record deleted.", "success")
    return redirect(url_for("admin_education"))


# ---- Skills & Languages (grouped under Settings-adjacent page) ----

@app.route("/admin/skills")
@login_required
def admin_skills():
    conn = get_db()
    skills = conn.execute("SELECT * FROM skills ORDER BY display_order ASC").fetchall()
    languages = conn.execute("SELECT * FROM languages ORDER BY display_order ASC").fetchall()
    conn.close()
    return render_template("admin/skills.html", skills=skills, languages=languages)


@app.route("/admin/skills/save", methods=["POST"])
@login_required
def admin_skills_save():
    validate_csrf()
    conn = get_db()
    skill_id = request.form.get("id")
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "technical").strip()
    order = request.form.get("display_order", 0) or 0
    if skill_id:
        conn.execute(
            "UPDATE skills SET name=?, category=?, display_order=? WHERE id=?",
            (name, category, order, skill_id),
        )
        flash("Skill updated successfully.", "success")
    else:
        conn.execute(
            "INSERT INTO skills (name, category, display_order) VALUES (?,?,?)",
            (name, category, order),
        )
        flash("Skill added successfully.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_skills"))


@app.route("/admin/skills/delete/<int:skill_id>", methods=["POST"])
@login_required
def admin_skills_delete(skill_id):
    validate_csrf()
    conn = get_db()
    conn.execute("DELETE FROM skills WHERE id=?", (skill_id,))
    conn.commit()
    conn.close()
    flash("Skill deleted.", "success")
    return redirect(url_for("admin_skills"))


@app.route("/admin/languages/save", methods=["POST"])
@login_required
def admin_languages_save():
    validate_csrf()
    conn = get_db()
    lang_id = request.form.get("id")
    name = request.form.get("name", "").strip()
    proficiency = request.form.get("proficiency", "").strip()
    order = request.form.get("display_order", 0) or 0
    if lang_id:
        conn.execute(
            "UPDATE languages SET name=?, proficiency=?, display_order=? WHERE id=?",
            (name, proficiency, order, lang_id),
        )
        flash("Language updated successfully.", "success")
    else:
        conn.execute(
            "INSERT INTO languages (name, proficiency, display_order) VALUES (?,?,?)",
            (name, proficiency, order),
        )
        flash("Language added successfully.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_skills"))


@app.route("/admin/languages/delete/<int:lang_id>", methods=["POST"])
@login_required
def admin_languages_delete(lang_id):
    validate_csrf()
    conn = get_db()
    conn.execute("DELETE FROM languages WHERE id=?", (lang_id,))
    conn.commit()
    conn.close()
    flash("Language deleted.", "success")
    return redirect(url_for("admin_skills"))


# ---- Settings (contact info, SEO, password) ----

@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    conn = get_db()
    if request.method == "POST":
        validate_csrf()
        action = request.form.get("action")

        if action == "update_seo":
            site_title = request.form.get("site_title", "").strip()
            meta_description = request.form.get("meta_description", "").strip()
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('site_title', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (site_title,)
            )
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('meta_description', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (meta_description,)
            )
            conn.commit()
            flash("SEO settings updated successfully.", "success")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")
            admin_row = conn.execute(
                "SELECT * FROM admin WHERE id=?", (session["admin_id"],)
            ).fetchone()
            if not admin_row or not check_password_hash(admin_row["password_hash"], current_pw):
                flash("Current password is incorrect.", "error")
            elif len(new_pw) < 8:
                flash("New password must be at least 8 characters.", "error")
            elif new_pw != confirm_pw:
                flash("New passwords do not match.", "error")
            else:
                conn.execute(
                    "UPDATE admin SET password_hash=? WHERE id=?",
                    (generate_password_hash(new_pw), session["admin_id"]),
                )
                conn.commit()
                flash("Password changed successfully.", "success")

        conn.close()
        return redirect(url_for("admin_settings"))

    settings_rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings = {row["key"]: row["value"] for row in settings_rows}
    conn.close()
    return render_template("admin/settings.html", settings=settings)


# --------------------------------------------------------------------------
# Error handlers
# --------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("404.html", message="Bad request."), 400


@app.template_filter("nl2list")
def nl2list(text):
    """Split a newline-separated string into a list of non-empty trimmed lines."""
    if not text:
        return []
    return [line.strip() for line in text.split("\n") if line.strip()]


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
