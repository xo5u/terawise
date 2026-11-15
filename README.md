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

## Structure

- `backend/app/main.py`: FastAPI application and health endpoint
- `backend/requirements.txt`: Python dependencies
- `frontend/src/`: React application and styles
- `frontend/vite.config.js`: frontend tooling and API proxy

On macOS/Linux, create the same virtual environment and use `backend/.venv/bin/python` instead of `backend/.venv/Scripts/python.exe`; run the backend with `backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload --port 8000`.
