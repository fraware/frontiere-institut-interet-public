"""Lecture de l'en-tête du CSV d'emploi, sans conserver d'offres individuelles."""
import pytest

from scripts.sonder_structure_offres_publiques import (
    ErreurColonnes, choisir, detecter_entete, lire_en_tete,
)


def test_choisir_la_ressource_csv_la_plus_recente():
    ressources = [
        {"id": "un", "format": "csv", "modifie_le": "2025-10-01",
         "url": "https://static.data.gouv.fr/resources/ancien.csv"},
        {"id": "deux", "format": "csv", "modifie_le": "2026-10-05",
         "url": "https://static.data.gouv.fr/resources/offres.csv"},
        {"id": "trois", "format": "pdf", "modifie_le": "2026-10-09",
         "url": "https://static.data.gouv.fr/resources/document.pdf"},
    ]
    assert choisir(ressources)["id"] == "deux"
    with pytest.raises(ErreurColonnes):
        choisir(ressources[:1] if False else [])


def test_en_tete_delimiteur_colonnes_et_aucune_ligne_reprise():
    result = detecter_entete(
        "Identifiant;Intitulé du poste;Organisme;Date de parution\n"
        "ID-1;Emploi scientifique;Agence publique;2026-10-01\n".encode("utf-8")
    )
    assert result["separateur"] == "point-virgule"
    assert result["nombre_colonnes"] == 4
    assert result["colonnes"][1] == "Intitulé du poste"
    assert result["lignes_individuelles_copiees"] == 0
    assert "Emploi scientifique" not in str(result)


def test_refus_en_tetes_invalides():
    with pytest.raises(ErreurColonnes):
        detecter_entete(b"colonne_unique\n")
    with pytest.raises(ErreurColonnes):
        detecter_entete(b"a;a\nligne1;ligne2\n")
    with pytest.raises(ErreurColonnes):
        detecter_entete(b"")
    with pytest.raises(ErreurColonnes):
        lire_en_tete("https://example.org/secret")


def test_lecture_partielle_ne_conserve_pas_le_corps(monkeypatch):
    from scripts import sonder_structure_offres_publiques as module

    class Reponse:
        status = 206
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def geturl(self):
            return "https://static.data.gouv.fr/resources/offres.csv"
        def read(self, taille):
            assert taille <= 65537
            return b"id;nom;date\n123;exemple;2026-10-01\n"

    def ouvrir(requete, timeout):
        assert requete.headers.get("Range") == "bytes=0-65535"
        return Reponse()
    monkeypatch.setattr(module, "urlopen", ouvrir)
    assert lire_en_tete("https://static.data.gouv.fr/resources/offres.csv")[
        "colonnes"] == ["id", "nom", "date"]
