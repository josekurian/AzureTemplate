.PHONY: install run test lint smoke
install:
	python -m pip install -r requirements.txt
run:
	uvicorn app.main:app --reload --port 8000
test:
	pytest -q
lint:
	ruff check app tests
smoke:
	bash scripts/smoke_test.sh
