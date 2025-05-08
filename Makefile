# Makefile — Cassandra-backend

DC := docker-compose

.PHONY: build start test down

# Build all images
build:
	$(DC) build

# Bring up Postgres, FastAPI, nginx proxy & UI
start: build
	@echo "⏳  Starting all services…"
	$(DC) up -d
	@echo "✔  FastAPI: http://localhost:8000/health"
	@echo "✔  Files  : http://localhost:8080/"
	@echo "✔  UI     : http://localhost:8501/"

# Run API tests
test: start
	@echo "⏳  Waiting for FastAPI to be healthy on localhost:8000…"
	@bash -c '\
	  for i in $$(seq 1 30); do \
	    if curl -fsS http://localhost:8000/health >/dev/null; then \
	      echo "✔  FastAPI healthy"; \
	      break; \
	    fi; \
	    echo -n "."; sleep 1; \
	  done'
	@echo
	@echo "▶  Running tests against http://app:8000 from inside the app container"
	$(DC) run --rm \
	  --entrypoint="" \
	  -e API_URL=http://app:8000 \
	  -e FILE_SERVER_URL=http://proxy/files \
	  app \
	  pytest -q tests/test_frames.py
	@echo "🛑  Tests done — shutting down all services"
	$(DC) down

# Tear down everything
down:
	@echo "🛑  Shutting down…"
	$(DC) down