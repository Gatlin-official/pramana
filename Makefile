# Works on Linux/macOS/WSL and Windows (Git Bash + GNU make).
ifeq ($(OS),Windows_NT)
PY := backend/.venv/Scripts/python.exe
else
PY := backend/.venv/bin/python
endif
VENV := backend/.venv/.installed

.PHONY: up down migrate ingest eval report dev api ui test lint

$(VENV): backend/requirements.txt backend/requirements-ml.txt
	python -m venv backend/.venv
	$(PY) -m pip install -q -r backend/requirements.txt -r backend/requirements-ml.txt
	touch $(VENV)

up:
	docker compose up -d --wait

down:
	docker compose down

migrate: $(VENV) up
	cd backend && ../$(PY) -m alembic upgrade head

ingest: migrate
	cd backend && ../$(PY) -m app.ingest.cli corpus

eval: $(VENV)
	$(PY) eval/run_eval.py
	$(PY) eval/report.py

dev: $(VENV)
	cd frontend && npm install --silent
	$(MAKE) -j2 api ui

api:
	cd backend && ../$(PY) -m uvicorn app.main:app --reload --port 8000

ui:
	cd frontend && npm run dev

test: $(VENV)
	cd backend && ../$(PY) -m pytest -q

lint: $(VENV)
	cd backend && ../$(PY) -m ruff check . ../eval && ../$(PY) -m ruff format --check . ../eval
