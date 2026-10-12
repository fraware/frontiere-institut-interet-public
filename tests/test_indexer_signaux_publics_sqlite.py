"""Essais de la base de signaux publique, sans réseau ni base institutionnelle."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from scripts.indexer_signaux_publics_sqlite import (
    IndexInvalide, importer, rechercher, verifier_donnees,
)


def config():
    return json.loads(
        Path("institutionnel/flux_publics/sources_v1.json").read_text(encoding="utf-8")
    )


def _observation(titre="Recrutement ingénieur scientifique", index=1):
    return {
        "identifiant_publication": hashlib.sha256(str(index).encode()).hexdigest(),
        "source_id": "anr_appels",
        "titre": titre,
        "description": "Appel public pour un programme technologique",
        "lien": "https://anr.fr/fr/detail/test/",
        "date_publication": "2026-10-12T09:00:00+00:00",
        "nature_signal": "publication_publique_non_qualifiee",
        "observe_initialement_le": "2026-10-12T10:00:00+00:00",
        "mis_a_jour_le": "2026-10-12T10:00:00+00:00",
        "empreinte_contenu": hashlib.sha256(titre.encode()).hexdigest(),
        "nombre_revisions": 0,
    }


def index(lignes=None):
    return {"version": 1, "observations": [_observation()] if lignes is None else lignes}


def test_importation_idempotente_et_recherche(tmp_path):
    base = tmp_path / "publications.sqlite3"
    premier = importer(base, config(), index())
    assert premier["ajouts"] == 1
    assert premier["publications_indexees"] == 1
    assert not premier["couverture_exhaustive"]
    second = importer(base, config(), index())
    assert second["ajouts"] == 0
    assert second["inchanges"] == 1
    resultats = rechercher(base, "scientifique")
    assert len(resultats) == 1
    assert resultats[0]["source_id"] == "anr_appels"
    assert rechercher(base, "scientifique", source="anr_bluesky") == []


def test_modification_persiste_et_date_initiale_est_conservee(tmp_path):
    base = tmp_path / "publications.sqlite3"
    d = index()
    importer(base, config(), d)
    nouveau = deepcopy(d)
    o = nouveau["observations"][0]
    o["titre"] = "Recrutement ingénieur quantique"
    o["empreinte_contenu"] = hashlib.sha256(o["titre"].encode()).hexdigest()
    o["mis_a_jour_le"] = "2026-10-12T11:00:00+00:00"
    o["nombre_revisions"] = 1
    resultat = importer(base, config(), nouveau)
    assert resultat["modifications"] == 1
    assert rechercher(base, "scientifique") == []
    ligne = rechercher(base, "quantique")[0]
    assert ligne["observe_initialement_le"] == "2026-10-12T10:00:00+00:00"


def test_source_absente_et_deux_identifiants_identiques_refuses():
    mauvais = index()
    mauvais["observations"][0]["source_id"] = "entite_inconnue"
    with pytest.raises(IndexInvalide):
        verifier_donnees(config(), mauvais)
    p = _observation()
    with pytest.raises(IndexInvalide):
        verifier_donnees(config(), index([p, deepcopy(p)]))


@pytest.mark.parametrize("champ,valeur", [
    ("nature_signal", "mission_certaine"),
    ("date_publication", "non date"),
    ("lien", "http://127.0.0.1/"),
    ("nombre_revisions", -1),
    ("empreinte_contenu", "invalide"),
])
def test_champs_faux_refuses(champ, valeur):
    d = index()
    d["observations"][0][champ] = valeur
    with pytest.raises(IndexInvalide):
        verifier_donnees(config(), d)


def test_etat_ancien_non_remplace_par_une_revision_plus_ancienne(tmp_path):
    base = tmp_path / "publications.sqlite3"
    ancien = index()
    importer(base, config(), ancien)
    recent = deepcopy(ancien)
    ligne = recent["observations"][0]
    ligne["titre"] = "Recrutement ingénieur quantique"
    ligne["empreinte_contenu"] = hashlib.sha256(ligne["titre"].encode()).hexdigest()
    ligne["mis_a_jour_le"] = "2026-10-12T11:00:00+00:00"
    importer(base, config(), recent)
    plus_vieux = deepcopy(ancien)
    ligne = plus_vieux["observations"][0]
    ligne["titre"] = "Recrutement expert optique"
    ligne["empreinte_contenu"] = hashlib.sha256(ligne["titre"].encode()).hexdigest()
    with pytest.raises(IndexInvalide):
        importer(base, config(), plus_vieux)
    assert len(rechercher(base, "quantique")) == 1
    assert rechercher(base, "optique") == []


def test_recherche_sans_base_et_limites(tmp_path):
    base = tmp_path / "sans-base.sqlite3"
    with pytest.raises(IndexInvalide):
        rechercher(base, "scientifique")
    importer(base, config(), index())
    with pytest.raises(IndexInvalide):
        rechercher(base, "")
    with pytest.raises(IndexInvalide):
        rechercher(base, "scientifique", limite=0)


def test_index_public_reel_si_disponible(tmp_path):
    chemin = Path("institutionnel/flux_publics/observations.json")
    if not chemin.is_file():
        pytest.skip("Premier relevé publié non disponible")
    document = json.loads(chemin.read_text(encoding="utf-8"))
    attendu = len(document["observations"])
    resultat = importer(tmp_path / "observations.sqlite3", config(), document)
    assert attendu > 0
    assert resultat["publications_indexees"] == attendu
