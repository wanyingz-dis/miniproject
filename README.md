

# Backend (FastAPI)  

This is a tiny FastAPI backend for the mini-project. It loads three CSVs (`experiments`, `trials`, `runs`), computes a few rollups, and exposes simple JSON endpoints the frontend can call. 

## Quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# CSVs live here:
# backend/data/experiments.csv
# backend/data/trials.csv
# backend/data/runs.csv

uvicorn app.main:app --port 8000 --reload --reload-dir app
