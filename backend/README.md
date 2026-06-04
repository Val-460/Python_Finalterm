Backend FastAPI wrapper for the existing Python scraper/analyzer.

Deploy this backend to any Python-capable host (Render, Fly, Railway, etc.). Vercel is not recommended for running Playwright due to binary and runtime limitations.

Local run (recommended inside a virtualenv):

```powershell
cd backend
python -m pip install -r requirements.txt
# install browsers for playwright
python -m playwright install
# run
uvicorn app:app --host 0.0.0.0 --port 8000
```

After running, the frontend can be deployed to Vercel with `NEXT_PUBLIC_BACKEND_URL` set to the backend base URL (e.g. `https://your-backend.example.com`).
