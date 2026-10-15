"""Essais SQL et collecteur CSP sans requêtes au réseau."""
from datetime import datetime, timezone
import hashlib
import json

import pytest

from app.collecteur_emplois_continu import cycle
from app.plateforme_emplois import (
    ImportEmploisInvalide, StockageEmplois,
)
from scripts.extraire_offres_publiques import publier

DATE = "2026-10-14T10:00:00+00:00"
RESSOURCE = "source-officielle-test"
URL = "https://static.data.gouv.fr/resources/test/2026/offres.csv"


def offre(reference: str, titre: str) -> dict:
    contenu = {
        "reference": reference, "intitule": titre,
        "organisme": "Ministère des sciences", "employeur": "Ministère",
        "metier": "Ingénierie scientifique",
        "localisation": "Paris",
        "competences_attendues": "Traitement des données",
        "champs_tronques": [],
    }
    cle = hashlib.sha256(json.dumps(
        contenu, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    return {**contenu, "cle_enregistrement": cle}


def creer_cliche(racine, offres, *, sha="a" * 64,
                 source=RESSOURCE, date=DATE):
    objets = {obj["cle_enregistrement"]: obj for obj in offres}
    manifeste = {
        "version": "emplois-publics-extraits-v1",
        "source_id": source, "source_modifie_le": date,
        "source_url": URL, "sha256_csv": sha,
        "extraire_le": date, "offres_distinctes": len(objets),
    }
    publier(objets, racine, manifeste)
    return json.loads((racine / "manifest_offres_postes.json").read_text(encoding="utf-8"))


def stockage(tmp_path):
    return StockageEmplois("sqlite:///" + str(tmp_path / "base.sqlite3"))


def test_importer_cliche_et_rechercher_references_identiques(tmp_path):
    fichier = tmp_path / "fichiers"
    creer_cliche(fichier, [offre("R-01", "Calcul quantique"),
                           offre("R-01", "Traitement statistique"),
                           offre("R-02", "Technicien réseau")])
    base = stockage(tmp_path)
    r = base.importer(fichier)
    assert r["etat"] == "importe"
    assert r["offres_du_dernier_cliche"] == 3
    assert r["variantes_historiques"] == 3
    assert len(base.rechercher("scientifique")) == 3
    assert {x["intitule"] for x in base.rechercher("Réseau")} == {"Technicien réseau"}
    assert base.importer(fichier)["etat"] == "deja_importe"
    assert base.etat()["captures"] == 1
    assert base.rechercher("%") == []


def test_changements_et_historique_avec_deux_cliches(tmp_path):
    fichier = tmp_path / "fichiers"
    base = stockage(tmp_path)
    creer_cliche(fichier, [offre("R-01", "Chercheur A")])
    base.importer(fichier)
    creer_cliche(fichier, [offre("R-01", "Chercheur B"),
                           offre("R-02", "Chercheur C")],
                 sha="b" * 64, date="2026-10-15T10:00:00+00:00")
    r = base.importer(fichier)
    assert r["captures"] == 2
    assert r["variantes_historiques"] == 3
    assert r["offres_du_dernier_cliche"] == 2
    assert len(base.rechercher("Chercheur")) == 2
    assert all(x["intitule"] != "Chercheur A" for x in base.rechercher("Chercheur"))


def test_signature_de_partition_incorrecte_annule_transaction(tmp_path):
    fichier = tmp_path / "fichiers"
    manifeste = creer_cliche(fichier, [offre("R-01", "Physique")])
    cible = fichier / "offres_postes" / "lot_0f.jsonl"
    with cible.open("ab") as f:
        f.write(b"\n")
    base = stockage(tmp_path)
    with pytest.raises(ImportEmploisInvalide, match="Empreinte"):
        base.importer(fichier)
    assert base.etat()["captures"] == 0
    assert base.etat()["variantes_historiques"] == 0


def test_empreinte_offre_modifiee_refusee_meme_si_partition_resignee(tmp_path):
    fichier = tmp_path / "fichiers"
    man = creer_cliche(fichier, [offre("R-01", "Biologie")])
    nom = next(n for n in man["empreintes_partitions"]
               if (fichier / "offres_postes" / n).stat().st_size > 0)
    chemin = fichier / "offres_postes" / nom
    ligne = json.loads(chemin.read_text(encoding="utf-8"))
    ligne["intitule"] = "Titre modifié sans nouvelle empreinte"
    contenu = json.dumps(ligne, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")) + "\n"
    chemin.write_text(contenu, encoding="utf-8")
    man["empreintes_partitions"][nom] = hashlib.sha256(
        contenu.encode("utf-8")
    ).hexdigest()
    (fichier / "manifest_offres_postes.json").write_text(json.dumps(man), encoding="utf-8")
    base = stockage(tmp_path)
    with pytest.raises(ImportEmploisInvalide, match="Contenu d'offre"):
        base.importer(fichier)
    assert base.etat()["captures"] == 0


def test_manifest_faux_ou_tronque_refuse(tmp_path):
    fichier = tmp_path / "fichiers"
    man = creer_cliche(fichier, [offre("R-01", "Chimie")])
    man["offres_distinctes"] = 500
    (fichier / "manifest_offres_postes.json").write_text(json.dumps(man), encoding="utf-8")
    base = stockage(tmp_path)
    with pytest.raises(ImportEmploisInvalide, match="Nombre"):
        base.importer(fichier)
    assert base.etat()["captures"] == 0


def test_collecteur_reutilise_cliche_sans_retelecharger(tmp_path):
    dossier = tmp_path / "csp"
    creer_cliche(dossier, [offre("R-01", "Technologies")])
    base = stockage(tmp_path)

    def faux_catalogue(*, maintenant):
        return ({
            "version": "ressources-emplois-publics-v1",
            "licence_declaree": "lov2",
            "jeu": "Choisir le service public",
            "ressources": [{
                "id": RESSOURCE, "url": URL, "format": "csv",
                "modifie_le": DATE, "titre": "offres.csv",
            }],
        }, {"controle_le": DATE})

    def interdit(*args, **kwargs):
        raise AssertionError("Le fichier CSV inchangé ne doit pas être retéléchargé.")

    r = cycle(base, dossier, maintenant=datetime.fromisoformat(DATE),
              relever=faux_catalogue, sonder=interdit, extraction=interdit)
    assert r["extraction"] == "inchangé"
    assert r["base"] == "importe"
    assert r["offres_du_dernier_cliche"] == 1
    r2 = cycle(base, dossier, maintenant=datetime.fromisoformat(DATE),
               relever=faux_catalogue, sonder=interdit, extraction=interdit)
    assert r2["base"] == "deja_importe"


def test_nouvelle_version_declenche_extraction_et_conservation(tmp_path):
    dossier = tmp_path / "csp"
    base = stockage(tmp_path)
    observation = "2026-10-15T12:00:00+00:00"
    def catalogue(*, maintenant):
        return ({
            "licence_declaree": "lov2",
            "jeu": "CSP",
            "ressources": [{
                "id": "nouveau-fichier", "url": URL, "format": "csv",
                "modifie_le": observation, "titre": "offres.csv"
            }]
        }, {"controle_le": observation})
    def sonde(_url):
        return {"separateur": "point-virgule", "colonnes": ["Référence"],
                "nombre_colonnes": 1}
    def extraction(racine):
        schema = json.loads((racine / "schema_emplois_publics.json").read_text(encoding="utf-8"))
        assert schema["source_id"] == "nouveau-fichier"
        creer_cliche(racine, [offre("R-03", "Géophysique")],
                     source="nouveau-fichier", sha="b" * 64, date=observation)
        return {"etat": "actualisé"}
    r = cycle(base, dossier, maintenant=datetime.fromisoformat(observation),
              relever=catalogue, sonder=sonde, extraction=extraction)
    assert r["base"] == "importe"
    assert r["offres_du_dernier_cliche"] == 1
    assert base.rechercher("Géophysique")


def test_date_manquante_et_champ_invalide_ne_sont_pas_indices(tmp_path):
    dossier = tmp_path / "csp"
    man = creer_cliche(dossier, [offre("R-01", "Astronomie")])
    del man["extraire_le"]
    (dossier / "manifest_offres_postes.json").write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(ImportEmploisInvalide, match="Date"):
        stockage(tmp_path).importer(dossier)
