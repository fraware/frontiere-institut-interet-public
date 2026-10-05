import json
from pathlib import Path
from urllib.parse import urlparse


NIVEAUX = {"signal_contextuel", "cas_partiel", "cas_solide"}
PRIORITES = {"haute", "moyenne", "basse"}


def test_corpus_public_structure_et_integrite():
    chemin = Path("donnees/signaux_publics_v1.json")
    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    signaux = contenu["signaux"]

    assert contenu["nombre_signaux"] == len(signaux)
    assert len(signaux) >= 30

    identifiants = [s["id_signal"] for s in signaux]
    assert len(identifiants) == len(set(identifiants))

    for signal in signaux:
        assert signal["niveau_documentaire"] in NIVEAUX
        assert signal["priorite_examen"] in PRIORITES
        assert signal["titre"].strip()
        assert signal["fait_documente"].strip()
        assert signal["capacite_concernee"].strip()
        assert signal["source_organisme"].strip()
        url = urlparse(signal["source_url"])
        assert url.scheme == "https"
        assert url.netloc


def test_corpus_contient_des_contre_exemples_et_des_chronologies():
    contenu = json.loads(Path("donnees/signaux_publics_v1.json").read_text(encoding="utf-8"))
    signaux = contenu["signaux"]

    assert sum(1 for s in signaux if s["contre_exemple"]) >= 5
    assert sum(1 for s in signaux if s["chronologie_exploitable"]) >= 8
    assert sum(1 for s in signaux if s["niveau_documentaire"] == "cas_solide") >= 8
