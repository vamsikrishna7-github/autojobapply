# autojobapply

A Django-based job application automation system. It scrapes job postings from LinkedIn, Indeed, and Google Jobs using [JobSpy](https://github.com/speedyapply/JobSpy), stores them in PostgreSQL, extracts contact emails from job descriptions, and can send direct outreach emails to hiring teams.

## Features

- **Multi-platform scraping** — LinkedIn, Indeed, and Google Jobs via `python-jobspy`
- **PostgreSQL storage** — Job posts persisted with deduplication by `job_id`
- **Email extraction** — Regex scan of job descriptions for contact addresses
- **Automated outreach** — Optional Gmail SMTP emails with resume link (disabled by default)
- **Django admin** — Browse and manage scraped jobs

## How it works

```
Job boards (LinkedIn / Indeed / Google)
        │
        ▼
  run_job_scraper()          ← scraper/utils.py
        │
        ▼
  JobPost model (PostgreSQL)
        │
        ▼
  auto_apply_via_email()     ← scraper/outreach.py (optional)
        │
        ▼
  Gmail SMTP outreach
```

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ (3.11+ recommended) |
| PostgreSQL | 14+ (or a [Supabase](https://supabase.com) project) |
| Gmail account | With [App Password](https://support.google.com/accounts/answer/185833) enabled (for email outreach only) |

## Project structure

```
autojobapply/
├── core/                  # Django project settings & URLs
│   ├── settings.py
│   └── urls.py
├── scraper/               # Main application
│   ├── models.py          # JobPost model
│   ├── utils.py           # JobSpy scraping logic
│   ├── outreach.py        # Email outreach logic
│   └── management/commands/
│       └── run_job_system.py   # CLI entry point
├── manage.py
└── README.md
```

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/<your-username>/autojobapply.git
cd autojobapply

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install Django==6.0.6 psycopg2-binary python-jobspy
```

This installs the core packages. JobSpy pulls in `pandas`, `requests`, and other dependencies automatically.

### 3. Configure environment variables

Create a `.env` file in the project root (already gitignored):

```bash
# Database (PostgreSQL / Supabase)
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_HOST=your-project.supabase.co
DB_PORT=5432
DB_SSLMODE=require

# If your computer/network is IPv4-only, use the *Session pooler* values from
# Supabase Dashboard → Connect instead of the direct db.<project-ref> host:
# DB_HOST=aws-0-<region>.pooler.supabase.com
# DB_PORT=5432
# DB_USER=postgres.<project-ref>

# Set this instead of DB_* values to use a local SQLite database.
# USE_SQLITE=true

# Comma-separated JobSpy sources. Defaults to linkedin,indeed,google,naukri.
# Other supported sources: glassdoor,zip_recruiter,bayt,bdjobs
JOB_SITES=linkedin,indeed,google,naukri

# Gmail SMTP (required only for email outreach)
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
```

> **Note:** `core/settings.py` currently reads `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` from the environment. Update the `DATABASES` block in `core/settings.py` to use the `DB_*` variables above instead of hardcoded values before deploying or sharing the repo.

Example database config using env vars:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'postgres'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {'sslmode': 'require'},
    }
}
```

#### Local development with SQLite (optional)

For quick local testing without PostgreSQL, uncomment the SQLite block in `core/settings.py` and comment out the PostgreSQL config:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### 4. Run database migrations

```bash
python manage.py migrate
```

This creates the `JobPost` table and Django's built-in auth/session tables.

### 5. Create a Django admin user (optional)

```bash
python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password.

## Running the application

### Scrape jobs

The main automation command scrapes job boards and saves results to the database:

```bash
python manage.py run_job_system
```

This runs `run_job_scraper()` which:

1. Iterates over platforms: **LinkedIn**, **Indeed**, **Google**
2. Searches for configured keywords (default: `"Software Engineer"`)
3. Filters to jobs posted within the last **72 hours** in **India**
4. Saves up to **15 results per keyword per platform**
5. Extracts emails from job descriptions when present
6. Skips duplicate jobs (matched by `job_id`)

Expected output:

```
Starting JobSpy Scraping Routine...
=========================================
Starting Scraper targeting: LINKEDIN
=========================================
Scraping 'Software Engineer' on linkedin...
...
Scraping completed. Initiating direct outreach actions...
System execution completed successfully.
```

### Enable email outreach

Email sending is **disabled by default**. To turn it on:

1. Set `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in your environment
2. Update `from_email` in `scraper/outreach.py` to match your Gmail address (or use `settings.DEFAULT_FROM_EMAIL`)
3. Uncomment the outreach call in `scraper/management/commands/run_job_system.py`:

```python
# Change this:
# auto_apply_via_email()

# To this:
auto_apply_via_email()
```

Then run:

```bash
python manage.py run_job_system
```

The outreach module sends an application email to every `JobPost` that has an `extracted_email` and `email_sent=False`, then marks `email_sent=True` to avoid duplicates.

### Start the Django development server

```bash
python manage.py runserver
```

| URL | Description |
|---|---|
| http://127.0.0.1:8000/admin/ | Django admin panel |
| http://127.0.0.1:8000/ | App routes (currently empty) |

### Register models in admin (optional)

To view scraped jobs in the admin panel, register the model in `scraper/admin.py`:

```python
from django.contrib import admin
from .models import JobPost

@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'site', 'email_sent', 'date_scraped')
    list_filter = ('site', 'email_sent')
    search_fields = ('title', 'company')
```

## Customization

All scraper settings live in `scraper/utils.py`:

| Setting | Default | Description |
|---|---|---|
| `keywords` | `["Software Engineer"]` | Search terms to query |
| `JOB_SITES` | `linkedin,indeed,google,naukri` | Comma-separated JobSpy boards to scrape |
| `location` | `"India"` | Geographic filter |
| `results_wanted` | `15` | Max results per keyword per site |
| `hours_old` | `72` | Only jobs posted within this many hours |

Example — broaden the search:

```python
keywords = [
    "Python Django", "React", "Next.js",
    "Full-stack Developer", "Software Engineer",
]
```

Email template content (subject, body, resume link) can be edited in `scraper/outreach.py`.

## JobPost model

| Field | Description |
|---|---|
| `job_id` | Unique ID from the job board |
| `site` | Source platform (`linkedin`, `indeed`, `google`) |
| `title` | Job title |
| `company` | Company name |
| `location` | Job location |
| `job_url` | Link to the posting |
| `description` | Full job description text |
| `extracted_email` | Best-ranked publicly listed contact email |
| `date_posted` | When the job was posted |
| `date_scraped` | When the record was created (auto) |
| `email_sent` | Whether outreach email was sent |

## Troubleshooting

**`ModuleNotFoundError: No module named 'django'`**
Activate the virtual environment: `source .venv/bin/activate`

**Database connection errors**
- Copy the current connection details from Supabase → Project Settings → Database; a deleted or mistyped project reference creates a “could not translate host name” error.
- Verify `DB_HOST`, `DB_PASSWORD`, port, and SSL settings for Supabase.
- For local development, add `USE_SQLITE=true` to `.env`, then run `python manage.py migrate`.

**JobSpy returns empty results**
- Job boards rate-limit aggressively; try again later or reduce `results_wanted`
- LinkedIn requires `linkedin_fetch_description=True` (already set)
- Google Jobs requires `google_search_term` instead of `search_term` (already handled)

**Email sending fails**
- Use a Gmail [App Password](https://support.google.com/accounts/answer/185833), not your regular password
- Enable 2-Step Verification on your Google account first
- Confirm `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are exported in your shell

**Duplicate key errors on `job_id`**
Expected — the scraper skips jobs already in the database.

## License

MIT — see [LICENSE](LICENSE).
