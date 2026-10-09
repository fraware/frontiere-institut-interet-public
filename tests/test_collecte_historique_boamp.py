"""Vérifications de la collecte historique officielle, sans requête réseau."""
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.collecter_historique_boamp import (
    HistoriqueIncomplet, adresse_jour, executer, lire_jour, chemins_jour,
    publier_jour, serialiser,
)


def annoncer(identifiant, jour):
    return {
        "idweb": identifiant,
        "objet": "Analyse scientifique sur données publiques",
        "nomacheteur": "Administration fictive",
        "dateparution": jour,
        "datelimitereponse": "2026-12-01",
        "type_marche": "SERVICES",
        "etat": "INITIAL",
        "url_avis": "https://www.boamp.fr/avis/" + identifiant,
        "contact": "personne@example.org",
    }


def test_adresse_jour_bornee_et_deterministe():
    url = adresse_jour(date(2026, 10, 1), 2)
    args = parse_qs(urlparse(url).query)
    assert args["where"] == ['dateparution >= "2026-10-01" AND dateparution < "2026-10-02"']
    assert args["offset"] == ["200"]
    assert args["order_by"] == ["idweb asc"]
    assert "select" in args and "contact" not in args["select"][0]
    with pytest.raises(HistoriqueIncomplet):
        adresse_jour(date(2026, 10, 1), 50)


def test_collecte_toutes_les_pages_d_une_journee_sans_contacts():
    appels = []
    def api(url, origine):
        appels.append(url)
        q = parse_qs(urlparse(url).query)
        jour = q["where"][0].split('"')[1]
        decalage = int(q["offset"][0])
        lignes = [annoncer(f"26-{i:05d}", jour) for i in range(decalage, min(4, decalage + 2))]
        return {"total_count": 4, "results": lignes}
    lignes, total = lire_jour(date(2026, 10, 1), obtenir=api,
                             patienter=lambda n: None, taille=2)
    assert total == len(lignes) == 4
    assert len(appels) == 2
    assert "personne@example.org" not in str(lignes)
    archive, empreinte = serialiser(lignes)
    assert gzip.decompress(archive).count(b"\n") == 4
    assert hashlib.sha256(gzip.decompress(archive)).hexdigest() == empreinte
    assert serialiser(lignes)[0] == archive


@pytest.mark.parametrize("genre", ["page_manquante", "total_change", "mauvaise_date",
                                    "identifiant_duplique", "trop_nombreux"])
def test_refus_explicite_des_journees_incertaines(genre):
    def api(url, _origine):
        args = parse_qs(urlparse(url).query)
        decalage = int(args["offset"][0])
        jour = args["where"][0].split('"')[1]
        if genre == "trop_nombreux":
            return {"total_count": 6000, "results": [annoncer("26-1", jour)]}
        if decalage == 0:
            return {"total_count": 3, "results": [annoncer("26-1", jour), annoncer("26-2", jour)]}
        if genre == "page_manquante":
            return {"total_count": 3, "results": []}
        if genre == "total_change":
            return {"total_count": 4, "results": [annoncer("26-3", jour)]}
        if genre == "mauvaise_date":
            return {"total_count": 3, "results": [annoncer("26-3", "2024-01-01")]}
        return {"total_count": 3, "results": [annoncer("26-1", jour)]}
    with pytest.raises(HistoriqueIncomplet):
        lire_jour(date(2026, 10, 1), obtenir=api, patienter=lambda n: None, taille=2)


def test_reprise_apres_une_journee_incomplete(tmp_path):
    instant = datetime(2026, 10, 9, 14, 0, tzinfo=timezone.utc)
    appels = []
    def api(url, _origine):
        q = parse_qs(urlparse(url).query)
        jour = q["where"][0].split('"')[1]
        appels.append(jour)
        if jour == "2026-09-30":
            raise OSError("Panne fictive")
        return {"total_count": 1, "results": [annoncer("26-" + jour, jour)]}
    bilan = executer(tmp_path, instant=instant, obtenir=api,
                     patienter=lambda n: None, jours_par_execution=4)
    assert bilan["jours_complets_cette_execution"] == 1
    assert bilan["jour_suivant_a_relever"] == "2026-09-30"
    assert bilan["erreurs"][0]["jour"] == "2026-09-30"
    chemin, fiche = chemins_jour(tmp_path, date(2026, 10, 1))
    assert chemin.is_file() and fiche.is_file()
    preuve = json.loads(fiche.read_text(encoding="utf-8"))
    assert preuve["avis_distincts"] == 1
    assert preuve["pages_completes"] is True
    assert hashlib.sha256(chemin.read_bytes()).hexdigest() == preuve["sha256_archive_gzip"]
    assert gzip.decompress(chemin.read_bytes()).count(b"\n") == 1

    def repris(url, _origine):
        q = parse_qs(urlparse(url).query)
        jour = q["where"][0].split('"')[1]
        return {"total_count": 1, "results": [annoncer("26-" + jour, jour)]}
    nouveau = executer(tmp_path, instant=instant, obtenir=repris,
                       patienter=lambda n: None, jours_par_execution=1)
    assert nouveau["jour_initial_cette_execution"] == "2026-09-30"
    assert nouveau["jour_suivant_a_relever"] == "2026-09-29"
    assert chemins_jour(tmp_path, date(2026, 9, 30))[0].is_file()


def test_refus_curseur_invalide_et_archive_alteree(tmp_path):
    instant = datetime(2026, 10, 9, tzinfo=timezone.utc)
    (tmp_path / "etat_historique_boamp.json").write_text(
        json.dumps({"jour_suivant_a_relever": "../interdit"}), encoding="utf-8",
    )
    with pytest.raises(HistoriqueIncomplet, match="mal formé"):
        executer(tmp_path, instant=instant, obtenir=lambda *a: {})
    jour = date(2026, 10, 1)
    publier_jour(tmp_path, jour, [{"id": "exemple", "date_parution": jour.isoformat()}],
                 1, instant)
    p, _ = chemins_jour(tmp_path, jour)
    p.write_bytes(b"fichier altere")
    with pytest.raises(HistoriqueIncomplet, match="altérées"):
        publier_jour(tmp_path, jour, [], 0, instant)



def test_lot_de_vingt_quatre_jours_et_plafond_explicite(tmp_path):
    instant = datetime(2026, 10, 9, tzinfo=timezone.utc)
    def api(url, _origine):
        return {"total_count": 0, "results": []}
    bilan = executer(tmp_path, instant=instant, obtenir=api,
                     patienter=lambda n: None, jours_par_execution=24)
    assert bilan["jours_complets_cette_execution"] == 24
    assert bilan["avis_distincts_cette_execution"] == 0
    assert bilan["jour_suivant_a_relever"] == "2026-09-07"
    with pytest.raises(HistoriqueIncomplet, match="incorrect"):
        executer(tmp_path, instant=instant, obtenir=api,
                 patienter=lambda n: None, jours_par_execution=25)
