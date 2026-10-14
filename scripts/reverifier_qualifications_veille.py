"""Surveiller la dérive des publications préqualifiées sans entraver la collecte.

Le fichier de qualification est un instantané documentaire. Une modification
de l'empreinte de la source déclenche une nouvelle relecture scientifique,
sans transformer le relevé récent en preuve d'un besoin public.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

RACINE = Path(__file__).resolve().parents[1]
REGISTRE = Path("institutionnel/veille/revue_signaux_2026_10_14.json")
ARCHIVE = Path("institutionnel/flux_publics/observations.json")
HASH = re.compile(r"[0-9a-f]{64}\Z")


class RevueInvalide(ValueError):
    """La filiation du corpus de revue ne peut pas être contrôlée."""


def evaluer_revisions(registre: dict, observations: dict,
                     maintenant: datetime) -> dict:
    """Comparer les identifiants et empreintes sans modifier aucun registre."""
    if registre.get("version") != "revue-signaux-v1":
        raise RevueInvalide("Version de qualification inconnue")
    fiches = registre.get("observations")
    sources = observations.get("observations")
    if not isinstance(fiches, list) or not isinstance(sources, list):
        raise RevueInvalide("Registre ou source sans liste d'observations")

    index = {}
    for source in sources:
        if not isinstance(source, dict):
            raise RevueInvalide("Source mal formée")
        uid = source.get("identifiant_publication")
        if not isinstance(uid, str) or uid in index:
            raise RevueInvalide("Identifiant de source absent ou dupliqué")
        index[uid] = source

    resultat = []
    vus = set()
    for fiche in fiches:
        if not isinstance(fiche, dict):
            raise RevueInvalide("Qualification mal formée")
        uid = fiche.get("id_observation")
        original = fiche.get("empreinte_contenu_reference")
        if (not isinstance(uid, str) or not HASH.fullmatch(uid)
                or uid in vus or not isinstance(original, str)
                or not HASH.fullmatch(original)):
            raise RevueInvalide("Identifiant ou empreinte de qualification invalide")
        vus.add(uid)
        source = index.get(uid)
        etat = "observation_absente"
        if source is not None:
            if source.get("source_id") != fiche.get("source_id"):
                etat = "identite_source_modifiee"
            elif source.get("empreinte_contenu") == original:
                etat = "identique"
            else:
                etat = "revision_a_requalifier"
        resultat.append({
            "id_observation": uid,
            "source_id": fiche.get("source_id"),
            "etat": etat,
            "empreinte_reference": original,
            "empreinte_courante": source.get("empreinte_contenu") if source else None,
            "interprétation_validee": False,
        })

    comptes = {etat: sum(x["etat"] == etat for x in resultat) for etat in (
        "identique", "revision_a_requalifier", "identite_source_modifiee",
        "observation_absente"
    )}
    return {
        "version": 1,
        "controle_le": maintenant.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "nombre_qualifications": len(resultat),
        "comptes": comptes,
        "nouvelle_validation_scientifique_effectuee": False,
        "qualifications": resultat,
    }


def rapport(resultat: dict) -> str:
    lignes = [
        "## FRONTIÈRE — surveillance des qualifications documentaires",
        f"Contrôle : {resultat['controle_le']}. "
        "Une correspondance d'empreinte ne confirme pas la véracité de la source.",
        "",
    ]
    for etat, total in resultat["comptes"].items():
        lignes.append(f"- {etat} : {total}")
    for fiche in resultat["qualifications"]:
        if fiche["etat"] != "identique":
            lignes.append(
                f"- Relecture nécessaire : {fiche['id_observation']} "
                f"({fiche['etat']})"
            )
    lignes.append("")
    lignes.append("Une observation modifiée reste archivée. Sa qualification antérieure "
                  "ne sera pas automatiquement propagée à la nouvelle version.")
    return "\n".join(lignes) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--racine", type=Path, default=RACINE)
    parser.add_argument("--sortie-json", type=Path)
    parser.add_argument("--resume-markdown", type=Path)
    args = parser.parse_args()
    try:
        registre = json.loads((args.racine / REGISTRE).read_text(encoding="utf-8"))
        observations = json.loads((args.racine / ARCHIVE).read_text(encoding="utf-8"))
        resultat = evaluer_revisions(registre, observations, datetime.now(timezone.utc))
    except (OSError, ValueError, TypeError) as exc:
        print(f"Relecture impossible : {type(exc).__name__}: {exc}")
        return 1
    sortie = rapport(resultat)
    print(sortie)
    if args.sortie_json:
        args.sortie_json.parent.mkdir(parents=True, exist_ok=True)
        args.sortie_json.write_text(
            json.dumps(resultat, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.resume_markdown:
        args.resume_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.resume_markdown.write_text(sortie, encoding="utf-8")
    # Une révision ou disparition est un signal scientifique, non une raison
    # de bloquer l'ingestion des autres nouvelles publications.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
