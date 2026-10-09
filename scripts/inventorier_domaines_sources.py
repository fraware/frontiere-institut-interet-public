"""Repérer les domaines qui hébergent les ressources annoncées dans les catalogues.

Aucun domaine découvert n'est interrogé automatiquement. Le relevé permet
de déterminer quelles nouvelles sources officielles ou institutionnelles
méritent l'ouverture ultérieure d'un connecteur contrôlé.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit

RACINE = Path(__file__).resolve().parents[1]
REPERTOIRE = RACINE / "institutionnel/decouverte"
CANDIDATS = REPERTOIRE / "candidats_data_gouv.json"
SOURCES = RACINE / "institutionnel/sources_v1.json"
SORTIE = REPERTOIRE / "domaines_sources.json"
MAX_EXEMPLES = 4


def extraire_domaine(valeur: object) -> str | None:
    if not isinstance(valeur, str) or len(valeur) > 2048:
        return None
    try:
        url = urlsplit(valeur)
        if url.scheme not in {"http", "https"} or url.username or url.password:
            return None
        domaine = url.hostname
        if not domaine or len(domaine) > 253 or "." not in domaine:
            return None
        try:
            ipaddress.ip_address(domaine)
            return None
        except ValueError:
            pass
        if domaine.endswith((".localhost", ".local", ".internal", ".test", ".invalid")):
            return None
        return domaine.lower()
    except ValueError:
        return None


def domaines_deja_suivis(sources: dict) -> set[str]:
    domaines = set()
    for item in sources.get("sources", []):
        if not isinstance(item, dict):
            continue
        for cle in ("metadata_url", "page_url", "resource_url"):
            domaine = extraire_domaine(item.get(cle))
            if domaine:
                domaines.add(domaine)
    return domaines


def inventorier(donnees: dict, registre: dict, instant: str | None = None) -> dict:
    candidats = donnees.get("candidats")
    if not isinstance(candidats, list):
        raise ValueError("Liste des notices non structurée.")
    connus = domaines_deja_suivis(registre)
    index: dict[str, dict] = defaultdict(lambda: {"jeux": set(), "ressources": 0})
    for fiche in candidats:
        if not isinstance(fiche, dict) or not isinstance(fiche.get("id"), str):
            continue
        uid = fiche["id"]
        for res in fiche.get("ressources", []):
            if not isinstance(res, dict):
                continue
            domaine = extraire_domaine(res.get("url"))
            if not domaine:
                continue
            index[domaine]["jeux"].add(uid)
            index[domaine]["ressources"] += 1
    lignes = []
    for domaine, item in sorted(index.items()):
        lignes.append({
            "domaine": domaine,
            "nombre_jeux_distincts": len(item["jeux"]),
            "nombre_references_ressources": item["ressources"],
            "exemples_identifiants_jeux": sorted(item["jeux"])[:MAX_EXEMPLES],
            "domaine_deja_present_dans_registre": domaine in connus,
            "connexion_automatique_autorisee": False,
        })
    return {
        "version": "domaines-sources-v1",
        "controle_le": instant or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "nombre_domaines_distincts": len(lignes),
        "nombre_domaines_hors_registre": sum(
            not item["domaine_deja_present_dans_registre"] for item in lignes
        ),
        "domaines": lignes,
        "nouvelle_source_automatiquement_aspiree": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidats", type=Path, default=CANDIDATS)
    parser.add_argument("--registre", type=Path, default=SOURCES)
    parser.add_argument("--sortie", type=Path, default=SORTIE)
    a = parser.parse_args()
    try:
        cand = json.loads(a.candidats.read_text(encoding="utf-8"))
        reg = json.loads(a.registre.read_text(encoding="utf-8"))
        if not isinstance(cand, dict) or not isinstance(reg, dict):
            raise ValueError("Structure du registre incorrecte.")
        resultat = inventorier(cand, reg)
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        temp = a.sortie.with_suffix(".json.temp")
        temp.write_text(json.dumps(resultat, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(a.sortie)
        print(json.dumps({
            k: v for k, v in resultat.items() if k != "domaines"
        }, ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Inventaire des domaines interrompu : {exc}\n")


if __name__ == "__main__":
    main()
