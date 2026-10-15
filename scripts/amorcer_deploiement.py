"""Préparer et amorcer le déploiement permanent de FRONTIÈRE.

Par défaut, imprime seulement le plan d'exécution. Avec --executer,
construit les images, importe les archives présentes sur le disque,
puis démarre les six services définis dans compose.collecte.yml.

À exécuter sur l'hôte possédant Docker Compose et son espace disque durable.
La fusion sur GitHub n'a aucun effet sur cet hôte.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import json
import shlex
import shutil
import subprocess
import sys
from typing import Callable

SERVICES = (
    "collecte-boamp",
    "collecte-emplois",
    "collecte-decp",
    "collecte-decp-consolides",
    "collecte-ted",
    "consultation",
)
FICHIERS_ATTENDUS = (
    "compose.collecte.yml",
    "institutionnel/besoins_publics/manifest_offres_postes.json",
    "institutionnel/decp/sources_v1.json",
    "institutionnel/decp/sonde_aife_json.json",
    "institutionnel/decp/lot_dgfip_xml.json",
)
PREFIX = ("docker", "compose", "-f", "compose.collecte.yml")


@dataclass(frozen=True)
class Etape:
    nom: str
    commande: tuple[str, ...]


def etapes(*, amorcer: bool = True, demarrer: bool = True) -> tuple[Etape, ...]:
    """Ordre déterministe et rejouable des commandes sur un seul hôte."""
    sorties = [
        Etape("Vérifier la configuration des services", (*PREFIX, "config", "--quiet")),
        Etape("Construire les images", (*PREFIX, "build", *SERVICES)),
    ]
    if amorcer:
        sorties.extend((
            Etape(
                "Importer les avis BOAMP archivés",
                (*PREFIX, "run", "--rm", "--no-deps", "-T",
                 "collecte-boamp", "python", "-m", "app.plateforme_boamp",
                 "--base", "sqlite:////var/lib/frontiere/avis_boamp.sqlite3",
                 "importer", "--repertoire", "/opt/frontiere/archives"),
            ),
            Etape(
                "Importer les offres d'emploi archivées",
                (*PREFIX, "run", "--rm", "--no-deps", "-T",
                 "collecte-emplois", "python", "-m", "app.plateforme_emplois",
                 "--base", "sqlite:////var/lib/frontiere/offres_emplois.sqlite3",
                 "importer", "--repertoire", "/opt/frontiere/archives"),
            ),
            Etape(
                "Importer les attributions DECP archivées",
                (*PREFIX, "run", "--rm", "--no-deps", "-T",
                 "collecte-decp", "python", "-m", "app.collecteur_decp_continu",
                 "--base", "/var/lib/frontiere/marches_decp.sqlite3",
                 "--repertoire", "/var/lib/frontiere/releves",
                 "--archives", "/opt/frontiere/archives-decp", "amorcer"),
            ),
        ))
    if demarrer:
        sorties.extend((
            Etape("Démarrer les services", (*PREFIX, "up", "--detach", *SERVICES)),
            Etape("Lister les services", (*PREFIX, "ps")),
        ))
    return tuple(sorties)


def valider_repertoire(racine: Path) -> dict:
    """Ne jamais annoncer un amorçage possible si les sources locales manquent."""
    fichiers = [x for x in FICHIERS_ATTENDUS
                if not (racine / x).is_file()]
    partitions = sorted((racine / "institutionnel/besoins_publics/offres_postes"
                         ).glob("lot_*.jsonl"))
    manifestes = sorted((racine / "institutionnel/besoins_publics/historique_boamp"
                         ).glob("*/*/*.json"))
    if len(partitions) != 16:
        fichiers.append("institutionnel/besoins_publics/offres_postes (16 partitions)")
    if not manifestes:
        fichiers.append("institutionnel/besoins_publics/historique_boamp (manifestes)")
    return {
        "repertoire": str(racine),
        "fichiers_absents": fichiers,
        "partitions_emplois_detectees": len(partitions),
        "manifestes_boamp_detectes": len(manifestes),
        "pret_a_amorcer": not fichiers,
    }


def plan(racine: Path, *, amorcer: bool = True,
         demarrer: bool = True) -> dict:
    dossier = racine.resolve()
    etat = valider_repertoire(dossier)
    etat["mode"] = "simulation"
    etat["aucune_commande_executee"] = True
    etat["etapes"] = [{
        "nom": x.nom,
        "commande": shlex.join(x.commande),
    } for x in etapes(amorcer=amorcer, demarrer=demarrer)]
    return etat


def executer(
    racine: Path, *,
    amorcer: bool = True,
    demarrer: bool = True,
    executant: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list[str]:
    dossier = racine.resolve()
    prevol = valider_repertoire(dossier)
    if amorcer and not prevol["pret_a_amorcer"]:
        raise ValueError(
            "Archives d'amorçage absentes : " + ", ".join(prevol["fichiers_absents"])
        )
    if not (dossier / "compose.collecte.yml").is_file():
        raise ValueError("Configuration Compose absente.")
    if executant is subprocess.run and shutil.which("docker") is None:
        raise RuntimeError("Docker n'est pas installé sur cet hôte.")
    termine: list[str] = []
    for etape in etapes(amorcer=amorcer, demarrer=demarrer):
        print(f"\n>>> {etape.nom}", flush=True)
        executant(list(etape.commande), cwd=dossier, check=True)
        termine.append(etape.nom)
    return termine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repertoire", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--executer", action="store_true",
                        help="Autoriser la construction, l'importation et le démarrage")
    parser.add_argument("--sans-amorcage", action="store_true",
                        help="Ne pas relire le corpus versionné")
    parser.add_argument("--sans-demarrage", action="store_true",
                        help="Construire et amorcer seulement")
    args = parser.parse_args(argv)
    dossier = args.repertoire.resolve()
    if not args.executer:
        print(json.dumps(plan(
            dossier, amorcer=not args.sans_amorcage,
            demarrer=not args.sans_demarrage
        ), ensure_ascii=False, indent=2))
        return 0
    try:
        realisees = executer(
            dossier, amorcer=not args.sans_amorcage,
            demarrer=not args.sans_demarrage,
        )
    except (OSError, ValueError, RuntimeError,
            subprocess.CalledProcessError) as exc:
        print(f"Amorçage arrêté sans poursuivre les étapes suivantes : {exc}",
              file=sys.stderr)
        return 1
    print(json.dumps({"etapes_reussies": realisees,
                      "deploiement_reel": True,
                      "disponibilite_et_fraicheur_a_verifier": True},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
