"""Importation locale des lignes d'emploi depuis un fichier CSV fictif."""
import csv
import json

import pytest

from scripts.extraire_offres_publiques import (
    CLES, EchecExtraction, executer, ligne_offre, partitions, traiter_csv,
)


def colonnes():
    # Reprise des trente colonnes structurelles dont les champs employés.
    return list(CLES) + [f"Colonne supplémentaire {i}" for i in range(8)]


def fabriquer_csv(chemin, data, headers):
    with chemin.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter=";")
        writer.writeheader()
        for ligne in data:
            writer.writerow(ligne)


def ligne(reference, poste):
    return {
        "Référence": reference,
        "Intitulé du poste": poste,
        "Métier": "Chercheur",
        "Employeur": "Établissement public",
        "Compétences attendues": "Modélisation et statistiques",
    }


def test_lecture_et_partition_d_offres_sans_contacts(tmp_path):
    chemin = tmp_path / "offres.csv"
    donnees = [ligne("2026-ABC001", "Ingénieur scientifique"),
               ligne("2026-ABC002", "Chercheuse en physique")]
    cols = colonnes()
    fabriquer_csv(chemin, donnees, cols)
    offres, stats = traiter_csv(chemin, cols)
    assert stats["offres_distinctes"] == 2
    assert stats["lignes_lues"] == 2
    assert stats["couverture_integrale_du_csv"] is True
    premiere = next(x for x in offres.values() if x["reference"] == "2026-ABC001")
    assert premiere["metier"] == "Chercheur"
    assert premiere["competences_attendues"] == "Modélisation et statistiques"
    assert len(premiere["cle_enregistrement"]) == 64
    assert len(partitions(offres)) == 16
    assert sum(len(p) for p in partitions(offres).values()) == 2
    assert "courriel" not in str(offres)


def test_refus_d_un_schema_changé_ou_d_un_identifiant_contradictoire(tmp_path):
    csv_file = tmp_path / "offres.csv"
    cols = colonnes()
    fabriquer_csv(csv_file, [ligne("2026-ABC001", "Poste A"),
                              ligne("2026-ABC001", "Poste B")], cols)
    d, bilan = traiter_csv(csv_file, cols)
    assert bilan["offres_distinctes"] == 2
    assert bilan["references_distinctes"] == 1
    assert bilan["references_avec_plusieurs_variantes"] == 1
    assert bilan["variantes_supplementaires_de_reference"] == 1
    assert {x["intitule"] for x in d.values()} == {"Poste A", "Poste B"}
    with pytest.raises(EchecExtraction, match="Schéma"):
        traiter_csv(csv_file, cols[::-1])


def test_refus_identifiants_invalides_et_troncature_explicite(tmp_path):
    offres = [ligne("", "Vide"), ligne("2026-ABC001", "A" * 500)]
    cols = colonnes()
    csv_file = tmp_path / "offres.csv"
    fabriquer_csv(csv_file, offres, cols)
    d, stats = traiter_csv(csv_file, cols)
    assert stats["lignes_sans_reference"] == 1
    assert stats["cellules_tronquees"] == 1
    assert stats["couverture_integrale_du_csv"] is False
    assert next(iter(d.values()))["champs_tronques"] == ["intitule"]


def test_identite_fichier_et_schema_obligatoires(tmp_path):
    (tmp_path / "ressources_emplois_publics.json").write_text(json.dumps({
        "licence_declaree": "lov2",
        "ressources": [{
            "id": "source-1",
            "format": "csv",
            "modifie_le": "2026-10-05",
            "url": "https://static.data.gouv.fr/resources/emplois.csv",
        }],
    }), encoding="utf-8")
    (tmp_path / "schema_emplois_publics.json").write_text(json.dumps({
        "source_id": "source-2",
        "separateur": "point-virgule",
        "colonnes": colonnes(),
    }), encoding="utf-8")
    with pytest.raises(EchecExtraction, match="concordent"):
        executer(tmp_path)


def test_refus_d_une_ligne_de_contact_non_couverte():
    ligne = {"Référence": "2026-ABC001", "courriel": "personne@example.org",
             "Intitulé du poste": "Poste fictif"}
    resultat = ligne_offre(ligne)
    assert "courriel" not in resultat
    assert "personne@example.org" not in str(resultat)
