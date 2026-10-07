from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RegleVariation:
    chemin: str
    variation_relative_max: float
    variation_absolue_min: int


CONFIGURATION = {
    "roae": {
        "fichier": "institutionnel/statistiques_roae.json",
        "regles": (
            RegleVariation("nombre_entites_canoniques", 0.03, 100),
            RegleVariation("nombre_relations_hierarchiques", 0.05, 200),
            RegleVariation("liens_hierarchiques_non_resolus", 0.75, 100),
        ),
    },
    "annuaire": {
        "fichier": "institutionnel/statistiques_annuaire_local.json",
        "regles": (
            RegleVariation("nombre_enregistrements_export_complet", 0.03, 1000),
            RegleVariation("nombre_entites_canoniques", 0.03, 1000),
            RegleVariation("nombre_relations_hierarchiques", 0.20, 1000),
            RegleVariation("couverture.avec_territoire_direct", 0.05, 2000),
        ),
    },
    "cog": {
        "fichier": "institutionnel/statistiques_cog.json",
        "regles": (
            RegleVariation("nombre_territoires", 0.02, 500),
            RegleVariation("nombre_relations", 0.05, 5000),
            RegleVariation("resolution_annuaire.references_codes_insee", 0.05, 10000),
        ),
    },
}


def extraire(objet: dict[str, Any], chemin: str) -> int | float:
    valeur: Any = objet
    for morceau in chemin.split("."):
        if not isinstance(valeur, dict) or morceau not in valeur:
            raise KeyError(chemin)
        valeur = valeur[morceau]
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise TypeError(f"{chemin} n'est pas numérique: {valeur!r}")
    return valeur


def evaluer_variations(
    precedent: dict[str, Any],
    courant: dict[str, Any],
    regles: tuple[RegleVariation, ...],
) -> dict[str, Any]:
    mesures: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    for regle in regles:
        ancien = extraire(precedent, regle.chemin)
        nouveau = extraire(courant, regle.chemin)
        delta = nouveau - ancien
        delta_absolu = abs(delta)
        variation_relative = None if ancien == 0 else delta_absolu / abs(ancien)
        violation = (
            ancien != 0
            and delta_absolu >= regle.variation_absolue_min
            and variation_relative is not None
            and variation_relative >= regle.variation_relative_max
        )
        mesure = {
            "metrique": regle.chemin,
            "precedent": ancien,
            "courant": nouveau,
            "delta": delta,
            "variation_relative": round(variation_relative, 6) if variation_relative is not None else None,
            "seuil_relatif": regle.variation_relative_max,
            "seuil_absolu_min": regle.variation_absolue_min,
            "violation": violation,
        }
        mesures.append(mesure)
        if violation:
            violations.append(mesure)

    return {"mesures": mesures, "violations": violations}


def lire_json_git(ref: str, fichier: str) -> dict[str, Any] | None:
    resultat = subprocess.run(
        ["git", "show", f"{ref}:{fichier}"],
        cwd=RACINE,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultat.returncode != 0:
        return None
    return json.loads(resultat.stdout)


def lire_json_courant(fichier: str) -> dict[str, Any]:
    return json.loads((RACINE / fichier).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refuse une variation structurelle silencieuse d'un snapshot institutionnel."
    )
    parser.add_argument("--source", choices=sorted(CONFIGURATION), required=True)
    parser.add_argument("--base-ref", default="HEAD")
    args = parser.parse_args()

    configuration = CONFIGURATION[args.source]
    fichier = configuration["fichier"]
    precedent = lire_json_git(args.base_ref, fichier)
    courant = lire_json_courant(fichier)

    if precedent is None:
        print(json.dumps({"source": args.source, "statut": "SANS_BASE", "fichier": fichier}, ensure_ascii=False))
        return

    rapport = evaluer_variations(precedent, courant, configuration["regles"])
    sortie = {
        "source": args.source,
        "statut": "A_REVOIR" if rapport["violations"] else "CONFORME",
        "fichier": fichier,
        **rapport,
    }
    print(json.dumps(sortie, ensure_ascii=False))

    if rapport["violations"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
