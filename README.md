# SpendSense — Personal Expense & Budget Assistant

SpendSense is a complete local web application for tracking income and expenses, setting monthly category budgets, and reviewing spending with charts, a transparent month-end estimate, and rule-based unusual-expense notes.

Financial records are stored in a **local SQLite database**. The app does not use a cloud database, paid APIs, or external login providers.

## Features

- Registration, login, logout, and password change with hashed passwords
- Income and expense transactions with categories, payment methods, filters, and pagination
- Default plus custom categories
- Monthly category budgets with spent, remaining, and utilization
- Dashboard totals, charts, recent activity, and an optional demo-data action
- Analytics: monthly trends, category breakdown, daily spending
- Rule-based insights, baseline month-end forecast, and median-based unusual expense flags
- Profile editing
- pytest coverage for auth, transactions, budgets, dashboard math, and isolation

## Technology stack

- Frontend: HTML5, CSS3, vanilla JavaScript, Chart.js (CDN)
- Backend: Python 3, Flask REST API
- Database: SQLite via the built-in `sqlite3` module
- Security: Werkzeug password hashing, Flask sessions, Flask-WTF CSRF
- Tests: pytest
- Config: python-dotenv

## Project directory structure

```
spendsense/
├── app.py                  # WSGI entrypoint for hosting platforms
├── run.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── pytest.ini
├── server/
├── client/
├── public/assets/           # Static assets served by Vercel and Flask locally
├── tests/
└── instance/
```

## Prerequisites (Windows)

- Python 3.10 or later (`py --version`)
- PowerShell
- A browser (Chrome, Edge, or Firefox)

## Create a virtual environment

```powershell
cd "C:\Users\koush\OneDrive\Desktop\SpendSense Project\spendsense"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activate script, run this once for your user account:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again.

## Install dependencies

```powershell
pip install -r requirements.txt
```

## Configure `.env`

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace `SECRET_KEY` with a long random string. Example:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the printed value into `SECRET_KEY`.

For production, set `APP_ENV=production`, use a unique key with at least 32 characters, keep `FLASK_DEBUG=0`, and set `SESSION_COOKIE_SECURE=1` when serving over HTTPS.

## Initialize the SQLite database

You do not need a separate init command. Starting the app creates `instance/spendsense.db` automatically from `server/schema.sql` if the file is missing.

## Start the Flask server

```powershell
python run.py
```

For hosting platforms that ask for a Flask application or WSGI entrypoint, use
`app:app`. The root `app.py` exposes the Flask application; `run.py` remains the
beginner-friendly local development command.

Static files are stored in `public/assets` so Vercel can serve them through its
static asset CDN. Flask serves the same `/assets/...` paths during local runs.

For Vercel, add `SECRET_KEY` as an environment variable (use a newly generated
random value of at least 32 characters). Vercel is treated as production and
uses secure session cookies. If `DATABASE_PATH` is not set, the app uses
`/tmp/spendsense.db` so the function can start. Vercel's `/tmp` storage is
ephemeral and can be isolated between function instances, so this is suitable
only for a disposable demo. Do not store real financial records there; use a
durable database before inviting real users.

## Local URL

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Register and use the application

1. Click **Get started** and create an account (password: at least 8 characters, including a letter and a number).
2. You are signed in and sent to the dashboard.
3. Use **Quick add** or the Transactions page to record income and expenses in INR.
4. Set category budgets for the current month.
5. Open Analytics and Insights for charts, the month-end estimate, and unusual-expense notes.
6. Use **Log out** when you are done.

Amounts are stored as integer paise (₹1.00 = 100 paise) so totals are not rounded by binary floating point.

## Run automated tests

```powershell
pytest
```

Tests use a temporary SQLite file. They do not write to `instance/spendsense.db`.

## Optional demo data

On an empty dashboard, click **Add optional demo data** and confirm. This inserts labeled sample transactions and two budgets. The app never adds demo rows silently.

## Reset the local database safely

Stop the Flask server, then:

```powershell
Remove-Item .\instance\spendsense.db -ErrorAction SilentlyContinue
python run.py
```

A new empty database is created on startup. Existing user accounts in the old file are not recovered.

## Troubleshoot common errors

| Problem | What to try |
| --- | --- |
| `Activate.ps1` is disabled | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `pip` is not recognized | Confirm the venv is active (`(.venv)` in the prompt) |
| Port 5000 already in use | Stop the other process or change the port in `run.py` |
| CSRF / session token expired | Refresh the page and sign in again |
| Charts do not load | Check that you have internet access for the Chart.js CDN, then refresh |
| Database locked | Stop extra Flask processes and try again |

## Security limitations and deployment notes

This project is designed to run locally for coursework and interviews.

- Flask’s signed cookie session is used. Set a strong `SECRET_KEY`.
- Session cookies are HttpOnly and SameSite=Lax. Set `SESSION_COOKIE_SECURE=1` only behind HTTPS.
- CSRF protection is enabled for state-changing API requests.
- SQLite is a single-file database. It is a poor fit for multiple app servers writing at once.
- Do not commit `.env`, the live database, or real user data.
- For a production host (for example Render, Railway, or a VPS with Gunicorn): use HTTPS, a persistent disk for the SQLite file, `FLASK_DEBUG=0`, and a unique secret key. This README does not claim that a live deployment has been completed.

## Push the project to GitHub

From the `spendsense` folder (after installing Git):

```powershell
git init
git add .
git status
git commit -m "Add SpendSense local SQLite expense tracker."
gh repo create spendsense --private --source=. --remote=origin --push
```

Confirm `.env` and `instance/*.db` are not staged.

## Interview talking points

- **Integer money:** amounts are stored as paise; display uses Indian grouping (`₹1,25,000.00`).
- **User isolation:** every query includes `user_id` from the server session, not a client-supplied owner id.
- **Budgets:** spent = sum of expense transactions for that category whose `transaction_date` falls in the budget month.
- **Forecast:** current-month expenses ÷ elapsed days × remaining days, optionally blended with earlier monthly averages. This is arithmetic, not a trained model.
- **Unusual expenses:** median and median absolute deviation on the same category; at least five earlier expenses are required. A flag is not a fraud claim.
- **SQL:** user input is passed as bound parameters (`?` placeholders).

## License

Prepared for academic demonstration. Use and extend it for your own coursework.

