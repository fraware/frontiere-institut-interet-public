.PHONY: installer lancer verifier initialiser reinitialiser

installer:
	python -m pip install -e ".[dev]"

lancer:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

verifier:
	python -m compileall -q app scripts tests
	pytest

initialiser:
	python scripts/initialiser_demonstration.py

reinitialiser:
	rm -f data/frontiere.db
	python scripts/initialiser_demonstration.py
