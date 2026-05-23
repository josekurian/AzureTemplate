# Azure High-End Restaurant AI Automation

Quickstart:

cd Azure/HighEndRestaurantAIAutomation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
make run

Open http://127.0.0.1:8000/docs

Project layout: app/, infra/, docs/, tests/, scripts/

Frontend test console:

- Start the full stack with `docker compose up --build`
- Open `http://127.0.0.1:8081`
- Use the left-side menu to switch between overview, episode testing, request/response inspection, performance monitoring, AI agents, and workflows
