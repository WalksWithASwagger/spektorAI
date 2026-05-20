PYTHON ?= venv/bin/python
PORT ?= 8501
SMOKE_PORT ?= 8599
COMPOSE ?= docker compose

.PHONY: help lint test eval-fixture digest smoke browser-e2e browser-e2e-fresh app services-run services-smoke services-down

help:
	@printf "WhisperForge operations commands\n\n"
	@printf "  make lint            Run dependency-light Python syntax check\n"
	@printf "  make test            Run unit tests\n"
	@printf "  make eval-fixture    Run credential-free editorial fixture eval\n"
	@printf "  make digest          Generate local resurfacing digest\n"
	@printf "  make smoke           Boot Streamlit and check /_stcore/health\n"
	@printf "  make browser-e2e     Run Playwright browser smoke (run-history reopen + export)\n"
	@printf "  make browser-e2e-fresh Run Playwright fresh-run smoke (paste->recipe->review->export)\n"
	@printf "  make app             Start the local Streamlit monolith on PORT=%s\n" "$(PORT)"
	@printf "  make services-run    Start docker-compose services mode\n"
	@printf "  make services-smoke  Start services mode, wait for health, then stop\n"
	@printf "  make services-down   Stop docker-compose services mode\n"

lint:
	$(PYTHON) -m compileall -q app.py whisperforge.py whisperforge_core ui services scripts tests

test:
	$(PYTHON) -m pytest tests/ -q

eval-fixture:
	$(PYTHON) scripts/editorial_eval_fixture.py

digest:
	$(PYTHON) scripts/resurfacing_digest.py

smoke:
	SMOKE_PORT=$(SMOKE_PORT) tests/smoke.sh

browser-e2e:
	$(PYTHON) scripts/browser_e2e_smoke.py

browser-e2e-fresh:
	$(PYTHON) scripts/browser_e2e_fresh_smoke.py

app:
	OPENAI_API_KEY=$${OPENAI_API_KEY:-dummy} \
	ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY:-dummy} \
	NOTION_API_KEY=$${NOTION_API_KEY:-dummy} \
	NOTION_DATABASE_ID=$${NOTION_DATABASE_ID:-dummy} \
	SERVICE_TOKEN=$${SERVICE_TOKEN:-dummy} \
	$(PYTHON) -m streamlit run app.py --server.port $(PORT)

services-run:
	@test -f .env || { printf "Missing .env; create one from the README Configure .env section before services mode.\n"; exit 1; }
	$(COMPOSE) up --build

services-smoke:
	@test -f .env || { printf "Missing .env; create one from the README Configure .env section before services mode.\n"; exit 1; }
	set -e; trap '$(COMPOSE) down' EXIT; $(COMPOSE) up -d --build --wait; curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null

services-down:
	$(COMPOSE) down
