# Variables
ENV_FILE = .env
APP_MODULE = app.main:app
HOST = 0.0.0.0
PORT = 8000

# Commands
install:
	pip install -r requirements.txt

run:
	uvicorn $(APP_MODULE) --reload --host $(HOST) --port $(PORT) --env-file $(ENV_FILE)

format:
	black .
	isort .

lint:
	flake8 .

check:
	black --check .
	isort --check-only .
	flake8 .

test:
	pytest tests

migrate:
	alembic upgrade head

makemigrations:
	alembic revision --autogenerate -m "Auto migration"

clean-pyc:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache *.pyc

