"""Contrôles hors connexion du suivi des modifications rétroactives BOAMP."""
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.collecter_historique_boamp import chemins_jour, publier_jour
from scripts.collecter_besoins_publics import notice_boamp
from scripts.surveiller_revisions_boamp import (
    RelectureInvalide, choisir_jours, repertoires_revision, surveiller,
)


def annonce(identifiant, jour, objet="Analyse de la ressource en eau"):
    return {
        "idweb": identifiant,
        "dateparution": jour,
        "objet": objet,
        "nomacheteur": "Administration fictive",
        "type_marche": "SERVICES",
        "etat": "INITIAL",
        "url_avis": f"https://www.boamp.fr/avis/{identifiant}",
        "email": "personne@example.org",
    }


def archive_initiale(dossier, jour, avis):
    return publier_jour(
        dossier, date.fromisoformat(jour),
        [notice_boamp(x) for x in avis], len(avis),
        datetime(2026, 10, 8, tzinfo=timezone.utc),
    )


def api_jours(valeurs):
    def obtenir(url, origine):
        params = parse_qs(urlparse(url).query)
        jour = params["where"][0].split('"')[1]
        offset, taille = int(params["offset"][0]), int(params["limit"][0])
        contenus = valeurs[jour]
        return {
            "total_count": len(contenus),
            "results": contenus[offset:offset + taille],
        }
    return obtenir


def test_deux_jours_identiques_et_cursor_rotatif(tmp_path):
    jours = ["2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01"]
    valeurs = {j: [annonce(f"26-{j}", j)] for j in jours}
    for jour in jours:
        archive_initiale(tmp_path, jour, valeurs[jour])
    fiches = sorted((tmp_path / "historique_boamp").glob("20??/??/20??-??-??.json"))
    choisis, cursor = choisir_jours(fiches, "2026-10-01", recents=1, rotation=2)
    assert [x.stem for x in choisis] == ["2026-09-28", "2026-09-29", "2026-10-01"]
    assert cursor == "2026-09-29"
    bilan = surveiller(tmp_path, obtenir=api_jours(valeurs), patienter=lambda x: None,
                       instant=datetime(2026, 10, 9, tzinfo=timezone.utc),
                       recents=1, rotation=2)
    assert bilan["jours_controles"] == 3
    assert bilan["jours_avec_variation"] == 0
    assert bilan["nouvelles_revisions_archivees"] == 0
    assert bilan["dernier_jour_relecture_circulaire"] == "2026-09-29"
    suite = surveiller(tmp_path, obtenir=api_jours(valeurs), patienter=lambda x: None,
                       instant=datetime(2026, 10, 9, tzinfo=timezone.utc),
                       recents=1, rotation=2)
    assert suite["jours_controles"] == 3
    assert [x["jour"] for x in suite["controles"]] == [
        "2026-09-30", "2026-10-01",
    ]


def test_changement_documente_avec_octets_et_identifiants(tmp_path):
    jour = "2026-10-01"
    original = [
        annonce("26-100", jour, "Etude hydrologique"),
        annonce("26-101", jour, "Expertise écologique"),
    ]
    corrige = [
        annonce("26-100", jour, "Etude hydrologique modifiée"),
        annonce("26-102", jour, "Mesures de bassin"),
    ]
    archive_initiale(tmp_path, jour, original)
    un = surveiller(tmp_path, obtenir=api_jours({jour: corrige}),
                    patienter=lambda x: None,
                    instant=datetime(2026, 10, 9, tzinfo=timezone.utc))
    assert un["jours_controles"] == 1
    assert un["jours_avec_variation"] == 1
    assert un["nouvelles_revisions_archivees"] == 1
    c = un["controles"][0]
    assert (c["ajoutes"], c["absents"], c["modifies"]) == (1, 1, 1)
    originale, _ = chemins_jour(tmp_path, date.fromisoformat(jour))
    assert len(gzip.decompress(originale.read_bytes()).splitlines()) == 2
    nouveaux = list((tmp_path / "revisions_boamp").glob("**/*.jsonl.gz"))
    assert len(nouveaux) == 1
    fiche = nouveaux[0].with_suffix("").with_suffix(".json")
    manifeste = json.loads(fiche.read_text(encoding="utf-8"))
    assert manifeste["identifiants_ajoutes"] == ["26-102"]
    assert manifeste["identifiants_absents_du_releve"] == ["26-101"]
    assert manifeste["identifiants_modifies"] == ["26-100"]
    assert "personne@example.org" not in str(manifeste)
    assert hashlib.sha256(nouveaux[0].read_bytes()).hexdigest() == manifeste["cliche_revise_sha256_gzip"]
    autre = surveiller(tmp_path, obtenir=api_jours({jour: corrige}),
                       patienter=lambda x: None)
    assert autre["nouvelles_revisions_archivees"] == 0
    assert autre["controles"][0]["revision_deja_conservee"] is True


def test_refus_d_une_relecture_partielle(tmp_path):
    jour = "2026-10-01"
    archive_initiale(tmp_path, jour, [annonce("26-1", jour)])
    def panne(url, source):
        raise OSError("Indisponibilité simulée")
    with pytest.raises(RelectureInvalide, match="Aucune journée"):
        surveiller(tmp_path, obtenir=panne, patienter=lambda x: None)
    assert not (tmp_path / "etat_revisions_boamp.json").exists()
    assert not list((tmp_path / "revisions_boamp").glob("**/*"))


def test_rejet_d_une_revision_alteree(tmp_path):
    jour = "2026-10-01"
    archive_initiale(tmp_path, jour, [annonce("26-1", jour)])
    modification = {jour: [annonce("26-1", jour, "Avis corrigé")]}
    surveiller(tmp_path, obtenir=api_jours(modification), patienter=lambda x: None)
    archive = next((tmp_path / "revisions_boamp").glob("**/*.jsonl.gz"))
    archive.write_bytes(b"archive falsifiee")
    with pytest.raises(RelectureInvalide, match="Aucune journée"):
        surveiller(tmp_path, obtenir=api_jours(modification), patienter=lambda x: None)


def test_bornes_jour_et_limites(tmp_path):
    with pytest.raises(RelectureInvalide):
        repertoires_revision(tmp_path, "../../fuite", "a" * 64)
    with pytest.raises(RelectureInvalide):
        choisir_jours([Path("2026-10-01.json")], None, rotation=11)
