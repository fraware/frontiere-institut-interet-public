"""Vérifier les dénominateurs des catégories réobservées sans reconstruire leur origine."""
from datetime import date, datetime, timezone
import hashlib
import json
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.collecter_besoins_publics import notice_boamp
from scripts.collecter_historique_boamp import chemins_jour, publier_jour
from scripts.rechercher_historique_boamp import indexer
from scripts.completer_categories_boamp import completer_jour, chemins
from scripts.analyser_complements_categories_boamp import analyser, ecrire, BilanInvalide


def originale(id, jour, categorie):
    return {
        "idweb": id, "dateparution": jour, "type_marche": categorie,
        "objet": "Recherche sur les eaux", "etat": "INITIAL",
        "nomacheteur": "Établissement fictif",
        "url_avis": f"https://www.boamp.fr/avis/{id}",
    }


def donnees(tmp_path):
    base = tmp_path / "sources"
    index = tmp_path / "recherche.sqlite3"
    preuve = tmp_path / "preuve.json"
    t0 = datetime(2026, 10, 8, tzinfo=timezone.utc)
    for jour, ids in [
        ("2026-10-01", ["26-100", "26-101"]),
        ("2026-10-02", ["26-102"]),
    ]:
        items = [notice_boamp(originale(id, jour, ["SERVICES"])) for id in ids]
        publier_jour(base, date.fromisoformat(jour), items, len(items), t0)
    b = indexer(base, index)
    preuve.write_text(json.dumps({
        "version": "publication-index-boamp-v1",
        "revision_depot": "a" * 40,
        "sha256_index": hashlib.sha256(index.read_bytes()).hexdigest(),
        "jours_indexes": b["nombre_jours_indexes"],
        "avis_indexes": b["nombre_avis_indexes"],
    }), encoding="utf-8")
    return base, index, preuve


def relecture(jour, records):
    def obtenir(url, origine):
        q = parse_qs(urlparse(url).query)
        assert jour in q["where"][0]
        start, taille = int(q["offset"][0]), int(q["limit"][0])
        return {
            "total_count": len(records),
            "results": records[start:start + taille],
        }
    return obtenir


def test_qualite_sans_complement_signale_100_pourcent_absent(tmp_path):
    base, index, preuve = donnees(tmp_path)
    rapport = analyser(index, preuve, base)
    assert rapport["jours_archives_au_total"] == 2
    assert rapport["avis_de_l_index"] == 3
    assert rapport["jours_avec_complements_verifies"] == 0
    assert rapport["identifiants_initiaux_sans_complement"] == 3
    assert rapport["categories_retrouvees_lors_des_recontroles"] == 0
    assert rapport["categorie_a_la_date_de_publication_initiale_etablie"] is False


def test_qualite_recontrole_divergent_et_comparaison_mensuelle(tmp_path):
    base, index, preuve = donnees(tmp_path)
    jour = "2026-10-01"
    _gzip, fiche = chemins_jour(base, date.fromisoformat(jour))
    actuel = [
        originale("26-100", jour, ["FOURNITURES"]),
        originale("26-199", jour, ["SERVICES"]),
    ]
    completer_jour(
        base, fiche, obtenir=relecture(jour, actuel),
        instant=datetime(2026, 10, 11, tzinfo=timezone.utc),
        patienter=lambda _: None,
    )
    bilan = analyser(index, preuve, base)
    assert bilan["jours_avec_complements_verifies"] == 1
    assert bilan["identifiants_initiaux_couverts"] == 2
    assert bilan["identifiants_initiaux_sans_complement"] == 1
    assert bilan["categories_retrouvees_lors_des_recontroles"] == 1
    assert bilan["categories_non_retrouvees_parmi_identifiants_couverts"] == 1
    assert bilan["identifiants_absents_au_recontrole"] == 1
    assert bilan["identifiants_nouveaux_au_recontrole"] == 1
    assert bilan["nombre_instants_de_controle_distincts"] == 1
    assert bilan["mesures_par_mois"][0]["avis_initiaux_archives"] == 3
    assert bilan["mesures_par_mois"][0]["couverture_des_identifiants_archives"] == 0.666667
    fichier = tmp_path / "rapport.json"
    ecrire(bilan, fichier)
    assert json.loads(fichier.read_text(encoding="utf-8")) == bilan

    complement, _manifest = chemins(base, jour)
    complement.write_bytes(b"corrompu")
    with pytest.raises(BilanInvalide, match="Empreinte|Taille"):
        analyser(index, preuve, base)


def test_indice_altéré_refusé_avant_statistiques(tmp_path):
    base, index, preuve = donnees(tmp_path)
    contenu = json.loads(preuve.read_text(encoding="utf-8"))
    contenu["avis_indexes"] = 99
    preuve.write_text(json.dumps(contenu), encoding="utf-8")
    with pytest.raises(BilanInvalide):
        analyser(index, preuve, base)
