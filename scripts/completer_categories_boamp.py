"""Compléter les catégories BOAMP historiques sans modifier les relevés initiaux.

Les catégories ont été perdues par l'ancien normaliseur des listes.
Cette relecture officielle est une seconde observation datée ; chaque avis
initial garde son archive et son empreinte d'origine.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode

try:
    from scripts.collecter_besoins_publics import (
        BOAMP, recevoir, categorie_marche_officielle,
    )
    from scripts.rechercher_historique_boamp import avis_archive
    from scripts.surveiller_revisions_boamp import jours_archives
except ModuleNotFoundError:
    from collecter_besoins_publics import (
        BOAMP, recevoir, categorie_marche_officielle,
    )
    from rechercher_historique_boamp import avis_archive
    from surveiller_revisions_boamp import jours_archives

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "institutionnel" / "besoins_publics"
VERSION = "complements-categories-boamp-v1"
ARCHIVE = "categories_boamp"
MAX_JOURS = 16
MAX_PAGES = 50
TAILLE = 100
PAUSE = 0.25
SHA = re.compile(r"[0-9a-f]{64}")


class CategoriesIncompletes(ValueError):
    """La source ou la photographie complémentaire est incohérente."""


def empreinte(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def adresse(jour: date, page: int) -> str:
    if not 0 <= page < MAX_PAGES:
        raise CategoriesIncompletes("Page hors bornes.")
    suivant = jour + timedelta(days=1)
    return BOAMP + "?" + urlencode({
        "where": (f'dateparution >= "{jour.isoformat()}" AND '
                  f'dateparution < "{suivant.isoformat()}"'),
        "order_by": "idweb asc",
        "select": "idweb,dateparution,type_marche",
        "limit": TAILLE,
        "offset": page * TAILLE,
    })


def lire_categories(jour: date, obtenir=recevoir,
                    patienter=time.sleep) -> tuple[dict[str, str | None], int]:
    attendus, notices = None, {}
    for page in range(MAX_PAGES):
        retour = obtenir(adresse(jour, page), BOAMP)
        if not isinstance(retour, dict) or not isinstance(retour.get("results"), list):
            raise CategoriesIncompletes("Réponse officielle sans liste.")
        total = retour.get("total_count")
        if type(total) is not int or total < 0:
            raise CategoriesIncompletes("Dénominateur officiel invalide.")
        if attendus is None:
            attendus = total
            if total > MAX_PAGES * TAILLE:
                raise CategoriesIncompletes("Journée dépassant le plafond autorisé.")
        if attendus != total:
            raise CategoriesIncompletes("Dénominateur instable pendant les pages.")
        lignes = retour["results"]
        if len(lignes) != min(TAILLE, attendus - len(notices)):
            raise CategoriesIncompletes("Page officielle incomplète ou répétée.")
        for record in lignes:
            if not isinstance(record, dict):
                raise CategoriesIncompletes("Notice officielle mal formée.")
            uid = record.get("idweb")
            if isinstance(uid, int) and not isinstance(uid, bool):
                uid = str(uid)
            if (not isinstance(uid, str) or not re.fullmatch(r"[\w.-]{1,150}", uid)
                    or uid in notices
                    or not isinstance(record.get("dateparution"), str)
                    or record["dateparution"][:10] != jour.isoformat()):
                raise CategoriesIncompletes("Identifiant ou jour de la source incohérent.")
            notices[uid] = categorie_marche_officielle(record.get("type_marche"))
        if len(notices) == attendus:
            return notices, total
        patienter(PAUSE)
    raise CategoriesIncompletes("Pagination interrompue avant complétude.")


def chemins(base: Path, jour: str) -> tuple[Path, Path]:
    date.fromisoformat(jour)
    racine = base / ARCHIVE / jour[:4] / jour[5:7]
    return racine / (jour + ".jsonl.gz"), racine / (jour + ".json")


def completer_jour(base: Path, fiche_initiale: Path, *,
                   obtenir=recevoir, patienter=time.sleep,
                   instant: datetime | None = None) -> dict:
    jour, _archive, sha_initial, originaux = avis_archive(fiche_initiale, base)
    instant = instant or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise CategoriesIncompletes("Date de contrôle sans fuseau horaire.")
    categorie_path, manifeste_path = chemins(base, jour)
    if categorie_path.exists() or manifeste_path.exists():
        return verifier_complement(base, fiche_initiale)
    source, total = lire_categories(
        date.fromisoformat(jour), obtenir=obtenir, patienter=patienter,
    )
    identifiants_initiaux = {x["id"] for x in originaux}
    manquants = sorted(identifiants_initiaux - source.keys())
    nouveaux = sorted(source.keys() - identifiants_initiaux)
    records = [
        {
            "id": uid,
            "categorie_marche": source.get(uid),
            "present_dans_releve_complementaire": uid in source,
        }
        for uid in sorted(identifiants_initiaux)
    ]
    contenu = "".join(
        json.dumps(x, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        for x in records
    ).encode("utf-8")
    compresse = gzip.compress(contenu, compresslevel=9, mtime=0)
    manifeste = {
        "version": VERSION, "source": BOAMP,
        "jour_parution": jour,
        "controle_le": instant.replace(microsecond=0).isoformat(),
        "archive_originale_sha256_gzip": sha_initial,
        "nombre_identifiants_initiaux": len(originaux),
        "nombre_identifiants_source": total,
        "nombre_identifiants_ajoutes_depuis_initial": len(nouveaux),
        "sha256_liste_ajoutes": empreinte(
            json.dumps(nouveaux, ensure_ascii=False).encode("utf-8")
        ),
        "nombre_identifiants_absents_depuis_initial": len(manquants),
        "sha256_liste_absents": empreinte(
            json.dumps(manquants, ensure_ascii=False).encode("utf-8")
        ),
        "categories_renseignees_pour_identifiants_initiaux": sum(
            x["categorie_marche"] is not None for x in records
        ),
        "categories_non_renseignees_pour_identifiants_initiaux": sum(
            x["categorie_marche"] is None for x in records
        ),
        "archive_relative": categorie_path.relative_to(base).as_posix(),
        "sha256_archive_gzip": empreinte(compresse),
        "sha256_octets_decompresses": empreinte(contenu),
        "octets_archive": len(compresse),
        "photographie_initiale_modifiee": False,
        "date_origine_de_la_categorie_etablie": False,
        "completude_historique_de_la_source_etablie": False,
    }
    categorie_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_archive = categorie_path.with_suffix(".gz.tmp")
    tmp_fiche = manifeste_path.with_suffix(".json.tmp")
    tmp_archive.write_bytes(compresse)
    tmp_fiche.write_text(
        json.dumps(manifeste, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_archive.replace(categorie_path)
    tmp_fiche.replace(manifeste_path)
    return verifier_complement(base, fiche_initiale)


def verifier_complement(base: Path, fiche_initiale: Path) -> dict:
    jour, _archive, sha_original, notices = avis_archive(fiche_initiale, base)
    fichier, fiche = chemins(base, jour)
    if (not fichier.is_file() or fichier.is_symlink()
            or not fiche.is_file() or fiche.is_symlink()):
        raise CategoriesIncompletes("Complément et manifeste doivent être présents.")
    info = json.loads(fiche.read_text(encoding="utf-8"))
    if (not isinstance(info, dict)
            or info.get("version") != VERSION
            or info.get("jour_parution") != jour
            or info.get("archive_originale_sha256_gzip") != sha_original
            or info.get("nombre_identifiants_initiaux") != len(notices)
            or info.get("archive_relative") != fichier.relative_to(base).as_posix()
            or info.get("photographie_initiale_modifiee") is not False
            or info.get("date_origine_de_la_categorie_etablie") is not False):
        raise CategoriesIncompletes("Provenance du complément incohérente.")
    b = fichier.read_bytes()
    if not 0 < len(b) <= 2_000_000 or len(b) != info.get("octets_archive"):
        raise CategoriesIncompletes("Taille de complément incohérente.")
    if empreinte(b) != info.get("sha256_archive_gzip"):
        raise CategoriesIncompletes("Empreinte comprimée du complément incorrecte.")
    try:
        contenu = gzip.decompress(b)
    except (OSError, EOFError) as err:
        raise CategoriesIncompletes("Complément comprimé illisible.") from err
    if len(contenu) > 8_000_000 or empreinte(contenu) != info.get("sha256_octets_decompresses"):
        raise CategoriesIncompletes("Empreinte décompressée du complément incorrecte.")
    documents = []
    try:
        for ligne in contenu.splitlines():
            documents.append(json.loads(ligne))
    except (ValueError, UnicodeDecodeError) as erreur:
        raise CategoriesIncompletes("Lignes du complément incorrectes.") from erreur
    ids_originaux = sorted(x["id"] for x in notices)
    if ([x.get("id") for x in documents] != ids_originaux
            or any(x.get("categorie_marche") not in (
                None, "SERVICES", "FOURNITURES", "TRAVAUX",
            ) or type(x.get("present_dans_releve_complementaire")) is not bool
                   for x in documents)):
        raise CategoriesIncompletes("Identifiants ou catégories du complément incorrects.")
    if (sum(x["categorie_marche"] is not None for x in documents)
            != info.get("categories_renseignees_pour_identifiants_initiaux")
            or sum(x["categorie_marche"] is None for x in documents)
            != info.get("categories_non_renseignees_pour_identifiants_initiaux")):
        raise CategoriesIncompletes("Décomptes de catégories incorrects.")
    return info


def executer(base: Path = DOSSIER, *, instant: datetime | None = None,
            obtenir=recevoir, patienter=time.sleep,
            jours_par_execution: int = 12) -> dict:
    if type(jours_par_execution) is not int or not 1 <= jours_par_execution <= MAX_JOURS:
        raise CategoriesIncompletes("Taille du lot de compléments incorrecte.")
    instant = instant or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise CategoriesIncompletes("Horodatage non défini.")
    fiches = jours_archives(base)
    deja = []
    a_completer = []
    for fiche in sorted(fiches, reverse=True):
        _, cible = chemins(base, fiche.stem)
        if cible.exists() or cible.with_suffix(".jsonl.gz").exists():
            verifier_complement(base, fiche)
            deja.append(fiche.stem)
        else:
            a_completer.append(fiche)
    resultats, erreurs = [], []
    for fiche in a_completer[:jours_par_execution]:
        try:
            resultat = completer_jour(
                base, fiche, instant=instant, obtenir=obtenir, patienter=patienter,
            )
            resultats.append({
                "jour": fiche.stem,
                "identifiants": resultat["nombre_identifiants_initiaux"],
                "categories_renseignees": resultat[
                    "categories_renseignees_pour_identifiants_initiaux"
                ],
                "absents_source": resultat[
                    "nombre_identifiants_absents_depuis_initial"
                ],
            })
        except (OSError, ValueError, TimeoutError) as exc:
            erreurs.append({"jour": fiche.stem, "motif": type(exc).__name__})
    bilan = {
        "version": VERSION,
        "controle_le": instant.replace(microsecond=0).isoformat(),
        "jours_deja_completes_et_verifies": len(deja),
        "jours_nouveaux": len(resultats),
        "complements": resultats,
        "erreurs": erreurs,
        "jours_initiaux_sans_complement_avant_traitement": len(a_completer),
        "completude_historique_etablie": False,
        "categorie_initiale_de_l_avis_etablie": False,
    }
    if resultats:
        state = base / "etat_categories_boamp.json"
        temporaire = state.with_suffix(".json.tmp")
        temporaire.write_text(
            json.dumps(bilan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporaire.replace(state)
    if not resultats and erreurs:
        raise CategoriesIncompletes("Aucune catégorie historique récupérée.")
    return bilan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jours", type=int, default=12)
    args = parser.parse_args()
    try:
        bilan = executer(jours_par_execution=args.jours)
        print(json.dumps({
            "version": VERSION, "jours_nouveaux": bilan["jours_nouveaux"],
            "erreurs": bilan["erreurs"],
            "jours_a_completer_avant": bilan[
                "jours_initiaux_sans_complement_avant_traitement"
            ],
        }, ensure_ascii=False))
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(1, f"Complément BOAMP interrompu : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
