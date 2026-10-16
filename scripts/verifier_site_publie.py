"""Auditer les fichiers réellement servis par le site statique FRONTIÈRE.

La récupération est bornée, en lecture seule, sur une adresse publique fixe.
Une révision différente est un retard de publication, pas une altération des
sources. Une réponse inaccessible n'est jamais transformée en vérification.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from scripts.auditer_chaine_publication import identites

RACINE = Path(__file__).resolve().parents[1]
ORIGINE = "https://frontiere-observatoire-public.onrender.com"
HOTE = urlsplit(ORIGINE).hostname
LOT = re.compile(r"part-(boamp|emplois|decp)-(\d{4})-(\d{3})\.json")
SHA = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
SOURCES = ("boamp", "emplois", "decp")


class EchecPublication(ValueError):
    """Une pièce publique ne satisfait pas ses attestations internes."""


def imposer(valide: bool, cause: str) -> None:
    if not valide:
        raise EchecPublication(cause)


def recuperer(chemin: str, limite: int) -> bytes:
    """Télécharger un fichier JSON d'une origine fixe, sans suivi hors hôte."""
    imposer(re.fullmatch(r"[a-z0-9_./-]+", chemin) is not None
            and ".." not in chemin.split("/") and chemin.endswith(".json"),
            "Chemin distant non autorisé.")
    requete = Request(ORIGINE + "/" + chemin, headers={
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "frontiere-controle-publication/1.0",
    })
    with urlopen(requete, timeout=12) as reponse:
        cible = urlsplit(reponse.geturl())
        imposer(cible.scheme == "https" and cible.hostname == HOTE
                and cible.port is None, "Redirection de publication interdite.")
        imposer(reponse.status == 200, "Publication HTTP non disponible.")
        donnees = reponse.read(limite + 1)
    imposer(0 < len(donnees) <= limite, "Réponse publique vide ou trop grande.")
    return donnees


def ouvrir(telecharger, chemin: str, limite: int) -> tuple[dict | list, bytes]:
    brut = telecharger(chemin, limite)
    imposer(isinstance(brut, bytes) and 0 < len(brut) <= limite,
            "Réponse absente ou hors limite.")
    try:
        return json.loads(brut), brut
    except (ValueError, UnicodeError) as exc:
        raise EchecPublication("Réponse JSON invalide : " + chemin) from exc


def empreinte(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def controler_publication(telecharger=recuperer, *,
                         attendu: str | None = None,
                         racine: Path = RACINE) -> dict:
    """Comparer les manifestes distants et leurs pièces, puis la révision locale."""
    imposer(attendu is None or COMMIT.fullmatch(attendu) is not None,
            "Révision de référence invalide.")
    principal, octets_principaux = ouvrir(
        telecharger, "recherche-index.json", 2_000_000)
    manifeste, octets_manifeste = ouvrir(
        telecharger, "partitions/manifeste.json", 1_000_000)
    dates, _ = ouvrir(telecharger, "metadonnees-index.json", 20_000)
    imposer(isinstance(principal, dict) and isinstance(manifeste, dict)
            and isinstance(dates, dict), "Structure des manifestes incorrecte.")
    version = principal.get("revision_sources")
    imposer(version == manifeste.get("revision_sources") ==
            dates.get("revision_sources"), "Révision contradictoire des publications.")
    imposer(principal.get("portee") == "echantillon_documentaire_non_exhaustif"
            and principal.get("recherche_temps_reel") is False and
            manifeste.get("portee") == "extrait_etendu_non_exhaustif" and
            manifeste.get("mise_a_jour_temps_reel") is False,
            "Limites de la publication incorrectes.")
    imposer(isinstance(principal.get("documents"), list) and
            isinstance(manifeste.get("partitions"), list) and
            isinstance(manifeste.get("selection", {}).get("sources"), list),
            "Corpus déclaré absent.")
    principaux = {s: identites(
        [d for d in principal["documents"]
         if isinstance(d, dict) and d.get("source") == s], s) for s in SOURCES}
    imposer(sum(map(len, principaux.values())) == len(principal["documents"]),
            "Source inconnue dans l'index principal.")

    etendus: dict[str, list] = {s: [] for s in SOURCES}
    fichiers_vus: set[str] = set()
    volume = 0
    for lot in manifeste["partitions"]:
        nom = lot.get("fichier") if isinstance(lot, dict) else None
        match = LOT.fullmatch(nom) if isinstance(nom, str) else None
        imposer(match is not None and nom not in fichiers_vus,
                "Nom de partition invalide ou répété.")
        fichiers_vus.add(nom)
        source, annee = match.group(1), match.group(2)
        imposer(lot.get("source") == source and lot.get("annee") == annee,
                "Origine de partition incompatible.")
        pieces, brut = ouvrir(telecharger, "partitions/" + nom, 1_000_000)
        imposer(isinstance(pieces, list) and
                type(lot.get("documents")) is int and
                len(pieces) == lot["documents"] and
                len(brut) == lot.get("octets") and
                isinstance(lot.get("sha256"), str) and
                SHA.fullmatch(lot["sha256"]) and
                empreinte(brut) == lot["sha256"],
                "Partition distante divergente : " + nom)
        imposer(all(isinstance(d, dict) and isinstance(d.get("date"), str)
                    and d["date"].startswith(annee + "-") for d in pieces),
                "Partition contenant une année incohérente.")
        etendus[source].extend(pieces)
        volume += len(pieces)

    resultat_sources = {}
    for source in SOURCES:
        uniques = identites(etendus[source], source)
        sel = [s for s in manifeste["selection"]["sources"]
               if isinstance(s, dict) and s.get("source") == source]
        imposer(len(sel) == 1, "Source absente du bilan des partitions.")
        nb = sel[0].get("documents_indexes")
        declare = principal.get("sources", {}).get(source, {}).get("retenus")
        imposer(type(nb) is int and nb == len(uniques) and
                type(declare) is int and declare == len(principaux[source]) and
                len(principaux[source]) <= len(uniques),
                "Décompte distant incohérent : " + source)
        for identifiant, document in principaux[source].items():
            ext = uniques.get(identifiant)
            imposer(ext is not None and
                    all(ext.get(k) == v for k, v in document.items()),
                    "Index principal et partition divergents : " + source)
        resultat_sources[source] = {
            "index_principal": len(principaux[source]),
            "partitions": len(uniques),
        }
    imposer(manifeste.get("selection", {}).get("couverture_nationale_etablie") is False,
            "Couverture nationale injustifiée.")

    # Une révision non attestée ne suffit jamais à déclarer le site à jour.
    coherent = COMMIT.fullmatch(version) is not None if isinstance(version, str) else False
    if attendu is None or not coherent:
        statut = "revision_non_verifiable"
    elif version != attendu:
        statut = "revision_distincte"
    else:
        local_index = (racine / "site_frontiere/recherche-index.json").read_bytes()
        local_manifest = (racine / "site_frontiere/partitions/manifeste.json").read_bytes()
        imposer(empreinte(local_index) == empreinte(octets_principaux)
                and empreinte(local_manifest) == empreinte(octets_manifeste),
                "Révision identique mais octets publiés divergents.")
        statut = "a_jour_et_concordant"
    return {
        "version": "frontiere-verification-publication-v1",
        "origine": ORIGINE,
        "statut": statut,
        "integrite_publique_verifiee": True,
        "revision_publique": version,
        "revision_attendue": attendu,
        "partitions_lues": len(fichiers_vus),
        "documents_partitions": volume,
        "sources": resultat_sources,
        "site_a_jour": statut == "a_jour_et_concordant",
        "couverture_nationale_demontree": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rapport", required=True, type=Path)
    parser.add_argument("--racine", type=Path, default=RACINE)
    parser.add_argument("--revision", default=os.getenv("GITHUB_SHA"))
    args = parser.parse_args()
    try:
        bilan = controler_publication(attendu=args.revision, racine=args.racine)
        code = 0
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        bilan = {
            "version": "frontiere-verification-publication-v1",
            "statut": "publication_inaccessible",
            "integrite_publique_verifiee": False,
            "site_a_jour": False,
            "detail": type(exc).__name__,
        }
        code = 0  # Échec du site externe : diagnostic, sans détruire la CI.
    except (EchecPublication, ValueError, KeyError, TypeError) as exc:
        bilan = {
            "version": "frontiere-verification-publication-v1",
            "statut": "publication_incoherente",
            "integrite_publique_verifiee": False,
            "site_a_jour": False,
            "detail": str(exc)[:180],
        }
        code = 1
    sortie = args.rapport.resolve()
    sortie.parent.mkdir(parents=True, exist_ok=True)
    provisoire = sortie.with_name(sortie.name + ".tmp")
    provisoire.write_text(json.dumps(bilan, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    os.replace(provisoire, sortie)
    print(json.dumps(bilan, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
