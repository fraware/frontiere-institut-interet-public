.PHONY: lancer verifier initialiser reinitialiser

lancer:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

verifier:
	pytest

initialiser:
	python scripts/initialiser_demonstration.py

reinitialiser:
	rm -f data/frontiere.db
	python scripts/initialiser_demonstration.py
