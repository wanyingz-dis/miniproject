# Mini Project: LLM Observability Platform

Monitoring and analytics for LLM experiments, trials, and runs. FastAPI backend + React frontend with visualizations. Made with joy.

## Features
- Display experiments, trials, accuracy, cost
- Filtering by status, accuracy range, trial ID, sort
- Charts: accuracy curve, cost breakdown, daily spend
- Optional chatbot via DeepInfra (Meta-Llama-3.1-70B)
- Docker one-command deploy

## Tech Stack
**Backend:** FastAPI, Python 3.12, Pandas, Pydantic, Uvicorn  
**Frontend:** React, TypeScript, Vite, D3.js, Tailwind CSS

## Quick Start
```bash
# Clone
git clone <repository-url>
cd miniproject

# Env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# (optional) DeepInfra key
echo "DEEPINFRA_API_KEY=your_api_key" >> backend/.env

# Run (Docker)
docker compose up --build

Access
Webpage: http://localhost:3000
# Stop
docker compose down




## Alternative: Local Development Setup

If Docker doesn't work or you prefer local development:

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env and add your DEEPINFRA_API_KEY (optional)

# Run backend
uvicorn app.main:app --port 8000 --reload --reload-dir app
```

Backend will be available at http://localhost:8000

### Frontend Setup
```bash
# Navigate to frontend (in a new terminal)
cd frontend

# Install dependencies
npm install

# Setup environment
cp .env.example .env

# Run frontend
npm run dev
```

Frontend will be available at http://localhost:5173


## Environment Variables

**backend/.env:**
```
DEEPINFRA_API_KEY=your_key_here  # Optional for chatbot
DEEPINFRA_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct
```

**frontend/.env:**
```
VITE_API_BASE=http://localhost:8000/api/v1
```


## Known Issues

### Invalid Trial Pages
Clicking on trials with invalid data (e.g., Trial #8 with typo "fnished" status or invalid dates) may result in infinite loading or blank pages. This is an behavior due to malformed data, will fix in the future. Refresh or navigate back to the experiments list to continue.

**Workaround:** Avoid clicking on trials marked with pending/failed status values. 

### Chatbot Feature
The chatbot integration requires a valid DeepInfra API key. If the chatbot is not responding:
- Verify your `DEEPINFRA_API_KEY` is set correctly in `backend/.env`
- Restart the backend service after updating the `.env` file
-There's a context limitation: we're currently sending empty context {} to the API, so the chatbot responds with "I don't have any experiment data” This issue will be fixed in the future

### Docker API Documentation
When running with Docker, the backend API documentation may not be accessible at `http://localhost:8000/docs`. 
