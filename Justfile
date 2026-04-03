



serve:
    @echo 'Serving on http://localhost:9103'
    python -m http.server 9103


fastapi:
    uv run uvicorn python.api:app --host 0.0.0.0 --port 9103