"""Contrats hors réseau du suivi des pages officielles des programmes ANR."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from scripts.surveiller_programmes_scientifiques import (
    SurveillanceInvalide, adresse_autorisee, charger_sources, collecter,
    empreinte_document, verifier_etat, HISTORIQUE_MAX,
)
from scripts.publier_mise_a_jour_institutionnelle import (
    PublicationRefusee, identite_branche, verifier_portee,
)

MAINTENANT = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
RACINE = Path(__file__).resolve().parents[1]
TEXTE = b"<html><body><main>" + b"Un communique institutionnel officiel sur la recherche et les projets selectionnes. " * 4 + b"</main></body></html>"
PDF = b"%PDF-1.7\ncontenu fictif d'un document de selection"


def source(identifiant="anr_essai", fmt="html"):
    return {
        "id": identifiant, "programme": "saps_cppe_2026",
        "nature_document": "appel" if fmt == "html" else "liste_selection",
        "format": fmt, "url": "https://anr.fr/fr/essai",
    }


def test_catalogue_reel_borne_a_cinq_urls_anr():
    catalogue = json.loads((RACINE / "institutionnel/programmes_scientifiques/sources_v1.json")
                           .read_text(encoding="utf-8"))
    sources = charger_sources(catalogue)
    assert len(sources) == 5
    assert {s["programme"] for s in sources} == {
        "saps_cppe_2026", "anr_nrf_iabio_2026", "transversal"
    }
    assert all(s["url"].startswith("https://anr.fr/") for s in sources)
    assert verifier_etat(json.loads(
        (RACINE / "institutionnel/programmes_scientifiques/etat_observations.json")
        .read_text(encoding="utf-8")
    )) == {}


@pytest.mark.parametrize("url", [
    "http://anr.fr/fr/test", "https://evil.org/",
    "https://anr.fr.evil.org/", "https://user:pwd@anr.fr/x",
    "https://anr.fr:8443/x", "https://127.0.0.1/x",
])
def test_seules_origines_officielles_https_autorisees(url):
    with pytest.raises(SurveillanceInvalide):
        adresse_autorisee(url)


def test_empreinte_texte_html_ignore_balises_cosmetiques_et_scripts():
    page = TEXTE
    var = TEXTE.replace(b"<main>", b"<main><script>une valeur aleatoire</script><p>").replace(
        b"</main>", b"</p></main>"
    )
    assert empreinte_document(page, "html") == empreinte_document(var, "html")
    assert empreinte_document(PDF, "pdf") == hashlib.sha256(PDF).hexdigest()


def test_premiere_capture_ne_devient_pas_financement():
    s = source()
    suivant, bilan = collecter([s], {"version": 1, "observations": []},
                               MAINTENANT, acquerir=lambda _: (TEXTE, "text/html"))
    obs = suivant["observations"][0]
    assert obs["empreinte"] == empreinte_document(TEXTE, "html")
    assert obs["programme"] == "saps_cppe_2026"
    assert obs["historique"] == []
    assert bilan["modifications_documentaires"] == [
        {"source_id": "anr_essai", "statut": "premiere_observation"}
    ]
    assert bilan["transitions_institutionnelles_inferees"] == 0


def test_identite_repetee_ne_genere_aucune_proposition():
    s = source()
    premier, _ = collecter([s], {"version": 1, "observations": []},
                           MAINTENANT, acquerir=lambda _: (TEXTE, "text/html"))
    meme, bilan = collecter([s], premier, MAINTENANT,
                           acquerir=lambda _: (TEXTE, "text/html"))
    assert meme == premier
    assert bilan["modifications_documentaires"] == []


def test_revision_historique_et_non_inference():
    s = source()
    premier, _ = collecter([s], {"version": 1, "observations": []},
                           MAINTENANT, acquerir=lambda _: (TEXTE, "text/html"))
    modifie = TEXTE.replace(b"recherche", b"scientifiques")
    nouveau, bilan = collecter([s], premier, MAINTENANT,
                               acquerir=lambda _: (modifie, "text/html"))
    assert nouveau["observations"][0]["empreinte"] != premier["observations"][0]["empreinte"]
    assert nouveau["observations"][0]["historique"][0]["empreinte_avant"] == (
        premier["observations"][0]["empreinte"]
    )
    assert bilan["transitions_institutionnelles_inferees"] == 0
    assert bilan["modifications_documentaires"][0]["statut"] == "modification_a_requalifier"


def test_erreur_ne_remplace_jamais_ancienne_empreinte():
    s = source()
    premier, _ = collecter([s], {"version": 1, "observations": []},
                           MAINTENANT, acquerir=lambda _: (TEXTE, "text/html"))
    def refuse(_):
        raise OSError("Accès refusé")
    suivant, bilan = collecter([s], premier, MAINTENANT, acquerir=refuse)
    assert suivant == premier
    assert bilan["echecs"] == 1
    assert bilan["controles"][0]["cause"] == "OSError"


def test_adresse_de_publication_modifiee_refusee():
    s = source()
    premier, _ = collecter([s], {"version": 1, "observations": []},
                           MAINTENANT, acquerir=lambda _: (TEXTE, "text/html"))
    autre = {**s, "url": "https://anr.fr/fr/autre-page"}
    meme, bilan = collecter([autre], premier, MAINTENANT,
                           acquerir=lambda _: (TEXTE, "text/html"))
    assert meme == premier
    assert bilan["echecs"] == 1


def test_source_nouvelle_et_erreur_partielle_conservent_l_une():
    sources = [source(), source("anr_autre")]
    def acquerir(s):
        if s["id"] == "anr_autre":
            raise OSError("Service inaccessible")
        return TEXTE, "text/html"
    suivant, bilan = collecter(sources, {"version": 1, "observations": []},
                               MAINTENANT, acquerir=acquerir)
    assert len(suivant["observations"]) == 1
    assert bilan["succes"] == 1 and bilan["echecs"] == 1


def test_plafond_historique_et_verification_filiation():
    item = {
        "source_id": "anr_essai",
        "empreinte": "a" * 64,
        "historique": [{"avant": x} for x in range(HISTORIQUE_MAX + 1)],
    }
    with pytest.raises(SurveillanceInvalide, match="Historique"):
        verifier_etat({"version": 1, "observations": [item]})


def test_publication_n_autorise_que_l_etat_des_programmes():
    autorise = "institutionnel/programmes_scientifiques/etat_observations.json"
    assert verifier_portee("programmes", [autorise])["nombre_fichiers"] == 1
    assert identite_branche("programmes", "123456", "1") == (
        "automatisation/programmes-123456-1"
    )
    for p in ("institutionnel/programmes_scientifiques/sources_v1.json",
              "institutionnel/programmes_scientifiques/original.pdf",
              "institutionnel/veille/revue_signaux_2026_10_14.json"):
        with pytest.raises(PublicationRefusee, match="hors périmètre"):
            verifier_portee("programmes", [p])
