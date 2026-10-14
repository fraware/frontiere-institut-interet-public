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
    assert len(sources) == 6
    assert len([s for s in sources if s["format"] == "pdf"]) == 2
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


def test_menu_et_pied_de_page_n_alterent_pas_le_contenu_principal():
    corps = b"Un programme de recherche publique et ses partenaires institutionnels. " * 5
    un = (
        b"<html><header>Menu actualite 1</header><main><article>" + corps +
        b"</article></main><footer>Informations du mois</footer></html>"
    )
    deux = (
        b"<html><header>Menu actualite 2</header><main><article>" + corps +
        b"</article></main><footer>Nouvelles recentes</footer></html>"
    )
    assert empreinte_document(un, "html") == empreinte_document(deux, "html")
    modifie = deux.replace(b"recherche publique", b"recherche territoriale")
    assert empreinte_document(un, "html") != empreinte_document(modifie, "html")


def test_l_historique_est_borne_apres_une_longue_suite_de_modifications():
    src = source()
    etat = {"version": 1, "observations": []}
    for i in range(HISTORIQUE_MAX + 5):
        # Modifier explicitement le contenu situé dans <main>.
        corps = TEXTE.replace(b"</main>", b"<p>" + str(i).encode() + b"</p></main>")
        etat, bilan = collecter([src], etat, MAINTENANT,
                                acquerir=lambda _, c=corps: (c, "text/html"))
    assert len(etat["observations"][0]["historique"]) == HISTORIQUE_MAX
    assert bilan["transitions_institutionnelles_inferees"] == 0


def test_chronologie_six_etapes_officielles_et_financement_inconnu():
    chrono = json.loads(
        (RACINE / "institutionnel/programmes_scientifiques/chronologie_documentaire_v1.json")
        .read_text(encoding="utf-8")
    )
    assert chrono["version"] == 1
    assert len(chrono["programmes"]) == 2
    ids = set()
    for programme in chrono["programmes"]:
        ids.add(programme["id"])
        etapes = programme["evenements"]
        assert [e["etape"] for e in etapes] == [
            "appel_ouvert", "appel_clos", "selection_annoncee"
        ]
        assert [e["date"] for e in etapes] == sorted(e["date"] for e in etapes)
        assert all(adresse_autorisee(e["url"]) for e in etapes)
        assert "convention_ou_notification" in programme["etapes_non_etablies"]
        assert "premier_usage_administratif" in programme["etapes_non_etablies"]
        assert not any(e["etape"] == "aide_attribuee_individuellement" for e in etapes)
    assert ids == {"saps_cppe_2026", "anr_nrf_iabio_2026"}
    saps = next(p for p in chrono["programmes"] if p["id"] == "saps_cppe_2026")
    assert saps["evenements"][2]["nombre_projets_retenus_annonces"] == 22
    assert len(saps["evenements"][2]["acronymes_selectionnes"]) == 22
    assert len(set(saps["evenements"][2]["acronymes_selectionnes"])) == 22
    assert len(saps["evenements"][2]["acronymes_liste_complementaire"]) == 5
    assert "DATSUM" in saps["evenements"][2]["acronymes_selectionnes"]
    assert set(saps["evenements"][2]["acronymes_selectionnes"]).isdisjoint(
        saps["evenements"][2]["acronymes_liste_complementaire"]
    )
    nrf = next(p for p in chrono["programmes"] if p["id"] == "anr_nrf_iabio_2026")
    selection = nrf["evenements"][2]
    assert selection["nombre_projets_retenus_annonces"] == 5
    assert len(selection["acronymes_selectionnes"]) == 5
    assert selection["piece_selection"].endswith(".pdf")
    assert "conditionné" in selection["precision"] or "dépendent" in selection["precision"]



def test_changement_du_pdf_lie_est_detecte_meme_a_texte_identique():
    texte = b"Description officielle du programme et de sa liste de projets." * 4
    def page(version):
        return (b"<html><main><article>" + texte +
                b'<a href="/fileadmin/selection/' + version +
                b'.pdf">Liste des projets selectionnes</a></article></main></html>')
    assert empreinte_document(page(b"v1"), "html") != (
        empreinte_document(page(b"v2"), "html")
    )
