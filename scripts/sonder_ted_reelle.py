"""Vérifier la réponse réelle de TED Search API v3 sans importer de données.

Cet essai réseau est exécuté séparément des tests unitaires. Il effectue
une requête bornée sur une journée récente et vérifie uniquement le contrat
de réponse, les identifiants et les dates de publication observées.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from urllib.error import HTTPError, URLError

from app.collecteur_ted_continu import (
    CHAMPS, TEDInvalide, StockageTED, _notice, collecter_jour, requete_ted,
)


def sonder(jour: date, *, demander=requete_ted) -> dict:
    if jour > datetime.now(timezone.utc).date():
        raise TEDInvalide("Une journée future n'est pas admissible.")
    demande = {
        "query": (
            "buyer-country = FRA AND publication-date = "
            + jour.strftime("%Y%m%d")
        ),
        "fields": CHAMPS,
        "scope": "ALL",
        "limit": 25,
        "page": 1,
        "paginationMode": "PAGE_NUMBER",
    }
    resultat = demander(demande)
    if not isinstance(resultat, dict) or resultat.get("timedOut") is True:
        raise TEDInvalide("Le serveur TED a renvoyé une recherche expirée.")
    annonces = resultat.get("notices")
    total = resultat.get("totalNoticeCount")
    if (type(total) is not int or total < 0
            or not isinstance(annonces, list)
            or len(annonces) > 25 or len(annonces) > total):
        raise TEDInvalide("Contrat de réponse TED incompatible.")
    if total > 0 and not annonces:
        raise TEDInvalide("Aucun résultat dans une page pourtant non vide.")
    publications = [_notice(x, jour)["numero"] for x in annonces]
    if len(set(publications)) != len(publications):
        raise TEDInvalide("Deux numéros TED identiques sur la page.")
    return {
        "source": "TED Search API v3",
        "jour": jour.isoformat(),
        "resultats_declares": total,
        "resultats_examines": len(annonces),
        "premier_numero": publications[0] if publications else None,
        "controle_structurel": "reussi",
        "portee": "premiere_page_uniquement",
        "recupération_nationale_exhaustive": False,
    }


def sonder_integralement(jour: date, *, demander=requete_ted) -> dict:
    """Contrôler toutes les pages et l'importation dans une base temporaire."""
    notices, pages = collecter_jour(jour, obtenir=demander)
    with tempfile.TemporaryDirectory(prefix="frontiere-sonde-ted-") as dossier:
        stockage = StockageTED(Path(dossier) / "verification.sqlite3")
        premier = stockage.importer(jour, notices, pages)
        reprise = stockage.importer(jour, notices, pages)
        etat = stockage.etat()
    if (
        premier["etat"] != "actualisé"
        or reprise["etat"] != "inchangé"
        or etat["avis"] != len(notices)
        or etat["versions"] != len(notices)
        or etat["jours"] != 1
    ):
        raise TEDInvalide("Contrôle de persistance du corpus TED incohérent.")
    return {
        "source": "TED Search API v3",
        "jour": jour.isoformat(),
        "avis_recuperes": len(notices),
        "pages_recuperees": pages,
        "enregistrements_en_base": etat["avis"],
        "reprise_sans_doublon": True,
        "controle_integral": "reussi",
        "copie_temporaire_uniquement": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jour", type=date.fromisoformat,
        default=datetime.now(timezone.utc).date() - timedelta(days=2)
    )
    parser.add_argument("--complet", action="store_true",
                        help="Parcourir et importer provisoirement toute la journée")
    args = parser.parse_args(argv)
    try:
        bilan = sonder_integralement(args.jour) if args.complet else sonder(args.jour)
        print(json.dumps(bilan, ensure_ascii=False, sort_keys=True))
        return 0
    except (TEDInvalide, HTTPError, URLError, OSError, ValueError) as exc:
        print(f"Contrat TED non confirmé : {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
