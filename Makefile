# Makefile — Cassandra-backend

DC := docker-compose

.PHONY: build start test down

# Build all images
build:
	$(DC) build

# Bring up Postgres, FastAPI, nginx proxy & UI
start: build
	@echo "Starting all services..."
	$(DC) up -d
	@echo "FastAPI: http://localhost:8000/health"
	@echo "Files  : http://localhost:8080/"
	@echo "UI     : http://localhost:8501/"

# Run API tests and copy results
test:
	@echo "Running tests from inside the app container..."
	$(DC) exec app pytest -v tests/run_backend_test.py
	@echo "Copying downloaded images to local tests directory..."
	@docker cp cassandra_app:/app/tests/test_lores.jpg tests/ 2>/dev/null || echo "  test_lores.jpg not found (no LoRes frames available)"
	@docker cp cassandra_app:/app/tests/test_random_frame.jpg tests/ 2>/dev/null || echo "  test_random_frame.jpg not found (no frames available)"
	@docker cp cassandra_app:/app/tests/test_hires.jpg tests/ 2>/dev/null || echo "  test_hires.jpg not found (no HiRes frames available)"
	@docker cp cassandra_app:/app/tests/performance_report.json tests/ 2>/dev/null || echo "  performance_report.json not found"
	@echo "Test results copied to ./tests/ directory"
	@echo "Performance report available at: ./tests/performance_report.json"

# Tear down everything
down:
	@echo "Shutting down..."
	$(DC) down