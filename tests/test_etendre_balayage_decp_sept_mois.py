"""Vérification hors réseau de sept ressources et du dédoublonnage intermensuel."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

import pytest

from scripts.balayer_fichiers_consolides_decp import analyser, choisir_ressources
from scripts.etendre_balayage_decp_sept_mois import (
    VERSION, ExtensionInvalide, IndexIntermois, MOIS_NOUVEAUX,
    executer, sources_anciennes,
)

ANCIENS = ("2025-08", "2026-02", "2026-04")
SIRET = "21060027600013"
AUTRE = "26310012500016"
REF = "25M034"
RIDS = [
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
    "33333333-3333-4333-8333-333333333333",
    "44444444-4444-4444-8444-444444444444",
]


def marche(siret: str, numero: str, objet="Prestation technique", offres="NC"):
    return {"_type": "Marché", "id": numero,
            "acheteur": {"id": siret}, "objet": objet,
            "offresRecues": offres, "dateNotification": "2025-08-15"}


def faire_fichier(path: Path, notices: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"marches": {"marche": notices, "contrat-concession": []}}
    path.write_text(json.dumps(data), encoding="utf-8")


def fabriquer(tmp_path: Path):
    chaines = tmp_path / "chaines.json"
    dossiers = []
    for i in range(17):
        contrats = ([{
            "reference_contrat_comparable_decp": True,
            "reference_contrat_declaree": REF if i == 0 else f"REF2025{i:04d}",
            "reference_locale": "CON-0001",
            "origine_reference_contrat": "/contrat/cbc:ID",
        }] if i < 7 else [])
        dossiers.append({
            "avis_boamp": f"25-{80000+i}",
            "siret_chiffres_sans_schema_boamp": SIRET,
            "contrats_locaux": contrats,
        })
    chaines.write_text(json.dumps({
        "version": "chaines-documentaires-acheteurs-17-avis-v1",
        "liaisons_contractuelles_decp_prouvees": 0,
        "nombre_siret_distincts": 16,
        "mesures": {"avis": 17, "references_contrat_comparables": 7},
        "dossiers": dossiers,
    }), encoding="utf-8")
    anciennes = tmp_path / "archives"
    originaux = []
    population = [
        [marche(SIRET, "INCHANGÉ")],
        [marche(SIRET, "INCHANGÉ"), marche(AUTRE, REF)],
        [marche(SIRET, "INCHANGÉ", objet="Variante déclarée")],
    ]
    for m, notices in zip(ANCIENS, population):
        chemin = anciennes / "fichiers-officiels" / f"decp-{m}.json"
        faire_fichier(chemin, notices)
        selection = {"titre": chemin.name, "taille_octets": chemin.stat().st_size,
                     "ressource_id": RIDS[0], "url": "https://static.data.gouv.fr/test.json",
                     "date_modification_declaree": "2026-10-13T00:00:00+00:00"}
        analyse = analyser(chemin, selection, {})
        originaux.append(analyse)
    (anciennes / "rapport.json").write_text(json.dumps({
        "version": "balayage-contrats-consolides-decp-v1",
        "mois_examines": list(ANCIENS), "nombre_fichiers_analyses": 3,
        "sources": originaux,
    }), encoding="utf-8")
    nouveaux = {}
    population_nouv = [
        [marche(SIRET, "INCHANGÉ"), marche(SIRET, REF)],
        [marche(SIRET, REF), marche(AUTRE, REF)],
        [marche(SIRET, "INCHANGÉ", objet="Variante déclarée")],
        [marche(SIRET, "UNIQUE2026"), marche(SIRET, REF, objet="Variante contrat")],
    ]
    for m, notices in zip(MOIS_NOUVEAUX, population_nouv):
        f = tmp_path / "originaux" / f"decp-{m}.json"
        faire_fichier(f, notices)
        nouveaux[f.name] = f
    ressources = []
    for i, (nom, path) in enumerate(nouveaux.items()):
        ressources.append({
            "titre": nom, "id": RIDS[i],
            "taille_octets_declaree": path.stat().st_size,
            "modifie_le": "2026-10-13T00:00:00+00:00",
            "format": "json",
        })
    etat = {"catalogues": [{
        "source_id": "mef_decp_consolides", "ressources_recentes": ressources,
    }]}
    fiche = {"resources": [{
        "id": r["id"], "title": r["titre"], "format": "json",
        "filesize": r["taille_octets_declaree"],
        "url": "https://static.data.gouv.fr/resources/" + r["titre"],
    } for r in ressources]}
    def recuperer(selection, fichier):
        fichier.write_bytes(nouveaux[selection["titre"]].read_bytes())
    return chaines, anciennes, etat, fiche, recuperer


def test_bilan_identites_et_variantes_independamment():
    index = IndexIntermois()
    a = {"acheteur_siret": SIRET, "id_marche": "X", "objet": "alpha"}
    index.observer(a, "janvier")
    index.observer(a, "février")
    index.observer({**a, "objet": "beta"}, "février")
    index.observer({**a, "objet": "beta"}, "mars")
    bilan = index.bilan()
    assert bilan["identites_distinctes_siret_et_id_marche"] == 1
    assert bilan["variantes_documentaires_distinctes"] == 2
    assert bilan["repetitions_de_variantes_identiques"] == 2
    assert bilan["identites_apparaissant_dans_plusieurs_mois"] == 1
    assert bilan["identites_avec_plusieurs_variantes"] == 1


def test_selection_parametree_pour_quatre_mois(tmp_path):
    _, _, etat, fiche, _ = fabriquer(tmp_path)
    selection = choisir_ressources(
        etat, fiche, mois=MOIS_NOUVEAUX,
        plafond_fichier=160_000_000, plafond_total=430_000_000,
    )
    assert [r["titre"] for r in selection] == [
        f"decp-{m}.json" for m in MOIS_NOUVEAUX
    ]
    with pytest.raises(ValueError, match="Périmètre"):
        choisir_ressources(etat, fiche, mois=("2025-10", "2025-10"))


def test_execution_sept_mois_conserve_deux_types_de_collision(tmp_path):
    chaines, anciennes, etat, fiche, recuperer = fabriquer(tmp_path)
    resultat = executer(
        chaines, anciennes, etat, fiche, tmp_path / "resultat",
        recuperer=recuperer,
    )
    assert resultat["version"] == VERSION
    assert resultat["nombre_fichiers_intacts_lus"] == 7
    assert resultat["statistiques"]["notices_normalisees"] == 11
    assert resultat["statistiques"]["offres_recues_non_communiquees_nc"] == 11
    assert resultat["dedoublonnage_intermois"]["identites_distinctes_siret_et_id_marche"] == 4
    assert resultat["dedoublonnage_intermois"]["variantes_documentaires_distinctes"] == 6
    assert resultat["dedoublonnage_intermois"]["repetitions_de_variantes_identiques"] == 5
    assert resultat["nombre_pistes_avec_siret_acheteur_identique"] == 1
    assert resultat["nombre_references_collisions_autres_acheteurs"] == 1
    matches = [x for x in resultat["pistes_documentaires"]
               if x["meme_siret_acheteur_boamp"]]
    assert matches[0]["mois_observes"] == [
        "decp-2025-10.json", "decp-2025-12.json", "decp-2026-05.json",
    ]
    assert matches[0]["contrat_juridiquement_identifie"] is False
    assert (tmp_path / "resultat" / "rapport.json").is_file()
    with pytest.raises(ExtensionInvalide, match="déjà présent"):
        executer(chaines, anciennes, etat, fiche, tmp_path / "resultat",
                 recuperer=recuperer)


def test_archive_historique_alteree_refusee(tmp_path):
    chaines, anciennes, etat, fiche, recuperer = fabriquer(tmp_path)
    a, _ = sources_anciennes(anciennes)
    f = anciennes / "fichiers-officiels" / "decp-2025-08.json"
    f.write_bytes(f.read_bytes() + b" ")
    with pytest.raises(ExtensionInvalide, match="altéré"):
        executer(chaines, anciennes, etat, fiche, tmp_path / "sortie",
                 recuperer=recuperer)
    assert not (tmp_path / "sortie").exists()


def test_archive_historique_sha_rapport_strict(tmp_path):
    _, anciennes, _, _, _ = fabriquer(tmp_path)
    with pytest.raises(ExtensionInvalide, match="Empreinte"):
        sources_anciennes(anciennes, empreinte_attendue="0" * 64)


def test_ressource_nouvelle_incomplete_refusee(tmp_path):
    chaines, anciennes, etat, fiche, recuperer = fabriquer(tmp_path)
    def tronque(selection, fichier):
        recuperer(selection, fichier)
        if selection["titre"] == "decp-2026-05.json":
            fichier.write_bytes(fichier.read_bytes()[:-1])
    sortie = tmp_path / "absent"
    with pytest.raises(ExtensionInvalide, match="totalité"):
        executer(chaines, anciennes, etat, fiche, sortie, recuperer=tronque)
    assert not sortie.exists()
