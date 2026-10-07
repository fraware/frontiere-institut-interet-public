from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[1]

DOSSIER_TERRITOIRES = RACINE / "institutionnel" / "territoires" / "cog"
DOSSIER_ENTITES_LOCALES = RACINE / "institutionnel" / "entites" / "locales"
HISTORIQUE_COMMUNES = (
    RACINE
    / "institutionnel"
    / "evenements"
    / "cog"
    / "historique_communes_depuis_1943.jsonl"
)
MANIFESTE_COG = RACINE / "institutionnel" / "instantanes" / "cog_manifest.json"
MANIFESTE_LOCAL = (
    RACINE / "institutionnel" / "instantanes" / "annuaire_local_manifest.json"
)
SORTIE = RACINE / "institutionnel" / "resolution_territoires_dila_cog.json"

TYPES_COMMUNAUX = {
    "COMMUNE": 0,
    "ARRONDISSEMENT_MUNICIPAL": 1,
    "COMMUNE_ASSOCIEE": 2,
    "COMMUNE_DELEGUEE": 2,
}


class ErreurResolutionTerritoriale(RuntimeError):
    """Erreur explicite de résolution entre l'Annuaire DILA et le COG."""


def maintenant_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def nettoyer(valeur: Any) -> str | None:
    if valeur is None:
        return None
    texte = str(valeur).strip().upper()
    return texte or None


def charger_json(chemin: Path) -> dict[str, Any]:
    if not chemin.exists():
        raise ErreurResolutionTerritoriale(f"Fichier requis absent: {chemin}")
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    if not isinstance(donnees, dict):
        raise ErreurResolutionTerritoriale(f"Objet JSON attendu: {chemin}")
    return donnees


def charger_index_territoires(
    dossier: Path,
) -> dict[str, list[dict[str, Any]]]:
    par_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not dossier.exists():
        raise ErreurResolutionTerritoriale(
            "Le snapshot COG doit être ingéré avant la résolution DILA."
        )

    for chemin in sorted(dossier.glob("*.jsonl")):
        with chemin.open("r", encoding="utf-8") as fichier:
            for numero, ligne in enumerate(fichier, start=1):
                if not ligne.strip():
                    continue
                objet = json.loads(ligne)
                type_territoire = objet.get("type_territoire")
                if type_territoire not in TYPES_COMMUNAUX:
                    continue
                code = nettoyer(objet.get("code"))
                if not code:
                    raise ErreurResolutionTerritoriale(
                        f"Territoire communal sans code: {chemin}:{numero}"
                    )
                par_code[code].append(objet)

    return dict(par_code)


def choisir_territoire(
    candidats: list[dict[str, Any]],
) -> tuple[str, dict[str, Any] | list[dict[str, Any]] | None]:
    if not candidats:
        return "ABSENT", None

    classes: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for candidat in candidats:
        classes[TYPES_COMMUNAUX[candidat["type_territoire"]]].append(candidat)

    meilleure_priorite = min(classes)
    meilleurs = classes[meilleure_priorite]
    if len(meilleurs) == 1:
        return "RESOLU", meilleurs[0]
    return "AMBIGU", meilleurs


def charger_codes_historiques(chemin: Path) -> set[str]:
    codes: set[str] = set()
    if not chemin.exists():
        raise ErreurResolutionTerritoriale(
            "L'historique communal COG est absent."
        )
    with chemin.open("r", encoding="utf-8") as fichier:
        for numero, ligne in enumerate(fichier, start=1):
            if not ligne.strip():
                continue
            objet = json.loads(ligne)
            code = nettoyer(objet.get("code"))
            if not code:
                raise ErreurResolutionTerritoriale(
                    f"Historique communal sans code: {chemin}:{numero}"
                )
            codes.add(code)
    return codes


def iter_references_locales(
    dossier: Path,
):
    if not dossier.exists():
        raise ErreurResolutionTerritoriale(
            "Le snapshot local DILA est absent."
        )

    for chemin in sorted(dossier.glob("*.jsonl")):
        with chemin.open("r", encoding="utf-8") as fichier:
            for numero, ligne in enumerate(fichier, start=1):
                if not ligne.strip():
                    continue
                entite = json.loads(ligne)
                identifiant = entite.get("id")
                territoires = entite.get("territoires") or []
                if not isinstance(territoires, list):
                    raise ErreurResolutionTerritoriale(
                        f"territoires non-liste: {chemin}:{numero}"
                    )
                for valeur in territoires:
                    code = nettoyer(valeur)
                    if code:
                        yield identifiant, code


def empreinte_dependances(
    manifeste_cog: dict[str, Any],
    manifeste_local: dict[str, Any],
) -> str:
    cle = {
        "cog_sha256_archive": manifeste_cog.get("sha256_archive"),
        "cog_version_transformation": manifeste_cog.get("version_transformation"),
        "cog_millesime": manifeste_cog.get("millesime"),
        "annuaire_sha256_semantique": manifeste_local.get(
            "sha256_semantique_export"
        ),
        "annuaire_version_transformation": manifeste_local.get(
            "version_transformation"
        ),
    }
    if not all(cle.values()):
        raise ErreurResolutionTerritoriale(
            "Les manifestes ne contiennent pas toutes les identités de dépendance."
        )
    brut = json.dumps(cle, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def calculer_resolution(
    *,
    dossier_territoires: Path = DOSSIER_TERRITOIRES,
    dossier_entites: Path = DOSSIER_ENTITES_LOCALES,
    historique: Path = HISTORIQUE_COMMUNES,
    manifeste_cog_path: Path = MANIFESTE_COG,
    manifeste_local_path: Path = MANIFESTE_LOCAL,
) -> dict[str, Any]:
    index = charger_index_territoires(dossier_territoires)
    historiques = charger_codes_historiques(historique)
    manifeste_cog = charger_json(manifeste_cog_path)
    manifeste_local = charger_json(manifeste_local_path)

    entites_par_code: dict[str, list[str]] = defaultdict(list)
    total_references = 0
    for entite_id, code in iter_references_locales(dossier_entites):
        total_references += 1
        if len(entites_par_code[code]) < 20:
            entites_par_code[code].append(entite_id)

    compteurs = Counter()
    details = []
    for code in sorted(entites_par_code):
        statut, valeur = choisir_territoire(index.get(code, []))
        if statut == "RESOLU":
            compteurs["codes_resolus_courants"] += 1
            assert isinstance(valeur, dict)
            detail = {
                "code": code,
                "statut": "RESOLU_COURANT",
                "territoire_id": valeur["id"],
                "type_territoire": valeur["type_territoire"],
                "nom": valeur["nom_officiel"],
            }
        elif statut == "AMBIGU":
            compteurs["codes_ambigus"] += 1
            assert isinstance(valeur, list)
            detail = {
                "code": code,
                "statut": "AMBIGU",
                "candidats": [
                    {
                        "territoire_id": x["id"],
                        "type_territoire": x["type_territoire"],
                        "nom": x["nom_officiel"],
                    }
                    for x in valeur
                ],
            }
        elif code in historiques:
            compteurs["codes_historiques_seulement"] += 1
            detail = {
                "code": code,
                "statut": "HISTORIQUE_SEULEMENT",
            }
        else:
            compteurs["codes_inconnus"] += 1
            detail = {
                "code": code,
                "statut": "INCONNU",
            }

        detail["exemples_entites"] = entites_par_code[code]
        details.append(detail)

    return {
        "version": "1",
        "observe_le": maintenant_iso(),
        "dependances": {
            "cog_millesime": manifeste_cog.get("millesime"),
            "cog_sha256_archive": manifeste_cog.get("sha256_archive"),
            "cog_version_transformation": manifeste_cog.get(
                "version_transformation"
            ),
            "annuaire_sha256_semantique": manifeste_local.get(
                "sha256_semantique_export"
            ),
            "annuaire_version_transformation": manifeste_local.get(
                "version_transformation"
            ),
            "empreinte": empreinte_dependances(
                manifeste_cog,
                manifeste_local,
            ),
        },
        "nombre_references_territoriales": total_references,
        "nombre_codes_distincts": len(entites_par_code),
        "resultats": dict(sorted(compteurs.items())),
        "codes": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Résout les codes territoriaux des entités DILA vers les territoires COG."
        )
    )
    parser.add_argument("--sortie", type=Path, default=SORTIE)
    args = parser.parse_args()

    try:
        rapport = calculer_resolution()
    except (OSError, json.JSONDecodeError, ErreurResolutionTerritoriale) as exc:
        print(f"ERREUR: {exc}")
        return 2

    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(
        json.dumps(rapport, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "references": rapport["nombre_references_territoriales"],
                "codes": rapport["nombre_codes_distincts"],
                **rapport["resultats"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
