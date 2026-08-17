# Dania Amjad — Recruitment Portfolio & Admin CMS

A premium, fully editable personal portfolio website for Dania Amjad (Recruitment Manager / HR
Professional), built with Flask + SQLite + vanilla HTML/CSS/JS. Every section of the public site is
powered by a lightweight admin CMS — no code changes are needed to update content.

## Features

- Premium, corporate one-page portfolio (Hero, About, Impact Stats, Services, Experience Timeline,
  Companies, Education, Skills/Languages/Achievements, Contact).
- Secure admin panel (`/admin`) with hashed passwords, session-based auth, and CSRF protection.
- Full CRUD for experience, companies (with logo upload), services, education, statistics,
  achievements, skills, and languages.
- Profile photo and CV (PDF) upload/replace/delete, with automatic image compression.
- SEO: meta tags, Open Graph, `robots.txt`, `sitemap.xml`, semantic HTML.
- Fully responsive (375px – 1440px+), accessible (alt text, focus states, keyboard nav,
  `prefers-reduced-motion` support).

## Requirements

- Python 3.9+

## Setup

```bash
cd dania_portfolio
pip install -r requirements.txt
python app.py
```

The site will be available at **http://127.0.0.1:5000**.

On first run, the database (`instance/database.db`) is created automatically and seeded with the
starter content described in the project brief (profile intro, service descriptions, statistic
labels, technical skills, and languages). Experience, companies, and education are left empty by
design — add your real data through the admin panel.

### First-time admin login

On first run, a console message prints a generated admin username/password (default username
`admin`). You can override these defaults by setting environment variables **before the first run**:

```bash
export ADMIN_USERNAME="youradmin"
export ADMIN_PASSWORD="a-strong-password"
python app.py
```

Go to **http://127.0.0.1:5000/admin/login**, sign in, and immediately change your password from
**Settings → Change Password**.

> If you ever need to reset everything, stop the server, delete `instance/database.db`, and restart
> the app — a fresh admin account will be generated.

## Project structure

```text
dania_portfolio/
├── app.py                  # Flask app & all routes
├── database.py              # Schema + seed data
├── requirements.txt
├── README.md
├── instance/
│   └── database.db          # SQLite database (auto-created)
├── templates/
│   ├── base.html
│   ├── index.html            # Public one-page portfolio
│   ├── login.html
│   ├── 404.html
│   └── admin/
│       ├── admin_base.html
│       ├── dashboard.html
│       ├── profile.html
│       ├── experience.html
│       ├── companies.html
│       ├── expertise.html
│       ├── education.html
│       ├── achievements.html   # Statistics + Awards/Activities
│       ├── skills.html         # Technical skills + Languages
│       └── settings.html
└── static/
    ├── css/style.css
    ├── js/main.js
    └── uploads/
        ├── profile/
        ├── companies/
        ├── education/
        └── cv/
```

## Using the admin panel

Everything is managed from `/admin` after logging in:

- **Profile** — name, title, intro, about text, industries, contact details, profile photo, CV.
- **Experience** — add/edit/delete roles, link to a company (or type a name), mark as current,
  reorder, hide/show.
- **Companies** — add/edit/delete organizations, upload logos, set website links, reorder,
  hide/show. Logos are shown at their natural aspect ratio; a text placeholder is shown if no
  logo is uploaded.
- **Services / Expertise** — the "What I Do" cards, each with a title, description, icon (Font
  Awesome solid icon name), order, and active toggle.
- **Achievements** — manages both the highlighted impact statistics (e.g. "1,000+ Blue-Collar
  Professionals Placed") and the Awards & Activities list.
- **Education** — degree, institution, years, description, logo/icon.
- **Skills** — technical skills and languages.
- **Settings** — SEO title/description and admin password change.

Every list follows the same pattern: **+ Add** opens a form, **Edit** pre-fills the same form,
**Delete** asks for confirmation first, and successful saves show a confirmation banner.

## Security notes

- Passwords are hashed with Werkzeug's `generate_password_hash` — never stored in plain text.
- All admin POST requests are protected with a per-session CSRF token.
- Uploaded files are renamed to random, safe filenames; only image types (png/jpg/jpeg/webp/svg)
  are accepted for photos/logos, and only PDF for the CV.
- The admin dashboard is not accessible without a valid session (`/admin/login` required).

## Notes on content

Per the project brief, no companies, degrees, certifications, awards, or statistics were invented.
Only the information explicitly supplied (profile summary, industries, service descriptions,
example statistic *labels*, technical skills, and languages) was seeded. Experience, Companies,
and Education start empty and are meant to be filled in through the admin panel with real data.
