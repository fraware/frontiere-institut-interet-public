"""Publication contrôlée des actualisations institutionnelles vers une proposition.

Les collectes téléchargent des données publiques sur une copie de main.
Cette commande refuse les modifications de fichiers hors périmètre, les
révisions périmées et les publications sans identité de procédure explicite.
Elle ne fusionne jamais de proposition ni n'écrit directement sur main.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

RACINE = Path(__file__).resolve().parents[1]
CHEMINS = {
    "rnsr": (
        "institutionnel/entites/rnsr",
        "institutionnel/statistiques_rnsr.json",
        "institutionnel/instantanes/rnsr_manifest.json",
    ),
    "surveillance": (
        "institutionnel/etat_sources.json",
        "institutionnel/alertes_sources.json",
    ),
    "referentiel": (
        "institutionnel/entites/roae",
        "institutionnel/relations/roae",
        "institutionnel/instantanes/roae_manifest.json",
        "institutionnel/statistiques_roae.json",
        "institutionnel/anomalies_roae.json",
        "institutionnel/entites/locales",
        "institutionnel/relations/locales",
        "institutionnel/instantanes/annuaire_local_manifest.json",
        "institutionnel/statistiques_annuaire_local.json",
        "institutionnel/anomalies_annuaire_local.json",
        "institutionnel/resolution_roae_local.json",
        "institutionnel/territoires/cog",
        "institutionnel/relations/territoriales/cog",
        "institutionnel/instantanes/cog_manifest.json",
        "institutionnel/statistiques_cog.json",
        "institutionnel/anomalies_cog.json",
        "institutionnel/resolution_annuaire_cog.json",
        "README.md",
        "institutionnel/README.md",
        "docs/INGESTION_COG_V1.md",
    ),
}
TITRES = {
    "rnsr": "Actualiser les structures publiques de recherche",
    "surveillance": "Actualiser la surveillance des sources institutionnelles",
    "referentiel": "Actualiser le référentiel administratif et territorial",
}
BRANCH = re.compile(r"^automatisation/(rnsr|surveillance|referentiel)-([0-9]+)-([1-9][0-9]*)$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class PublicationRefusee(ValueError):
    """La publication présenterait une erreur de portée ou de provenance."""


def _commande(*args: str, cwd: Path = RACINE, env: dict | None = None) -> str:
    """Exécuter une commande par arguments séparés, sans interpréteur de commandes."""
    retour = subprocess.run(
        args, cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    if retour.returncode:
        # Le détail des erreurs GitHub peut révéler une configuration privée.
        raise PublicationRefusee(
            f"Commande refusée ({args[0]} {args[1] if len(args) > 1 else ''}), "
            f"code {retour.returncode}."
        )
    # Conserver les octets de séparation représentés par \0 et les espaces du statut Git.
    return retour.stdout


def _autorise(chemin: str, autorises: tuple[str, ...]) -> bool:
    return any(chemin == prefix or chemin.startswith(prefix.rstrip("/") + "/")
               for prefix in autorises)


def verifier_portee(source: str, changements: list[str]) -> dict:
    """Examiner un ensemble de chemins avant tout ajout dans Git."""
    if source not in CHEMINS:
        raise PublicationRefusee("Collection inconnue.")
    hors_portee = sorted({
        x for x in changements if
        not x or x.startswith("/") or "\\" in x or
        any(element in {".", ".."} for element in Path(x).parts) or
        not _autorise(x, CHEMINS[source])
    })
    if hors_portee:
        raise PublicationRefusee("Modifications hors périmètre : " + ", ".join(hors_portee))
    return {
        "source": source,
        "fichiers_modifies": sorted(set(changements)),
        "nombre_fichiers": len(set(changements)),
        "publication_effectuee": False,
    }


def changements_git(racine: Path = RACINE) -> list[str]:
    """Lire les chemins de statut Git, sans confondre noms et données."""
    sortie = _commande("git", "status", "--porcelain=v1", "--untracked-files=all",
                       "-z", cwd=racine)
    # Les fichiers produits sont dans des chemins contrôlés ; les noms contenant
    # espaces ou caractères spéciaux sont refusés au stade de publication.
    champs = sortie.split("\0")
    chemins = []
    indice = 0
    while indice < len(champs):
        ligne = champs[indice]
        indice += 1
        if not ligne:
            continue
        if len(ligne) < 4 or ligne[2] != " ":
            raise PublicationRefusee("Statut Git incohérent.")
        status = ligne[:2]
        nom = ligne[3:]
        if "R" in status or "C" in status:
            if indice >= len(champs):
                raise PublicationRefusee("Renommage Git incomplet.")
            origine = champs[indice]
            indice += 1
            chemins.append(origine)
        chemins.append(nom)
    return chemins


def verifier_arbre_sain(source: str, racine: Path = RACINE) -> dict:
    """Vérifier l'absence de modifications accidentelles avant publication."""
    return verifier_portee(source, changements_git(racine))


def identite_branche(source: str, id_execution: str, tentative: str) -> str:
    nom = f"automatisation/{source}-{id_execution}-{tentative}"
    if source not in CHEMINS or not BRANCH.fullmatch(nom):
        raise PublicationRefusee("Identifiant de branche automatique non conforme.")
    return nom


def _environnement_publication(source: str) -> tuple[str, str]:
    """N'autoriser la publication que dans une procédure du dépôt principal."""
    env = os.environ
    evenement = env.get("GITHUB_EVENT_NAME")
    if env.get("GITHUB_REF") != "refs/heads/main" or evenement not in {"push", "schedule", "workflow_dispatch"}:
        raise PublicationRefusee("Publication réservée aux procédures de la branche principale.")
    depot = env.get("GITHUB_REPOSITORY", "")
    if not REPO.fullmatch(depot):
        raise PublicationRefusee("Dépôt GitHub non identifié.")
    if not env.get("GH_TOKEN"):
        raise PublicationRefusee("Jeton d'action GitHub absent.")
    branche = identite_branche(source, env.get("GITHUB_RUN_ID", ""), env.get("GITHUB_RUN_ATTEMPT", ""))
    return depot, branche


def publier(source: str, racine: Path = RACINE) -> dict:
    """Créer une proposition sans remplacement ni publication directe sur main."""
    depot, branche = _environnement_publication(source)
    rapport = verifier_arbre_sain(source, racine)
    if not rapport["nombre_fichiers"]:
        return dict(rapport, etat="inchangé")

    _commande("git", "fetch", "--quiet", "origin", "main", cwd=racine)
    depart = _commande("git", "rev-parse", "HEAD", cwd=racine).strip()
    actuel = _commande("git", "rev-parse", "origin/main", cwd=racine).strip()
    if depart != actuel:
        raise PublicationRefusee("La branche principale a avancé depuis la collecte : relancer les ingestions.")

    # Une seule proposition en attente par source afin d'éviter les publications
    # concurrentes issues de la même base.
    liste = _commande("gh", "pr", "list", "--repo", depot, "--state", "open",
                     "--base", "main", "--json", "headRefName", "--limit", "1000", cwd=racine)
    try:
        propositions = json.loads(liste)
    except json.JSONDecodeError as exc:
        raise PublicationRefusee("Liste des propositions illisible.") from exc
    if not isinstance(propositions, list) or any(
        isinstance(item, dict) and str(item.get("headRefName", "")).startswith(f"automatisation/{source}-")
        for item in propositions
    ):
        raise PublicationRefusee("Une proposition de la même source attend déjà une décision.")

    _commande("git", "switch", "-c", branche, cwd=racine)
    _commande("git", "add", "-A", "--", *CHEMINS[source], cwd=racine)
    fichiers = _commande("git", "diff", "--cached", "--name-only", "-z", cwd=racine).split("\0")
    fichiers = [x for x in fichiers if x]
    verifier_portee(source, fichiers)
    if not fichiers:
        raise PublicationRefusee("Aucune modification admissible à publier.")
    # Aucune proposition issue du jeton automatique ne doit être fusionnée
    # avant exécution d'un contrôle explicite sur son empreinte de branche.
    _commande("git", "config", "user.name", "frontiere-referentiel[bot]", cwd=racine)
    _commande("git", "config", "user.email", "frontiere-referentiel@users.noreply.github.com", cwd=racine)
    _commande("git", "commit", "-m", TITRES[source], cwd=racine)
    _commande("gh", "auth", "setup-git", cwd=racine)
    _commande("git", "push", "origin", f"HEAD:refs/heads/{branche}", cwd=racine)
    description = (
        f"Actualisation automatique de la source « {source} », générée à partir "
        "d'un état de main vérifié.\n\n"
        "Les fichiers ont été sélectionnés par une liste fermée et les validations "
        "d'ingestion ont été exécutées en amont. "
        "Les vérifications Python et conteneur sont déclenchées séparément sur "
        "cette branche. **Aucune fusion automatique n'est demandée.** "
        "Cette proposition ne constitue pas une vérification humaine "
        "de la pertinence des données institutionnelles."
    )
    _commande("gh", "pr", "create", "--repo", depot, "--base", "main",
             "--head", branche, "--title", TITRES[source],
             "--body", description, cwd=racine)
    _commande("gh", "workflow", "run", "ci.yml", "--repo", depot, "--ref", branche, cwd=racine)
    return dict(rapport, etat="proposition_ouverte", publication_effectuee=True, branche=branche)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=tuple(CHEMINS), required=True)
    parser.add_argument("--publier", action="store_true",
                        help="Utilisation exclusivement dans une procédure GitHub autorisée.")
    args = parser.parse_args()
    try:
        resultat = publier(args.source) if args.publier else verifier_arbre_sain(args.source)
    except (PublicationRefusee, OSError) as exc:
        parser.exit(1, f"Publication refusée : {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
