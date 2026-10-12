"""Contrôles du relevé d'épreuve sur réponses synthétiques."""
import hashlib
import json

import pytest
import scripts.relever_ensemble_epreuve_infructueux_boamp as module
from scripts.collecter_notices_pilotes_boamp import adresse


def registre(tmp_path, monkeypatch):
    lignes, n = [], 42000
    for m in module.MOIS:
        for _ in range(module.QUOTA):
            lignes.append({"avis": f"26-{n}", "date_parution": m + "-18"})
            n += 1
    ids = [x["avis"] for x in lignes]
    sha = hashlib.sha256(json.dumps(
        ids, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()
    monkeypatch.setattr(module, "EMPREINTE_BASE", "1" * 64)
    chemin = tmp_path / "tirage.json"
    chemin.write_text(json.dumps({
        "version": module.VERSION_TIRAGE,
        "sha256_tirage_original": "1" * 64,
        "issues_verifiees_par_lot": False,
        "ensemble_representatif": False,
        "cas": lignes,
        "sha256_identifiants_ordonnes": sha,
    }))
    return chemin, lignes


def avis(code, date):
    return json.dumps({
        "total_count": 1,
        "results": [{"idweb": code, "dateparution": date,
                     "nature": "APPEL_OFFRE", "donnees": None}]
    }).encode()


def test_releve_24_consultations_toujours_indeterminees(tmp_path, monkeypatch):
    chemin, lignes = registre(tmp_path, monkeypatch)
    reponses = {x["avis"]: avis(x["avis"], x["date_parution"]) for x in lignes}
    def obtenir(url):
        return next(v for k, v in reponses.items() if url == adresse(k))
    dossier = tmp_path / "sortie"
    bilan = module.relever(chemin, dossier, obtenir=obtenir)
    assert bilan["nombre_avis"] == 24
    assert bilan["statuts"] == {"avis_observe_sans_resultat_attribution": 24}
    assert bilan["prequalifications_par_lot"] == {}
    assert bilan["comparaison_avec_les_36_cas_realisee"] is False
    assert all(x["resultats_lots"] == [] for x in bilan["cas"])
    assert len(list(dossier.glob("26-*.json"))) == 24
    with pytest.raises(module.EpreuveInvalide, match="existante"):
        module.relever(chemin, dossier, obtenir=obtenir)


def test_empreinte_incoherente_refusee(tmp_path, monkeypatch):
    chemin, _ = registre(tmp_path, monkeypatch)
    contenu = json.loads(chemin.read_text())
    contenu["cas"][0]["avis"] = "26-30147"
    chemin.write_text(json.dumps(contenu))
    with pytest.raises(module.EpreuveInvalide, match="modifié"):
        module.charger(chemin)


def test_resultat_absent_n_est_jamais_une_absence_offre(tmp_path, monkeypatch):
    chemin, lignes = registre(tmp_path, monkeypatch)
    def obtenir(url):
        return b'{"total_count":0,"results":[]}'
    bilan = module.relever(chemin, tmp_path / "releve", obtenir=obtenir)
    assert bilan["statuts"] == {"non_retrouve_lors_du_releve": 24}
    assert bilan["prequalifications_par_lot"] == {}
