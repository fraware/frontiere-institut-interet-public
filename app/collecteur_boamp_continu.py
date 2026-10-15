"""Collecte BOAMP directe vers une base persistante, hors du cycle GitHub.

Le collecteur officiel existant interroge les sept derniers jours. Chaque
relevé est conservé dans un fichier local, puis indexé transactionnellement.
Une exécution continue exige un processus hébergé en permanence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Callable

from app.plateforme_boamp import StockageBOAMP, _normaliser
from scripts.collecter_besoins_publics import relever_boamp

VERSION = "boamp-direct-persistant-v1"
FICHIER = "dernier_releve_boamp.json"
TAILLE_MAX = 48 * 1024 * 1024


def _enregistrer_atomiquement(chemin: Path, donnees: dict) -> None:
    """Publier un relevé complet en une seule opération de remplacement."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    octets = (json.dumps(donnees, ensure_ascii=False, sort_keys=True, indent=2)
              + "\n").encode("utf-8")
    if len(octets) > TAILLE_MAX:
        raise ValueError("Relevé BOAMP dépassant le plafond de conservation.")
    provisoire: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=chemin.parent, prefix=".boamp-", delete=False
        ) as sortie:
            provisoire = sortie.name
            sortie.write(octets)
            sortie.flush()
            os.fsync(sortie.fileno())
        os.replace(provisoire, chemin)
    finally:
        if provisoire is not None and os.path.exists(provisoire):
            os.unlink(provisoire)


def _ancien_releve(chemin: Path, maintenant: datetime) -> dict:
    """Conserver la fenêtre de recherche, laisser les anciens avis dans la base."""
    if not chemin.exists():
        return {"annonces": []}
    if chemin.stat().st_size > TAILLE_MAX:
        raise ValueError("Ancien relevé BOAMP trop volumineux.")
    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    if (not isinstance(contenu, dict) or contenu.get("version") != VERSION
            or not isinstance(contenu.get("releve"), dict)
            or not isinstance(contenu["releve"].get("annonces"), list)):
        raise ValueError("Ancien relevé BOAMP incorrect ou incompatible.")
    debut = (maintenant.date() - timedelta(days=8)).isoformat()
    avis = [
        val for val in contenu["releve"]["annonces"]
        if isinstance(val, dict) and isinstance(val.get("date_parution"), str)
        and val["date_parution"][:10] >= debut
    ]
    return {"annonces": avis}


def cycle(
    stockage: StockageBOAMP,
    repertoire: Path,
    *,
    maintenant: datetime | None = None,
    obtenir: Callable | None = None,
    attendre: Callable[[float], None] = time.sleep,
    pages: int = 45,
) -> dict:
    """Collecter, indexer, puis conserver l'état nécessaire au cycle suivant.

    Toutes les réponses officielles sont analysées par le collecteur existant.
    Une collecte partielle est déclarée comme telle ; elle n'est pas assimilée
    à une couverture intégrale de la fenêtre.
    """
    horloge = maintenant or datetime.now(timezone.utc)
    if horloge.tzinfo is None:
        raise ValueError("Une date de collecte doit porter un fuseau.")
    horloge = horloge.astimezone(timezone.utc)
    chemin = repertoire / FICHIER
    ancien = _ancien_releve(chemin, horloge)
    options = {"maintenant": horloge, "pages": pages, "attendre": attendre}
    if obtenir is not None:
        options["obtenir"] = obtenir
    releve, rapport = relever_boamp(ancien, **options)
    avis = [_normaliser(x, jour=None) for x in releve["annonces"]]
    brut = json.dumps(releve, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    empreinte = hashlib.sha256(brut).hexdigest()
    capture = {
        "chemin": "flux-boamp-direct",
        "empreinte": empreinte,
        "observe_le": horloge.replace(microsecond=0).isoformat(),
        "jour": None,
        "jour_complet": False,
    }
    deja = stockage.capture_deja(capture["chemin"], empreinte)
    stockage.ingerer(capture, avis)
    _enregistrer_atomiquement(chemin, {
        "version": VERSION,
        "releve": releve,
        "rapport": rapport,
        "capture_sha256": empreinte,
    })
    return {
        "source": "BOAMP",
        "observe_le": capture["observe_le"],
        "annonces_retenues": len(avis),
        "nouvelle_capture": not deja,
        "recherche_partielle": rapport.get("recherche_partielle"),
        "pages_reussies": rapport.get("pages_reussies"),
        "total_source_declare": rapport.get("total_annonces_recherche_declare"),
        "avis_en_base": stockage.etat()["avis_distincts"],
        "fichier_local": str(chemin),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="URL SQLAlchemy de la base durable")
    parser.add_argument("--repertoire", type=Path, required=True,
                        help="Dossier privé des relevés directs BOAMP")
    parser.add_argument("--pages", type=int, default=45)
    parser.add_argument("--suivre", action="store_true",
                        help="Interroger périodiquement BOAMP jusqu'à l'arrêt du service")
    parser.add_argument("--intervalle", type=int, default=1800,
                        help="Intervalle en secondes ; défaut 1800 (30 minutes)")
    args = parser.parse_args(argv)
    if not 1 <= args.pages <= 50:
        parser.error("Le nombre de pages doit être compris entre 1 et 50.")
    if args.suivre and not 900 <= args.intervalle <= 86400:
        parser.error("L'intervalle permanent doit être compris entre 900 et 86400 secondes.")
    base = StockageBOAMP(args.base)
    while True:
        try:
            rapport = cycle(base, args.repertoire, pages=args.pages)
            print(json.dumps(rapport, ensure_ascii=False, sort_keys=True), flush=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            print(json.dumps({
                "source": "BOAMP", "collecte_reussie": False,
                "erreur": type(exc).__name__, "detail": str(exc),
                "observe_le": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False), file=sys.stderr, flush=True)
            if not args.suivre:
                return 1
        if not args.suivre:
            return 0
        time.sleep(args.intervalle)


if __name__ == "__main__":
    sys.exit(main())
