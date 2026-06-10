# Setup Guide

## Requirements

- Python 3.11 or newer
- A local Python virtual environment
- No Docker
- No paid API key
- No mandatory Ollama

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
```

Use the project virtual environment for all commands. This keeps global Python packages and plugins out of the project test run.

The app reads environment variables directly and loads `.env` when `python-dotenv` is installed from the project requirements.

For backend-only work, install the backend runtime dependencies:

```powershell
pip install -r backend/requirements.txt
```

## Run Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Run Backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Visit `http://127.0.0.1:8000/health`.

## Run Frontend

```powershell
.\.venv\Scripts\streamlit.exe run frontend/streamlit_app.py
```
