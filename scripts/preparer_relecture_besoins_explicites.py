"""Préparer une relecture traçable de demandes de compétences publiées.

Population : variantes d'offres Choisir le service public, archivées dans 16
partitions JSONL, sans données nominatives de contact. Deux échantillons
déterministes : général et orienté par lexique scientifique/technique.

Chaque citation est un champ exact de l'extraction ; aucune annonce n'est
déclarée encore ouverte et aucun besoin non satisfait n'est inféré.
La sélection NE constitue PAS une revue humaine ni un échantillon représentatif.
Le rapport est destiné à une pièce jointe temporaire contrôlée.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata

VERSION = "frontiere-candidats-relecture-besoins-v1"
SELECTION = "frontiere-csp-preselection-2026-10-15-v1"
REPERTOIRE = Path("institutionnel/besoins_publics")
FICHIER_MANIFESTE = REPERTOIRE / "manifest_offres_postes.json"
PARTITIONS = tuple(f"lot_{i:02x}.jsonl" for i in range(16))
SHA = re.compile(r"^[a-f0-9]{64}$")
EMAIL = re.compile(r"(?i)[\w.+-]+@[\w.-]+\.[a-z]{2,}")
URL = re.compile(r"(?i)https?://|www\.")
TELEPHONE = re.compile(r"(?<!\w)(?:\+33\s?(?:\(0\))?\s?|0)[1-9](?:[\s.\-]?\d{2}){4}(?!\d)")
DATE = re.compile(r"^20\d\d-\d\d-\d\d")
LEXIQUE = re.compile(
    r"informati|numeriqu|donnee|logiciel|cyber|securite des systemes|"
    r"ingenier|recherche|scientifi|mathemati|statistiqu|"
    r"intelligence artificielle|robotiqu|bioinformati|"
    r"physiqu|chimie|calcul intensif"
)


class EchecPreuve(ValueError):
    """Une pièce ou un décompte essentiel est incohérent."""


def verifier(ok: bool, motif: str) -> None:
    if not ok:
        raise EchecPreuve(motif)


def empreinte(texte: bytes) -> str:
    return hashlib.sha256(texte).hexdigest()


def date_publique(valeur: object) -> str | None:
    """Accepter une date civile explicite, y compris un horodatage suffixé."""
    if not isinstance(valeur, str) or not DATE.match(valeur):
        return None
    brut = valeur[:10]
    try:
        return brut if date.fromisoformat(brut).isoformat() == brut else None
    except ValueError:
        return None


def filtrer_texte(valeur: object, limite: int) -> str | None:
    """Réserver les extraits textuels aux champs courts, intégraux et sans URL."""
    if not isinstance(valeur, str):
        return None
    texte = valeur.strip()
    if (not texte or len(texte) > limite or EMAIL.search(texte) or
            URL.search(texte) or TELEPHONE.search(texte) or
            any(ord(c) < 32 for c in texte)):
        return None
    return texte


def normaliser(valeur: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", valeur.casefold())
                   if not unicodedata.combining(c))


def candidat(ligne: dict, chemin: str, numero: int, octets: bytes) -> dict | None:
    """Conserver les champs littéraux et une référence de ligne contrôlable."""
    if not isinstance(ligne, dict):
        raise EchecPreuve("Enregistrement de candidature non structuré.")
    ref = filtrer_texte(ligne.get("reference"), 180)
    titre = filtrer_texte(ligne.get("intitule"), 400)
    organisme = filtrer_texte(ligne.get("organisme"), 240)
    variante = ligne.get("cle_enregistrement")
    tronques = ligne.get("champs_tronques")
    if (not ref or not titre or not organisme or not isinstance(variante, str) or
            not SHA.fullmatch(variante) or not isinstance(tronques, list) or
            not all(isinstance(c, str) for c in tronques) or
            any(c in tronques for c in ("intitule", "organisme"))):
        return None
    champ_date = ("publication_debut" if date_publique(ligne.get("publication_debut"))
                  else "premiere_publication")
    date_iso = date_publique(ligne.get(champ_date))
    if not date_iso:
        return None
    competence = (None if "competences_attendues" in tronques
                  else filtrer_texte(ligne.get("competences_attendues"), 320))
    metier = filtrer_texte(ligne.get("metier"), 220)
    specialisation = filtrer_texte(ligne.get("specialisation"), 350)
    technique = bool(LEXIQUE.search(normaliser(" ".join(
        x for x in (titre, metier, specialisation) if x))))
    return {
        "reference": ref,
        "cle_enregistrement": variante,
        "organisme_declare": organisme,
        "titre_cite_integralement": titre,
        "competences_attendues_citees_integralement": competence,
        "date_publication": date_iso,
        "champ_date_publication": champ_date,
        "metier_declare": metier,
        "selection_lexicale_scientifique_technique": technique,
        "preuve": {
            "fichier": chemin,
            "ligne": numero,
            "sha256_ligne_jsonl": empreinte(octets),
            "champs": ["reference", "intitule", "organisme", champ_date] +
                      (["competences_attendues"] if competence else []),
        },
        "qualification": "recherche_de_competences_a_la_date_de_publication",
        "etat_actuel": "indetermine",
        "revue_humaine": "non_effectuee",
    }


def rang(reference: str, strate: str) -> str:
    return empreinte((SELECTION + "\x00" + strate + "\x00" + reference)
                     .encode("utf-8"))


def retenir(top: dict[str, dict], item: dict, nombre: int, strate: str) -> None:
    """Garder les k premières références par empreinte, variante minimale."""
    ref = item["reference"]
    if ref in top:
        if item["cle_enregistrement"] < top[ref]["cle_enregistrement"]:
            top[ref] = item
        return
    if len(top) < nombre:
        top[ref] = item
        return
    dernier = max(top, key=lambda r: (rang(r, strate), r))
    if (rang(ref, strate), ref) < (rang(dernier, strate), dernier):
        del top[dernier]
        top[ref] = item


def preparer(racine: Path, par_strate: int = 12) -> dict:
    """Rejouer le tirage sur tous les octets originaux, en mémoire bornée.

    Un même identifiant d'offre présent dans plusieurs variantes ne figure
    qu'une fois par échantillon. Les deux échantillons sont disjoints.
    """
    verifier(1 <= par_strate <= 30, "Taille de tirage non admise.")
    emplacement = racine / FICHIER_MANIFESTE
    brut = emplacement.read_bytes()
    manifest = json.loads(brut)
    sommes = manifest.get("empreintes_partitions")
    verifier(manifest.get("version") == "emplois-publics-extraits-v1" and
             isinstance(sommes, dict) and set(sommes) == set(PARTITIONS) and
             type(manifest.get("offres_distinctes")) is int and
             manifest["offres_distinctes"] > 0 and
             SHA.fullmatch(manifest.get("sha256_csv", "")) is not None,
             "Manifeste d'emplois incompatible.")
    general: dict[str, dict] = {}
    technique: dict[str, dict] = {}
    variantes_lues = admissibles = admissibles_techniques = 0
    for fichier in PARTITIONS:
        verifier(isinstance(sommes[fichier], str) and SHA.fullmatch(sommes[fichier]),
                 "Empreinte de partition manquante.")
        chemin = REPERTOIRE / "offres_postes" / fichier
        digest = hashlib.sha256()
        with (racine / chemin).open("rb") as entree:
            for numero, ligne in enumerate(entree, 1):
                digest.update(ligne)
                verifier(len(ligne) <= 24_000 and ligne.endswith(b"\n"),
                         "Ligne JSONL trop longue ou sans fin de ligne.")
                try:
                    contenu = json.loads(ligne)
                except (UnicodeError, json.JSONDecodeError) as exc:
                    raise EchecPreuve("Ligne de preuve JSONL mal formée.") from exc
                variantes_lues += 1
                evidence = candidat(contenu, chemin.as_posix(), numero, ligne)
                if evidence is None:
                    continue
                admissibles += 1
                retenir(general, evidence, par_strate, "general")
                if evidence["selection_lexicale_scientifique_technique"]:
                    admissibles_techniques += 1
                    # Garder le double de la taille : après élimination des
                    # références de la strate générale, k sont disponibles.
                    retenir(technique, evidence, par_strate * 2, "technique")
        verifier(digest.hexdigest() == sommes[fichier],
                 "Empreinte incohérente : " + fichier)
    verifier(variantes_lues == manifest["offres_distinctes"],
             "Nombre de variantes distinctes incompatible avec le manifeste.")
    verifier(len(general) == par_strate and len(technique) >= par_strate,
             "Population admissible insuffisante : "
             f"variantes_admissibles={admissibles}, "
             f"variantes_techniques={admissibles_techniques}, "
             f"references_generales={len(general)}, "
             f"references_techniques={len(technique)}.")
    selection_general = sorted(general.values(),
                              key=lambda v: (rang(v["reference"], "general"),
                                             v["reference"]))
    candidats_techniques = sorted(
        (v for ref, v in technique.items() if ref not in general),
        key=lambda v: (rang(v["reference"], "technique"), v["reference"]))
    verifier(len(candidats_techniques) >= par_strate,
             "Strate technique disjointe insuffisante.")
    selection = [
        {**ligne, "strate": "generale"} for ligne in selection_general
    ] + [
        {**ligne, "strate": "lexicale_scientifique_technique"}
        for ligne in candidats_techniques[:par_strate]
    ]
    return {
        "version": VERSION,
        "regle_selection": SELECTION,
        "sha256_manifeste": empreinte(brut),
        "sha256_csv_source": manifest["sha256_csv"],
        "source_modifie_le": manifest.get("source_modifie_le"),
        "fichier_source_conserve": False,
        "partitions_verifiees": len(PARTITIONS),
        "variantes_lues": variantes_lues,
        "variantes_admissibles": admissibles,
        "variantes_admissibles_lexicales": admissibles_techniques,
        "taille_par_strate": par_strate,
        "nombre_candidats": len(selection),
        "representativite_statistique_etablie": False,
        "besoins_actuellement_non_satisfaits_demonstres": 0,
        "relecture_humaine_effectuee": False,
        "candidats": selection,
        "precision": (
            "Le tirage est déterministe au sein des variantes admissibles de "
            "l'instantané de recrutement. La strate scientifique/technique "
            "résulte d'une règle lexicale et non d'une classification validée. "
            "L'intitulé et les compétences, si renseignées, sont des champs "
            "cités sans reformulation. Les dates et les états actuels des "
            "offres n'ont pas été vérifiés auprès des administrations."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--racine", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--par-strate", type=int, default=12)
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.sortie.exists() or args.sortie.is_symlink():
            raise EchecPreuve("Une sortie existe déjà : refus d'écrasement.")
        resultat = preparer(args.racine, args.par_strate)
        sortie = (json.dumps(resultat, ensure_ascii=False, sort_keys=True,
                             indent=2, allow_nan=False) + "\n").encode("utf-8")
        verifier(len(sortie) <= 100_000, "Pièce de relecture trop volumineuse.")
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_bytes(sortie)
        print(json.dumps({
            "variantes_lues": resultat["variantes_lues"],
            "admissibles": resultat["variantes_admissibles"],
            "admissibles_lexicales": resultat["variantes_admissibles_lexicales"],
            "candidats": resultat["nombre_candidats"],
            "preuve_integrale_consultable": True,
            "revue_humaine_effectuee": False
        }, ensure_ascii=False, sort_keys=True))
    except (EchecPreuve, OSError, UnicodeError, ValueError) as exc:
        parser.exit(1, f"Préparation refusée : {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
