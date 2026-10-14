"""Tests hors réseau de la veille des publications officielles DMTG."""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from scripts.surveiller_publications_dmtg import (
    SurveillanceInvalide, autoriser_adresse, consulter, lancer,
    valider_catalogue, ETAT, CATALOGUE,
)
from scripts.publier_mise_a_jour_institutionnelle import (
    PublicationRefusee, verifier_portee, identite_branche,
)

RACINE = Path(__file__).resolve().parents[1]
MAINTENANT = datetime(2026, 10, 14, 22, tzinfo=timezone.utc)
PAGE = (
    "<html><head><title>Statistiques</title></head><body><main><article>"
    + "Les publications et études de l'administration fiscale portent sur "
      "le traitement des déclarations et les moyens disponibles. " * 4
    + "</article></main></body></html>"
).encode("utf-8")


def copies(tmp_path: Path, sources: list[dict] | None = None) -> None:
    cfg = json.loads((RACINE / CATALOGUE).read_text(encoding="utf-8"))
    if sources is not None:
        cfg["sources"] = sources
    for chemin, obj in (
        (CATALOGUE, cfg),
        (ETAT, {"version": 1, "observations": []}),
    ):
        fichier = tmp_path / chemin
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(json.dumps(obj), encoding="utf-8")


def test_cinq_origines_publiques_stables():
    cfg = json.loads((RACINE / CATALOGUE).read_text(encoding="utf-8"))
    sources = valider_catalogue(cfg)
    assert len(sources) == 5
    assert {s["nature_document"] for s in sources} == {
        "index_statistiques", "catalogue_recettes", "catalogue_mutations",
        "reponse_ministerielle", "rapport_parlementaire"
    }
    assert all(s["format"] == "html" for s in sources)
    assert json.loads((RACINE / ETAT).read_text(encoding="utf-8")) == {
        "version": 1, "observations": []
    }


@pytest.mark.parametrize("url", (
    "http://www.impots.gouv.fr/dgfip-statistiques-2026",
    "https://www.impots.gouv.fr.evil.com/x",
    "https://evil.org/x",
    "https://127.0.0.1/",
    "https://utilisateur:secret@www.senat.fr/rap/",
    "https://www.senat.fr:8443/x",
    "https://www.senat.fr/x#fragment",
))
def test_origines_non_autorisees_refusees(url):
    with pytest.raises(SurveillanceInvalide):
        autoriser_adresse(url)


def test_premier_releve_sans_pretendre_a_un_resultat_statistique(tmp_path):
    copies(tmp_path)
    nouveau, rapport = lancer(tmp_path, acquerir=lambda _: (PAGE, "text/html"),
                              moment=MAINTENANT)
    assert rapport["succes"] == 5
    assert rapport["echecs"] == 0
    assert len(nouveau["observations"]) == 5
    assert rapport["transitions_institutionnelles_inferees"] == 0
    assert all(x["statut"] == "premiere_observation"
               for x in rapport["modifications_documentaires"])
    assert all(x["historique"] == [] for x in nouveau["observations"])


def test_identique_puis_revision_documentaire_sans_interpretation(tmp_path):
    copies(tmp_path)
    cfg = json.loads((tmp_path / CATALOGUE).read_text())
    identifiant = cfg["sources"][0]["id"]
    premier, _ = lancer(tmp_path, acquerir=lambda _: (PAGE, "text/html"),
                        moment=MAINTENANT)
    (tmp_path / ETAT).write_text(json.dumps(premier), encoding="utf-8")
    identique, bilan = lancer(tmp_path, acquerir=lambda _: (PAGE, "text/html"),
                             moment=MAINTENANT)
    assert identique == premier
    assert bilan["modifications_documentaires"] == []
    modifiee = PAGE.replace(b"statistique", b"nouvelle-etude")
    revise, bilan2 = lancer(tmp_path, acquerir=lambda src: (
        (modifiee if src["id"] == identifiant else PAGE), "text/html"
    ), moment=MAINTENANT)
    assert bilan2["transitions_institutionnelles_inferees"] == 0
    assert bilan2["modifications_documentaires"] == [{
        "source_id": identifiant, "statut": "modification_a_requalifier"
    }]
    changed = next(x for x in revise["observations"]
                   if x["source_id"] == identifiant)
    assert len(changed["historique"]) == 1


def test_echec_partiel_preserve_les_signatures_existantes(tmp_path):
    copies(tmp_path)
    ancien, _ = lancer(tmp_path, acquerir=lambda _: (PAGE, "text/html"),
                      moment=MAINTENANT)
    (tmp_path / ETAT).write_text(json.dumps(ancien), encoding="utf-8")
    def acces(source):
        if source["id"] == "senat_rapport_760":
            raise OSError("Site temporairement inaccessible")
        return PAGE, "text/html"
    suivant, bilan = lancer(tmp_path, acquerir=acces, moment=MAINTENANT)
    assert suivant == ancien
    assert bilan["echecs"] == 1 and bilan["succes"] == 4
    assert bilan["controles"][-1]["etat"] == "echec_observation"


def test_changement_adresse_ou_producteur_ne_se_propage_pas(tmp_path):
    copies(tmp_path)
    premier, _ = lancer(tmp_path, acquerir=lambda _: (PAGE, "text/html"),
                        moment=MAINTENANT)
    (tmp_path / ETAT).write_text(json.dumps(premier), encoding="utf-8")
    cfg = json.loads((tmp_path / CATALOGUE).read_text())
    cfg["sources"][0]["nature_document"] = "rapport_parlementaire"
    (tmp_path / CATALOGUE).write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(SurveillanceInvalide, match="Filiation"):
        lancer(tmp_path, acquerir=lambda _: (PAGE, "text/html"), moment=MAINTENANT)


def test_publisher_limite_a_un_seul_registre_dmtg():
    autorise = "institutionnel/programmes_scientifiques/etat_veille_dmtg_v1.json"
    assert verifier_portee("dmtg", [autorise])["nombre_fichiers"] == 1
    assert identite_branche("dmtg", "123456", "1") == (
        "automatisation/dmtg-123456-1"
    )
    for refuse in (
        "institutionnel/programmes_scientifiques/sources_veille_dmtg_v1.json",
        "institutionnel/programmes_scientifiques/dmtg_statistiques_successorales_senat_2026_v1.json",
        "institutionnel/programmes_scientifiques/etat_observations.json",
        "docs/INDEX.md",
    ):
        with pytest.raises(PublicationRefusee, match="hors périmètre"):
            verifier_portee("dmtg", [refuse])
