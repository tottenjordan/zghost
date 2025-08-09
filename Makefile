.PHONY: help install dev frontend backend artifact-server clean

help:
	@echo "Available commands:"
	@echo "  make install       - Install all dependencies (backend and frontend)"
	@echo "  make dev           - Run backend, artifact server, and frontend"
	@echo "  make frontend      - Run only the frontend development server"
	@echo "  make backend       - Run only the backend agent server"
	@echo "  make artifact-server - Run the artifact HTTP server"
	@echo "  make clean         - Clean up temporary files and caches"

install:
	@echo "Installing backend dependencies..."
	poetry install
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev:
	@echo "Starting development servers..."
	@echo "Backend will run on http://localhost:8000"
	@echo "Artifact server will run on http://localhost:8001"
	@echo "Frontend will run on http://localhost:5173"
	@trap 'kill %1; kill %2; kill %3' INT; \
	poetry run adk api_server . & \
	sleep 3 && \
	poetry run python artifact_server.py & \
	sleep 2 && \
	cd frontend && npm run dev & \
	wait

frontend:
	@echo "Starting frontend development server on http://localhost:5173..."
	cd frontend && npm run dev

backend:
	@echo "Starting backend agent server on http://localhost:8000..."
	poetry run adk api_server .

artifact-server:
	@echo "Starting artifact HTTP server on http://localhost:8001..."
	poetry run python artifact_server.py

clean:
	@echo "Cleaning up..."
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf .venv
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete