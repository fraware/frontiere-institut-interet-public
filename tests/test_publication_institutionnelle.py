"""Vérifications de publication contrôlée, sans accès réseau ni proposition réelle."""
from pathlib import Path
import subprocess

import pytest

from scripts.publier_mise_a_jour_institutionnelle import (
    PublicationRefusee, changements_git, identite_branche, indexer_changements,
    verifier_arbre_sain, verifier_portee,
)


def _git(racine: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=racine, check=True, capture_output=True)


def test_perimetres_independants_et_dependants():
    assert verifier_portee(
        "rnsr", ["institutionnel/entites/rnsr/rnsr_01.jsonl",
                 "institutionnel/statistiques_rnsr.json"],
    )["nombre_fichiers"] == 2
    assert verifier_portee(
        "surveillance", ["institutionnel/alertes_sources.json"],
    )["nombre_fichiers"] == 1
    assert verifier_portee(
        "referentiel", ["institutionnel/entites/roae/roae_00.jsonl",
                       "institutionnel/entites/locales/l_00.jsonl",
                       "institutionnel/territoires/cog/cog_00.jsonl",
                       "docs/INGESTION_COG_V1.md"],
    )["nombre_fichiers"] == 4


@pytest.mark.parametrize("source,path", [
    ("rnsr", "institutionnel/entites/locales/fiche.jsonl"),
    ("surveillance", ".github/workflows/ci.yml"),
    ("referentiel", "app/main.py"),
    ("rnsr", "../fuite"),
    ("rnsr", "/tmp/secret"),
    ("rnsr", "institutionnel/entites/rnsr/../autre"),
])
def test_modifications_hors_perimetre_refusees(source, path):
    with pytest.raises(PublicationRefusee, match="hors périmètre"):
        verifier_portee(source, [path])


@pytest.mark.parametrize("identifiant,tentative", [
    ("", "1"), ("un", "1"), ("123", "0"), ("12\n34", "1"),
])
def test_refuse_nom_automatique_invalide(identifiant, tentative):
    with pytest.raises(PublicationRefusee, match="branche"):
        identite_branche("rnsr", identifiant, tentative)


def test_nom_unique_de_proposition():
    assert identite_branche("surveillance", "123456", "2") == "automatisation/surveillance-123456-2"


def test_statu_git_preserve_espaces_et_fichiers_non_suivis(tmp_path: Path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Opérateur fictif")
    _git(tmp_path, "config", "user.email", "test@example.org")
    emplacement = tmp_path / "institutionnel"
    emplacement.mkdir()
    fichier = emplacement / "etat_sources.json"
    fichier.write_text("{}\n", encoding="utf-8")
    _git(tmp_path, "add", "--", "institutionnel/etat_sources.json")
    _git(tmp_path, "commit", "-qm", "État artificiel initial")
    fichier.write_text('{"exemple": true}\n', encoding="utf-8")
    assert changements_git(tmp_path) == ["institutionnel/etat_sources.json"]
    assert verifier_arbre_sain("surveillance", tmp_path)["nombre_fichiers"] == 1
    nouveau = emplacement / "alertes_sources.json"
    nouveau.write_text("{}\n", encoding="utf-8")
    assert set(changements_git(tmp_path)) == {
        "institutionnel/etat_sources.json",
        "institutionnel/alertes_sources.json",
    }
    (tmp_path / "dossier-inattendu.txt").write_text("exemple", encoding="utf-8")
    with pytest.raises(PublicationRefusee, match="hors périmètre"):
        verifier_arbre_sain("surveillance", tmp_path)


def test_aucune_publication_automatique_sans_contexte_autorise(monkeypatch):
    from scripts.publier_mise_a_jour_institutionnelle import publier
    for cle in ("GITHUB_EVENT_NAME", "GITHUB_REF", "GITHUB_REPOSITORY", "GH_TOKEN"):
        monkeypatch.delenv(cle, raising=False)
    with pytest.raises(PublicationRefusee, match="réservée"):
        publier("rnsr")



def test_indexation_reelle_des_seuls_chemins_modifies(tmp_path: Path):
    """Une source absente du périmètre admissible ne fait pas échouer git add."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Essai sans réseau")
    _git(tmp_path, "config", "user.email", "test@example.org")
    dossier = tmp_path / "institutionnel" / "decouverte"
    dossier.mkdir(parents=True)
    existant = dossier / "etat_collecte.json"
    existant.write_text('{"ancien": true}\n', encoding="utf-8")
    _git(tmp_path, "add", "--", "institutionnel/decouverte/etat_collecte.json")
    _git(tmp_path, "commit", "-qm", "Fichier initial fictif")
    existant.write_text('{"nouveau": true}\n', encoding="utf-8")
    pages = dossier / "balayage_pages"
    pages.mkdir()
    (pages / "page_00001.jsonl").write_text('{"id":"exemple"}\n', encoding="utf-8")
    nouveau = dossier / "balayage_etat.json"
    nouveau.write_text("{}\n", encoding="utf-8")
    # Le fichier optionnel catalogue_mesr.json manque délibérément.
    chemins = changements_git(tmp_path)
    assert len(chemins) == 3
    index = indexer_changements("sources", chemins, tmp_path)
    assert index == sorted(chemins)
    assert not (dossier / "catalogue_mesr.json").exists()
    _git(tmp_path, "commit", "-qm", "Lot fictif valide")


def test_indexation_garde_les_suppressions_prevues(tmp_path: Path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Essai sans réseau")
    _git(tmp_path, "config", "user.email", "test@example.org")
    dossier = tmp_path / "institutionnel" / "decouverte"
    dossier.mkdir(parents=True)
    fichier = dossier / "etat_collecte.json"
    fichier.write_text("{}", encoding="utf-8")
    _git(tmp_path, "add", "--", "institutionnel/decouverte/etat_collecte.json")
    _git(tmp_path, "commit", "-qm", "Fichier initial fictif")
    fichier.unlink()
    assert indexer_changements("sources", changements_git(tmp_path), tmp_path) == [
        "institutionnel/decouverte/etat_collecte.json"
    ]


def test_indexation_refuse_les_changements_hors_perimetre(tmp_path: Path):
    with pytest.raises(PublicationRefusee, match="hors périmètre"):
        indexer_changements("sources", ["app/main.py"], tmp_path)
