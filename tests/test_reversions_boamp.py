"""Conserver les retours à un état ancien sans effacer la correction intermédiaire."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.collecter_besoins_publics import notice_boamp
from scripts.collecter_historique_boamp import chemins_jour, publier_jour
from scripts.surveiller_revisions_boamp import surveiller
from scripts.rechercher_historique_boamp import indexer, chercher, ArchiveIncoherente


JOUR = "2026-10-01"


def annonce(identifiant, objet):
    return {
        "idweb": identifiant, "dateparution": JOUR, "objet": objet,
        "nomacheteur": "Institution scientifique fictive",
        "type_marche": "SERVICES", "etat": "INITIAL",
        "url_avis": f"https://www.boamp.fr/avis/{identifiant}",
    }


def reponse(annonces):
    def obtenir(url, origine):
        params = parse_qs(urlparse(url).query)
        assert JOUR in params["where"][0]
        offset = int(params["offset"][0])
        limit = int(params["limit"][0])
        return {
            "total_count": len(annonces),
            "results": annonces[offset:offset + limit],
        }
    return obtenir


def base(tmp_path):
    source = tmp_path / "sources"
    index = tmp_path / "index.sqlite3"
    initiale = annonce("26-100", "Étude hydrologique initiale")
    publier_jour(
        source, date.fromisoformat(JOUR), [notice_boamp(initiale)], 1,
        datetime(2026, 10, 9, tzinfo=timezone.utc),
    )
    return source, index, initiale


def test_modification_puis_retour_initial_archive_et_index(tmp_path):
    source, index, original = base(tmp_path)
    modifiee = annonce("26-100", "Modélisation sismique corrigée")
    t1 = datetime(2026, 10, 10, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 11, tzinfo=timezone.utc)
    b1 = surveiller(source, obtenir=reponse([modifiee]), patienter=lambda n: None,
                   instant=t1, recents=1, rotation=1)
    assert b1["jours_avec_variation"] == 1
    assert b1["retours_au_releve_initial"] == 0
    assert b1["nouvelles_revisions_archivees"] == 1
    assert indexer(source, index)["nombre_versions_corrigees_verifiees"] == 1
    assert chercher(index, "sismique")["total_candidats"] == 1

    b2 = surveiller(source, obtenir=reponse([original]), patienter=lambda n: None,
                   instant=t2, recents=1, rotation=1)
    assert b2["jours_avec_variation"] == 1
    assert b2["retours_au_releve_initial"] == 1
    assert b2["nouvelles_revisions_archivees"] == 0
    assert b2["controles"][0]["retour_releve_initial"] is True
    assert len(b2["changements_observes"]) == 2
    assert b2["changements_observes"][-1]["retour_releve_initial"] is True

    resultat = indexer(source, index)
    assert resultat["nombre_jours_indexes"] == 1
    assert resultat["nombre_avis_indexes"] == 1
    assert resultat["nombre_versions_corrigees_verifiees"] == 1
    assert resultat["retours_au_releve_initial_retenus"] == 1
    assert chercher(index, "sismique")["total_candidats"] == 0
    avant = chercher(index, "hydrologique")
    assert avant["total_candidats"] == 1
    assert "historique_boamp" in avant["resultats"][0]["archive_source"]
    assert avant["resultats"][0]["releve_le"].startswith("2026-10-11")
    # La correction reste disponible comme état antérieur.
    assert len(list((source / "revisions_boamp").glob("**/*.jsonl.gz"))) == 1
    assert len(list((source / "revisions_boamp").glob("**/*.json"))) == 1

    b3 = surveiller(
        source, obtenir=reponse([original]), patienter=lambda n: None,
        instant=datetime(2026, 10, 12, tzinfo=timezone.utc),
        recents=1, rotation=1,
    )
    assert b3["jours_avec_variation"] == 0
    assert len(b3["changements_observes"]) == 2


def test_empreinte_observee_sans_archive_verifiee_refusee(tmp_path):
    source, index, original = base(tmp_path)
    indexer(source, index)
    surveiller(
        source, obtenir=reponse([original]), patienter=lambda n: None,
        instant=datetime(2026, 10, 10, tzinfo=timezone.utc),
        recents=1, rotation=1,
    )
    etat = source / "etat_revisions_boamp.json"
    contenu = json.loads(etat.read_text(encoding="utf-8"))
    contenu["etat_connu_par_jour"][JOUR]["sha256_gzip"] = "a" * 64
    etat.write_text(json.dumps(contenu), encoding="utf-8")
    with pytest.raises(ArchiveIncoherente, match="sans archive vérifiée"):
        indexer(source, index)
    assert chercher(index, "hydrologique")["total_candidats"] == 1


def test_reprise_sans_curseur_retrouve_revision_anterieure(tmp_path):
    source, index, original = base(tmp_path)
    b1 = surveiller(
        source, obtenir=reponse([annonce("26-100", "Données corrigées")]),
        patienter=lambda n: None, instant=datetime(2026, 10, 10, tzinfo=timezone.utc),
        recents=1, rotation=1,
    )
    (source / "etat_revisions_boamp.json").unlink()
    # Reconstituer le dernier état archivé avant de détecter le retour.
    b2 = surveiller(
        source, obtenir=reponse([original]), patienter=lambda n: None,
        instant=datetime(2026, 10, 11, tzinfo=timezone.utc),
        recents=1, rotation=1,
    )
    assert b2["retours_au_releve_initial"] == 1
    assert b2["changements_observes"][-1]["retour_releve_initial"] is True
    assert indexer(source, index)["retours_au_releve_initial_retenus"] == 1
