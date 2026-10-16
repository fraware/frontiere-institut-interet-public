"""Essais synthétiques de réconciliation archives → index principal → partitions."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.auditer_chaine_publication import EchecAudit, auditer

REVISION = "a" * 40
CSP_MANIFEST = "institutionnel/besoins_publics/manifest_offres_postes.json"
BOAMP_ARCHIVE = "institutionnel/besoins_publics/annonces_boamp.json"
BOAMP_ETAT = "institutionnel/besoins_publics/etat_boamp.json"
DECP_BILAN = "institutionnel/decp/bilan_index_unifie.json"
AIFE = "institutionnel/decp/sonde_aife_json.json"
DGFIP = "institutionnel/decp/lot_dgfip_xml.json"
INDEX = "site_frontiere/recherche-index.json"
MANIFEST = "site_frontiere/partitions/manifeste.json"


def ecrire(racine: Path, path: str, objet: dict | list) -> bytes:
    p = racine / path
    p.parent.mkdir(parents=True, exist_ok=True)
    brut = (json.dumps(objet, ensure_ascii=False, sort_keys=True) + "\n").encode()
    p.write_bytes(brut)
    return brut


def h(brut: bytes) -> str:
    return hashlib.sha256(brut).hexdigest()


def fixture_chaine(racine: Path) -> None:
    ecrire(racine, BOAMP_ETAT, {"annonces_distinctes_conservees": 1})
    b = ecrire(racine, BOAMP_ARCHIVE, {"annonces": [{"id": "26-1"}]})
    c = ecrire(racine, CSP_MANIFEST, {
        "offres_distinctes": 2, "references_distinctes": 1,
        "empreintes_partitions": {f"lot_{i:02x}.jsonl": "b" * 64 for i in range(16)}
    })
    ecrire(racine, DECP_BILAN, {
        "attestations_documentaires": 3,
        "variantes_documentaires_distinctes": 2,
        "identites_distinctes_par_siret_et_id_marche": 1
    })
    a = ecrire(racine, AIFE, {"marches_extraits": [{"id": "M-1"}]})
    d = ecrire(racine, DGFIP, {"fichiers": []})
    documents = [
        {"source": "boamp", "id": "26-1", "date": "2026-10-14", "titre": "Machine"},
        {"source": "emplois", "id": "EMP-1", "date": "2026-10-13", "titre": "Ingénieur"},
        {"source": "decp", "id": "12345678901234/M-1",
         "date": "2026-10-11", "titre": "Instrument"},
    ]
    sources = {
        "boamp": {
            "retenus": 1, "notices_fichier": 1,
            "empreinte_fichier": h(b),
        },
        "emplois": {
            "retenus": 1, "variantes_fichier": 2,
            "empreinte_manifeste": h(c),
        },
        "decp": {
            "retenus": 1, "notices_fichiers": 3,
            "fichiers": [
                {"chemin": AIFE, "sha256": h(a)},
                {"chemin": DGFIP, "sha256": h(d)},
            ],
        },
    }
    ecrire(racine, INDEX, {
        "portee": "echantillon_documentaire_non_exhaustif",
        "recherche_temps_reel": False,
        "revision_sources": REVISION,
        "sources": sources,
        "limites": {"boamp": 700, "emplois": 700, "decp": 500},
        "documents": documents,
    })
    ecrire(racine, "site_frontiere/metadonnees-index.json",
           {"revision_sources": REVISION})
    comptes = {"boamp": 1, "emplois": 2, "decp": 3}
    passages = []
    for item in documents:
        source, annee = item["source"], item["date"][:4]
        nom = f"part-{source}-{annee}-001.json"
        donnees = [{**item, "qualification": {"type": "observation"}}]
        brut = ecrire(racine, "site_frontiere/partitions/" + nom, donnees)
        passages.append({
            "fichier": nom, "source": source, "annee": annee, "documents": 1,
            "octets": len(brut), "sha256": h(brut),
        })
    ecrire(racine, MANIFEST, {
        "portee": "extrait_etendu_non_exhaustif",
        "mise_a_jour_temps_reel": False,
        "revision_sources": REVISION,
        "limite_par_source": {s: 5000 for s in comptes},
        "selection": {
            "couverture_nationale_etablie": False,
            "sources": [
                {
                    "source": s, "documents_indexes": 1,
                    "enregistrements_sources_parcourus": n, "plafond": 5000
                } for s, n in comptes.items()
            ],
        },
        "partitions": passages
    })


def modifier(racine: Path, path: str, transformation) -> None:
    original = json.loads((racine / path).read_text(encoding="utf-8"))
    transformation(original)
    ecrire(racine, path, original)


def test_chaine_coherente_et_unites_distinctes(tmp_path: Path):
    fixture_chaine(tmp_path)
    bilan = auditer(tmp_path, REVISION)
    assert bilan["partitions_verifiees"] == 3
    assert bilan["sources"]["emplois"]["archives"] == 2
    assert bilan["sources"]["emplois"]["index_etendu"] == 1
    assert bilan["sources"]["decp"]["archives"] == 3
    assert bilan["site_render_examine"] is False
    assert bilan["couverture_nationale_demontree"] is False


def test_refus_partitions_corrompues(tmp_path: Path):
    fixture_chaine(tmp_path)
    p = tmp_path / "site_frontiere/partitions/part-boamp-2026-001.json"
    p.write_bytes(p.read_bytes().replace(b"Machine", b"Machines"))
    with pytest.raises(EchecAudit, match="empreinte"):
        auditer(tmp_path, REVISION)


def test_refus_document_absent_ou_modifie_dans_etendu(tmp_path: Path):
    fixture_chaine(tmp_path)
    modifier(tmp_path, INDEX, lambda x: x["documents"][0].update(titre="Autre"))
    with pytest.raises(EchecAudit, match="divergent"):
        auditer(tmp_path, REVISION)


def test_refus_mauvaise_population_source(tmp_path: Path):
    fixture_chaine(tmp_path)
    modifier(tmp_path, BOAMP_ETAT,
             lambda x: x.update(annonces_distinctes_conservees=2))
    with pytest.raises(EchecAudit, match="BOAMP"):
        auditer(tmp_path, REVISION)


def test_refus_versions_differentes(tmp_path: Path):
    fixture_chaine(tmp_path)
    modifier(tmp_path, MANIFEST,
             lambda x: x.update(revision_sources="b" * 40))
    with pytest.raises(EchecAudit, match="Versions"):
        auditer(tmp_path, REVISION)


def test_refus_de_doublon_documentaire(tmp_path: Path):
    fixture_chaine(tmp_path)
    def ajouter(doc):
        doc["partitions"].append(deepcopy(doc["partitions"][0]))
    modifier(tmp_path, MANIFEST, ajouter)
    with pytest.raises(EchecAudit, match="dupliquée"):
        auditer(tmp_path, REVISION)
