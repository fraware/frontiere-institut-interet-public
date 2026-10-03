.PHONY: run test seed reset

run:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	pytest

seed:
	python scripts/seed_demo.py

reset:
	rm -f data/frontiere.db
	python scripts/seed_demo.py
