# Project Setup Checklist for Django CTF Platform

## Project Setup

-   [ ] Initialize Django project and app
    -   [ ] Run `django-admin startproject ctfd_clone`
    -   [ ] Change directory: `cd ctfd_clone`
    -   [ ] Create CTF app: `python manage.py startapp ctf`
-   [ ] Configure settings
    -   [ ] Open `ctfd_clone/settings.py`
    -   [ ] Set `SECRET_KEY` to a secure value
    -   [ ] Configure `DATABASES` to use PostgreSQL or MySQL with proper credentials
    -   [ ] Add Redis cache backend under `CACHES` for hint scoring and leaderboard caching

## Authentication & Permissions

-   [ ] Set up admin authentication
    -   [ ] Enable Django's built-in admin by adding `'django.contrib.admin'` to `INSTALLED_APPS`
    -   [ ] Migrate database: `python manage.py migrate`
    -   [ ] Create superuser: `python manage.py createsuperuser`
-   [ ] Implement role-based access
    -   [ ] In `ctf/models.py`, define a `Role` model or use Django Groups (`superadmin`, `editor`, `judge`)
    -   [ ] In `ctf/admin.py`, register `Role` and assign permissions for challenge management, user management, statistics viewing

## Challenge Management

-   [ ] Define Challenge model
    -   [ ] In `ctf/models.py`, create `Challenge` with fields: `title` (CharField), `description` (TextField), `category` (ForeignKey), `value` (IntegerField), `hidden` (BooleanField)
    -   [ ] Add `file_uploads` (FileField, `upload_to='challenges/files/'`) and `flag` (CharField)
-   [ ] Create challenge categories
    -   [ ] Define `Category` model with `name` and `description` fields
    -   [ ] Prepopulate categories (Web, Crypto, Forensics, Pwn, Misc) via data migration
-   [ ] Build admin CRUD interface
    -   [ ] In `ctf/admin.py`, register `Challenge` and `Category` with custom `ModelAdmin` to show list display and filters
    -   [ ] Add rich text editor widget (e.g., Django CKEditor) for description in admin

## Attachments, Hints, and Flags

-   [ ] Support file attachments
    -   [ ] Add `ChallengeFile` model linking to `Challenge` and storing uploaded files
    -   [ ] In admin, inline `ChallengeFile` under Challenge form
-   [ ] Implement hints system
    -   [ ] Create `Hint` model with `challenge`, `text`, `cost` fields
    -   [ ] In admin, inline `Hint` under Challenge; define scoring deduction logic in model method
-   [ ] Validate and store flags
    -   [ ] Add `Submission` model with `user`, `challenge`, `submitted_flag`, `timestamp`, `correct` boolean
    -   [ ] On submission view, compare `submitted_flag` to `Challenge.flag` (case-insensitive) and update `correct`

## Import/Export & Custom Pages

-   [ ] Build import/export utilities
    -   [ ] Create management commands `import_challenges` and `export_challenges` to read/write CSV or YAML using Django's `call_command` API
-   [ ] Enable custom static pages
    -   [ ] Define `FlatPage` model or leverage `django.contrib.flatpages`
    -   [ ] In admin, allow editing of pages like FAQ, rules, and contact using a WYSIWYG editor

## Team and User Management

-   [ ] Define Team model
    -   [ ] In `ctf/models.py`, create `Team` with `name`, `members` (ManyToMany to User), `affiliation`, `registered_at`
-   [ ] Create team registration flow
    -   [ ] Build signup form in `ctf/forms.py` requesting team name, member emails, password
    -   [ ] Send email verification link using Django's `send_mail` and token generation
-   [ ] Admin interface for teams
    -   [ ] Register `Team` in `ctf/admin.py` with list display of name, status, and action buttons to disable/reactivate
    -   [ ] Add action to send bulk emails to selected teams

## Attempt Tracking & Statistics

-   [ ] Record submissions and hint unlocks
    -   [ ] In submission view, create `Submission` and `HintUnlock` records
    -   [ ] Log wrong attempts for rate-limiting and analytics
-   [ ] Build admin dashboard
    -   [ ] Create a custom admin view or separate dashboard app
    -   [ ] Query solve counts per challenge and per team
    -   [ ] Use Django ORM to generate time-series data for solves over time
-   [ ] Visualize data
    -   [ ] Integrate Chart.js or Plotly in admin templates to render graphs of solves, top teams, and category breakdowns

## Player Dashboard & Challenge Interaction

-   [ ] List available challenges
    -   [ ] Create view `challenge_list` filtering by category, solved status, and hidden flag
    -   [ ] Paginate results and display solved icons next to completed challenges
-   [ ] Display challenge details
    -   [ ] Create view `challenge_detail` showing description, files (download links), hints (if unlocked), and submission form
    -   [ ] Implement AJAX flag submission to show instant feedback without page reload
-   [ ] Handle flag submissions
    -   [ ] On POST, validate flag, save `Submission`, update user's score in `Team` model, and redirect back with flash message

## Real-Time Scoreboard & Stats

-   [ ] Build scoreboard view
    -   [ ] Create scoreboard view ordering teams by score and `last_solve_time`
    -   [ ] Use JavaScript polling (e.g., every 30 seconds) to refresh scoreboard table via JSON endpoint
-   [ ] Show user progress graphs
    -   [ ] Create API endpoints returning JSON for user's score over time and solves per category
    -   [ ] On dashboard, render line and bar charts with Chart.js based on API data

## Infrastructure & Deployment

-   [ ] Dockerize application
    -   [ ] Write `Dockerfile` for Django app with Gunicorn entrypoint
    -   [ ] Create `docker-compose.yml` including services: web, db (Postgres), redis
-   [ ] Configure web server
    -   [ ] Add Nginx service in Compose for reverse proxy with SSL termination (Let's Encrypt)
    -   [ ] Expose Gunicorn on internal port 8000 and static files via Nginx
-   [ ] Set up background tasks
    -   [ ] Install Celery and configure broker to Redis in `settings.py`
    -   [ ] Create `celery.py` and load tasks for async hint deductions and email sending

## Advanced & Optional

-   [ ] Implement code challenge grading
    -   [ ] Create `SubmissionFile` model for code uploads and `TestCase` model with input/output pairs
    -   [ ] In Celery task, spin up Docker container to compile/run code against test cases and record pass/fail
-   [ ] Add King-of-the-Hill mode
    -   [ ] Define `KOTHInstance` model storing current owner and timestamp
    -   [ ] Build challenge view showing a live terminal or interactive shell and capture button to claim ownership
-   [ ] Plugin and theming support
    -   [ ] Create a plugins folder and load plugins via Django's AppConfig ready signal
    -   [ ] Use Django templates with `{% block %}` tags to allow theme overrides and custom CSS loading
