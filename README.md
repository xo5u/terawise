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

## Structure

- `backend/app/main.py`: FastAPI application and health endpoint
- `backend/requirements.txt`: Python dependencies
- `frontend/src/`: React application and styles
- `frontend/vite.config.js`: frontend tooling and API proxy

On macOS/Linux, create the same virtual environment and use `backend/.venv/bin/python` instead of `backend/.venv/Scripts/python.exe`; run the backend with `backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload --port 8000`.
