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


def test_chronologies_publiques():
    contenu = json.loads(Path("donnees/chronologies_v1.json").read_text(encoding="utf-8"))
    chronologies = contenu["chronologies"]
    assert len(chronologies) >= 8
    ids = [c["id_signal"] for c in chronologies]
    assert len(ids) == len(set(ids))
    for chronologie in chronologies:
        assert chronologie["evenements"]
        assert chronologie["inconnues"]
        assert chronologie["lecture_provisoire"].strip()
        for evenement in chronologie["evenements"]:
            assert evenement["date"].strip()
            assert evenement["precision"] in {"jour", "mois", "annee", "intervalle"}
            assert evenement["evenement"].strip()


def test_audit_des_cas_solides():
    texte = Path("donnees/AUDIT_CAS_SOLIDES_V1.md").read_text(encoding="utf-8")
    contenu = json.loads(Path("donnees/signaux_publics_v1.json").read_text(encoding="utf-8"))
    solides = [signal["id_signal"] for signal in contenu["signaux"] if signal["niveau_documentaire"] == "cas_solide"]
    assert len(solides) == 16
    for identifiant in solides:
        assert identifiant in texte
    assert "Aucun des seize cas solides n’est rejeté" in texte


def test_dix_chronologies_documentees():
    contenu = json.loads(Path("donnees/chronologies_v1.json").read_text(encoding="utf-8"))
    assert len(contenu["chronologies"]) >= 10
