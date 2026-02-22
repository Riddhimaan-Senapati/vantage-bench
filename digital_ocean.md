**Title**

Deploy `backend` FastAPI service to DigitalOcean App Platform with Managed PostgreSQL


---

### Summary

- Migrate the current SQLite-backed FastAPI API (`backend/`) to use a DigitalOcean Managed PostgreSQL database.
- Host the API as a Python web service on DigitalOcean App Platform, built directly from your GitHub repository.
- Configure secrets and environment variables (Slack, Gmail, Gemini, DB URL) in App Platform, and rely on the existing `seed.py` to populate initial data in Postgres.


---

### Assumptions & Defaults

- **Hosting platform:** DigitalOcean **App Platform from GitHub** (your choice).
- **Database strategy:** Start with a **fresh Postgres database and reseed** using `seed.py` (your choice).
- **Service directory:** The backend service lives in the `backend/` subdirectory, with `main.py` exposing `app`.
- **DB configuration:** `backend/database.py` will continue to use the `DATABASE_URL` environment variable, now pointing to Postgres.
- **Secrets:** All sensitive values currently in `backend/.env` will be moved to **DigitalOcean environment variables** (no `.env` in the repo).
- **Docs lookup:** When implementing, you’ll use your **context7 MCP** integration to pull the latest DigitalOcean docs for App Platform and Managed Databases (this plan references those docs conceptually but doesn’t fetch them directly).


---

### Code & Config Changes (Local, Before Deployment)

These are implementation tasks to perform in your repo, but **not executed yet**:

1. **Add Postgres driver dependency**
   - In `backend/requirements.txt`, add a Postgres driver so SQLModel/SQLAlchemy can connect:
     - Add a line: `psycopg2-binary>=2.9.0`
   - Keep existing dependencies as-is.

2. **Confirm DB URL pattern for Postgres**
   - `backend/database.py` already uses:
     - `DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_DB)`
     - `create_engine(DATABASE_URL, ...)`
   - For Postgres, plan to use a URL of the form:
     - `postgresql+psycopg2://<user>:<password>@<host>:<port>/<database>?sslmode=require`
   - No code changes required here; just ensure the `DATABASE_URL` you set in DigitalOcean matches this pattern (DigitalOcean will provide a ready-made URL).

3. **Update `.env.example` to document Postgres use**
   - In `backend/.env.example`, add a commented example for `DATABASE_URL`, e.g.:
     - `# DATABASE_URL=postgresql+psycopg2://...`
   - Do **not** add real credentials; this is just documentation for local/prod configuration.

4. **Ensure secrets are not committed**
   - Verify `.gitignore` in `backend/` includes `.env`.
   - Make sure the actual `backend/.env` containing real tokens is **never pushed** to GitHub.
   - Implementation detail: if any secrets have already been committed, rotate them once you move to DigitalOcean.

5. **Run local sanity check against Postgres (optional but recommended)**
   - Once you have a Postgres instance (can be local Docker or a temporary cloud Postgres):
     - Set `DATABASE_URL` in your local shell to a Postgres URL.
     - Run `uvicorn main:app --reload` from the `backend/` directory.
     - Hit `/health` and `/summary` locally to confirm the app works with Postgres.


---

### DigitalOcean Managed PostgreSQL Setup

Use context7 MCP to open the latest “DigitalOcean Managed Databases for PostgreSQL” docs while following these steps.

1. **Create a Managed PostgreSQL cluster**
   - In DigitalOcean:
     - Create a new project (or use an existing one).
     - Add a **Managed Database → PostgreSQL** cluster.
     - Choose a small starter plan and your preferred region.

2. **Create database and user**
   - In the cluster settings:
     - Note the default database name and user (or create a dedicated `coverageiq` database and user).
     - Copy the **connection string** designed for SQL clients / SQLAlchemy (DigitalOcean provides this in the UI).
     - Ensure the string includes `sslmode=require` or equivalent TLS settings (DigitalOcean typically enforces TLS).

3. **Configure trusted sources**
   - In the Postgres cluster’s **Trusted Sources**, plan to:
     - Add your App Platform app **after** you create it (you can come back to this step).
   - Until the app exists, leave this step pending; the plan assumes you will attach the app later.

4. **Decide on the `DATABASE_URL`**
   - You will use the SQLAlchemy-style connection string as the value for `DATABASE_URL`.
   - Example shape (do not hardcode these values):
     - `postgresql+psycopg2://<user>:<password>@<host>:<port>/<db>?sslmode=require`


---

### DigitalOcean App Platform Setup (From GitHub)

Use context7 MCP to open the latest docs for “DigitalOcean App Platform → Python / FastAPI” while following these steps.

1. **Prepare the GitHub repository**
   - Ensure your repo (with `backend/` subdirectory) is pushed to GitHub or another Git provider supported by App Platform.
   - Confirm:
... (192 lines left)

