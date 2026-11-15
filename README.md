# Terawise

React frontend with Vite and a Python FastAPI backend.

## Setup (Windows PowerShell)

Requires Node.js 20.19+ or 22.12+ and Python 3.10+.

```powershell
npm install
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

Start the backend:

```powershell
npm run dev:server
```

In another terminal, start the frontend:

```powershell
npm run dev
```

- Frontend: http://localhost:5173
- API health: http://127.0.0.1:8000/api/health
- Interactive API docs: http://127.0.0.1:8000/docs

The frontend calls `/api/health`. Vite proxies `/api` requests to FastAPI during development and local preview, so no CORS configuration is needed.

## Production build

```powershell
npm run build
```

The output is in `frontend/dist`. Use `npm run preview` for a local preview with the backend running. For production, serve the built frontend with a web server and route `/api` to FastAPI. Run FastAPI without `--reload` behind your production server.

## Annual rainfall

From the `backend` folder:

```powershell
.\.venv\Scripts\python.exe rain.py --lat 36.5 --lon -98.5 --period past
.\.venv\Scripts\python.exe rain.py --lat 36.5 --lon -98.5 --period next
```

`past` returns the latest complete 12 months of historical rainfall, ending five days ago to allow archive processing. `next` estimates the next 12 months using monthly average daily rainfall from the five latest complete calendar years. It is a historical-average planning estimate, not a weather forecast. Both modes report annual and monthly totals in millimeters, excluding snow, and reject incomplete archive data. Annual output is the default; the older `--year` flag still works.

Run the rainfall unit tests with `.\.venv\Scripts\python.exe -m pytest test_rain_unit.py -v`.

## Planting history

Click **Plant** on a recommended crop to save it through `POST /api/history` into the Supabase `planting_history` table. The history view loads saved plantings through `GET /api/history`.

Enable **Anonymous Sign-Ins** in Supabase under **Authentication → Sign In / Providers**. The existing history table references `auth.users`, so a real Supabase session is required. No login form is needed: `POST /api/session` creates an anonymous session, and the browser stores it under `terawise.history.session`. History and recommendation requests send its bearer token; the backend validates the token and derives the owner rather than trusting a client-provided user ID. Clearing browser storage or switching browsers loses access to that anonymous session's history. Expired sessions refresh through `POST /api/session/refresh`.

Configure the backend's `.env` with `SUPABASE_URL` and the appropriate Supabase key (`SUPABASE_SECRET_KEY` or `SUPABASE_PUBLISHABLE_KEY`). Keep database keys on the server; do not put them in frontend code or `VITE_` variables.

The existing base `planting_history` table is supported. Run `backend/migrations/001_crop_recommendation.sql` in the Supabase SQL editor to enable crop name and nutrition-demand snapshots that preserve the values recorded at planting time.

## Structure

- `backend/app/main.py`: FastAPI application and health endpoint
- `backend/requirements.txt`: Python dependencies
- `frontend/src/`: React application and styles
- `frontend/vite.config.js`: frontend tooling and API proxy

On macOS/Linux, create the same virtual environment and use `backend/.venv/bin/python` instead of `backend/.venv/Scripts/python.exe`; run the backend with `backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload --port 8000`.
