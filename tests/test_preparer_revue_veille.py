"""Tests sans réseau du passage des signaux publics à la revue humaine."""
from datetime import datetime, timezone

import pytest

from scripts.auditer_fraicheur_veille import PolitiqueInvalide
from scripts.preparer_revue_veille import (
    categorie_temporelle, preparer_revue, reperes, resume, url_reference,
)

MAINTENANT = datetime(2026, 10, 14, 18, tzinfo=timezone.utc)
OBSERVE = "2026-10-14T14:00:00+00:00"


def publication(titre: str, identifiant: str = "a" * 64) -> dict:
    return {
        "identifiant_publication": identifiant,
        "source_id": "anr_actualites",
        "titre": titre,
        "description": "Les documents ont été rendus publics.",
        "nature_signal": "publication_publique_non_qualifiee",
        "date_publication": "2026-10-12T12:00:00+00:00",
        "observe_initialement_le": OBSERVE,
        "lien": "https://anr.fr/actualites/exemple",
    }


def piste() -> dict:
    return {
        "identifiant": "b" * 64,
        "jeu_id": "jeu-officiel",
        "collectivite": "Collectivité fictive",
        "deliberation_id": "D-42",
        "deliberation_date": "2026-10-01",
        "mots_de_reperage": ["cybersecurite"],
        "url_document_annonce": "https://publication-actes.fr/actes/42.pdf",
        "observe_pour_la_premiere_fois": OBSERVE,
    }


def test_veille_ne_transforme_pas_un_mot_en_besoin():
    revue = preparer_revue(
        {"observations": [publication("Nouvelle formation en intelligence artificielle")]},
        {"pistes": [piste()]}, MAINTENANT,
    )
    assert revue["nombre_total_de_pistes_selectionnees"] == 2
    assert revue["selection_par_reperage_lexical_uniquement"]
    assert {p["statut_preuve"] for p in revue["dossiers"]} == {
        "publication_non_qualifiee", "correspondance_scdl_non_qualifiee"
    }
    assert "besoin" not in revue["dossiers"][0]
    assert "Aucune n'est un besoin public validé" in resume(revue)


def test_mot_ia_isole_non_utilise_et_accents_reconnus():
    assert reperes("Projet IA") == []
    assert reperes("Programme de cybersécurité") == ["cybersecurite"]
    assert reperes("Intelligence Artificielle et recherche scientifique") == [
        "intelligence_artificielle", "recherche",
    ]


def test_publie_ancien_nest_pas_requalifie_nouveau():
    entree = publication("Marchés publics et compétences", "c" * 64)
    entree["date_publication"] = "2025-01-01T00:00:00+00:00"
    revue = preparer_revue(
        {"observations": [entree]}, {"pistes": []}, MAINTENANT,
    )
    assert revue["dossiers"][0]["classe_temporelle"] == "archives"
    assert categorie_temporelle(None, MAINTENANT) == "date_publication_inconnue"


def test_liste_bornee_sans_declassement_frauduleux():
    anciens = [publication("Marché public", f"{i:064x}") for i in range(5)]
    revue = preparer_revue({"observations": anciens}, {"pistes": []},
                           MAINTENANT, limite=2)
    assert revue["file_limitee"] is True
    assert revue["nombre_total_de_pistes_selectionnees"] == 5
    assert len(revue["dossiers"]) == 2


def test_identite_repetee_ou_nature_inattendue_refusee():
    un = publication("Intelligence artificielle")
    with pytest.raises(PolitiqueInvalide, match="dupliquée"):
        preparer_revue({"observations": [un, un]}, {"pistes": []}, MAINTENANT)
    with pytest.raises(PolitiqueInvalide, match="Nature"):
        preparer_revue(
            {"observations": [{**un, "nature_signal": "besoin_reel"}]},
            {"pistes": []}, MAINTENANT,
        )


def test_urls_ne_sont_pas_suivies_et_les_acces_prives_exclus():
    assert url_reference("https://publication-actes.fr/acte.pdf")
    assert url_reference("http://example.com/source.pdf") is None
    assert url_reference("https://identifiant:mdp@exemple.fr/") is None
    assert url_reference("https://example.org:8443/a") is None


def test_source_scdl_sans_pdf_ne_prouve_pas_un_usage():
    entree = {**piste(), "url_document_annonce": None}
    revue = preparer_revue(
        {"observations": []}, {"pistes": [entree]}, MAINTENANT,
    )
    element = revue["dossiers"][0]
    assert element["url_reference"] is None
    assert element["statut_preuve"] == "correspondance_scdl_non_qualifiee"

def test_date_reelle_prime_sur_la_date_de_collecte():
    ancien = publication("Intelligence artificielle", "1" * 64)
    ancien["date_publication"] = "2025-01-01T00:00:00+00:00"
    ancien["observe_initialement_le"] = "2026-10-14T17:59:00+00:00"
    recent = publication("Recherche scientifique", "2" * 64)
    recent["date_publication"] = "2026-10-13T08:00:00+00:00"
    recent["observe_initialement_le"] = "2026-10-12T08:00:00+00:00"
    resultat = preparer_revue(
        {"observations": [ancien, recent]}, {"pistes": []},
        MAINTENANT, limite=1,
    )
    assert resultat["dossiers"][0]["id"].endswith("2" * 64)
    assert resultat["dossiers"][0]["classe_temporelle"] == "publication_90_jours"
    assert resultat["file_limitee"] is True


def test_equilibre_des_sources_dans_une_file_bornee():
    abondants = [
        {**publication("Marchés publics", f"{i:064x}"),
         "source_id": "source_abondante"}
        for i in range(1, 12)
    ]
    divers = publication("Recherche scientifique", "f" * 64)
    divers["source_id"] = "source_distincte"
    resultat = preparer_revue(
        {"observations": abondants + [divers]}, {"pistes": []},
        MAINTENANT, limite=2,
    )
    assert {x["source_id"] for x in resultat["dossiers"]} == {
        "source_abondante", "source_distincte",
    }


def test_date_future_nest_jamais_prioritaire():
    futur = publication("Intelligence artificielle", "e" * 64)
    futur["date_publication"] = "2027-01-01T00:00:00+00:00"
    courant = publication("Recherche scientifique", "d" * 64)
    courant["date_publication"] = "2026-10-13T00:00:00+00:00"
    revue = preparer_revue(
        {"observations": [futur, courant]}, {"pistes": []},
        MAINTENANT, limite=1,
    )
    assert revue["dossiers"][0]["id"].endswith("d" * 64)

def test_lancement_reel_depuis_la_racine_du_depot(tmp_path):
    """Reproduire l'invocation en module depuis GitHub Actions."""
    import json
    from pathlib import Path
    import subprocess
    import sys

    sources = tmp_path / "institutionnel/flux_publics/observations.json"
    actes = tmp_path / "institutionnel/deliberations_publiques/pistes.json"
    sources.parent.mkdir(parents=True)
    actes.parent.mkdir(parents=True)
    sources.write_text(
        json.dumps({"observations": [publication("Intelligence artificielle")]}),
        encoding="utf-8",
    )
    actes.write_text(json.dumps({"pistes": [piste()]}), encoding="utf-8")
    resultat = subprocess.run(
        [
            sys.executable, "-m", "scripts.preparer_revue_veille",
            "--racine", str(tmp_path),
            "--sortie-json", str(tmp_path / "revue.json"),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert resultat.returncode == 0, resultat.stderr + resultat.stdout
    revue = json.loads((tmp_path / "revue.json").read_text(encoding="utf-8"))
    assert revue["nombre_total_de_pistes_selectionnees"] == 2

def test_date_de_deliberation_ne_devient_pas_date_de_publication():
    """L'adoption ne fournit pas l'instant de mise en ligne de l'acte."""
    resultat = preparer_revue(
        {"observations": []},
        {"pistes": [piste()]},
        MAINTENANT,
    )["dossiers"][0]
    assert resultat["date_evenement"] == "2026-10-01"
    assert resultat["date_publication"] is None
    assert resultat["classe_temporelle"] == "date_publication_inconnue"
    assert resultat["statut_preuve"] == "correspondance_scdl_non_qualifiee"


def test_date_de_deliberation_calendairement_invalide_est_refusee():
    fictif = {**piste(), "deliberation_date": "2026-02-30"}
    with pytest.raises(PolitiqueInvalide, match="Date de délibération"):
        preparer_revue({"observations": []}, {"pistes": [fictif]}, MAINTENANT)
