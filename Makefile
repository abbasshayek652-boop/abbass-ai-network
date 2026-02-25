run:
	uvicorn gateway:app --reload --port 8000

test:
	pytest -q

lint:
	ruff check .
	mypy .

fmt:
	ruff check --fix .
	black .
