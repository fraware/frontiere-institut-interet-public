from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[1]
INSTITUTIONNEL = RACINE / "institutionnel"

MARQUEURS = {
    RACINE / "README.md": (
        "<!-- FRONTIERE:ETAT_REFERENTIEL:DEBUT -->",
        "<!-- FRONTIERE:ETAT_REFERENTIEL:FIN -->",
    ),
    INSTITUTIONNEL / "README.md": (
        "<!-- FRONTIERE:ETAT_INSTITUTIONNEL:DEBUT -->",
        "<!-- FRONTIERE:ETAT_INSTITUTIONNEL:FIN -->",
    ),
    RACINE / "docs" / "INGESTION_COG_V1.md": (
        "<!-- FRONTIERE:ETAT_COG:DEBUT -->",
        "<!-- FRONTIERE:ETAT_COG:FIN -->",
    ),
}


def lire_json(nom: str) -> dict[str, Any]:
    return json.loads((INSTITUTIONNEL / nom).read_text(encoding="utf-8"))


def nombre(valeur: int | float) -> str:
    if isinstance(valeur, float) and not valeur.is_integer():
        return str(valeur).replace(".", ",")
    return f"{int(valeur):,}".replace(",", " ")


def date_iso(valeur: str | None) -> str:
    if not valeur:
        return "date inconnue"
    try:
        return datetime.fromisoformat(valeur.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return valeur


def bloc_readme(roae: dict[str, Any], local: dict[str, Any], cog: dict[str, Any]) -> str:
    resolution = cog["resolution_annuaire"]
    return "\n".join(
        [
            "| Couverture institutionnelle | État |",
            "| --- | ---: |",
            "| Enregistrements de l’Annuaire de l’administration couverts | "
            f"{nombre(local['nombre_enregistrements_export_complet'])} / {nombre(local['nombre_enregistrements_export_complet'])} |",
            f"| Services issus du Référentiel de l’organisation administrative de l’État | {nombre(roae['nombre_entites_canoniques'])} |",
            f"| Services et guichets locaux issus de l’Annuaire | {nombre(local['nombre_entites_canoniques'])} |",
            f"| Relations hiérarchiques résolues dans l’organisation de l’État | {nombre(roae['nombre_relations_hierarchiques'])} |",
            f"| Relations hiérarchiques résolues parmi les services locaux | {nombre(local['nombre_relations_hierarchiques'])} |",
            f"| Unités territoriales issues du Code officiel géographique 2026 | {nombre(cog['nombre_territoires'])} |",
            f"| Relations entre unités territoriales | {nombre(cog['nombre_relations'])} |",
            "| Références de l’Annuaire reliées à une unité territoriale actuelle | "
            f"{nombre(resolution['resolues'])} / {nombre(resolution['references_codes_insee'])} |",
            "| Références territoriales anciennes expliquées par l’historique officiel | "
            f"{nombre(resolution['absentes_courantes_expliquees_historiquement'])} / {nombre(resolution['absentes'])} |",
        ]
    )


def bloc_institutionnel(roae: dict[str, Any], local: dict[str, Any], cog: dict[str, Any]) -> str:
    res = cog["resolution_annuaire"]
    return "\n".join(
        [
            f"Dernier cycle complet observé le **{date_iso(cog.get('observe_le'))}** :",
            "",
            f"- **{nombre(roae['nombre_entites_canoniques'])} services ou organismes** issus du Référentiel de l’organisation administrative de l’État, avec **{nombre(roae['nombre_relations_hierarchiques'])} relations hiérarchiques résolues** ;",
            f"- **{nombre(local['nombre_entites_canoniques'])} services et guichets locaux** issus de l’Annuaire de l’administration, avec **{nombre(local['nombre_relations_hierarchiques'])} relations hiérarchiques locales ou croisées** ;",
            f"- **{nombre(cog['nombre_territoires'])} unités territoriales** issues du Code officiel géographique de l’Insee, reliées par **{nombre(cog['nombre_relations'])} relations territoriales**.",
            "",
            f"L’Annuaire contient **{nombre(res['references_codes_insee'])} références à des codes Insee**. **{nombre(res['resolues'])}** correspondent à une unité territoriale actuelle. Les **{nombre(res['absentes'])}** références restantes correspondent à d’anciens codes attestés par l’historique officiel. **{nombre(res['absentes_sans_trace_historique'])}** référence reste inexpliquée et **{nombre(res['ambigues'])}** cas est ambigu.",
            "",
            f"Le croisement des deux publications de la Direction de l’information légale et administrative résout également les **{nombre(local['resolution_croisee_roae']['resolues_par_annuaire_local'])} références hiérarchiques** dont la cible manquait dans la publication consacrée à l’organisation de l’État. Il reste **{nombre(local['hierarchie']['anomalies'])} références hiérarchiques locales** dont la cible n’apparaît dans aucune catégorie courante de l’Annuaire.",
        ]
    )


def bloc_cog(cog: dict[str, Any]) -> str:
    types = cog["types_territoires"]
    res = cog["resolution_annuaire"]
    repartition = [
        ("communes", types.get("COM", 0)),
        ("communes déléguées", types.get("COMD", 0)),
        ("cantons ou pseudo-cantons", types.get("CAN", 0)),
        ("communes associées", types.get("COMA", 0)),
        ("arrondissements", types.get("ARR", 0)),
        ("départements", types.get("DEP", 0)),
        ("arrondissements municipaux", types.get("ARM", 0)),
        ("régions", types.get("REG", 0)),
        ("collectivités ou territoires français d’outre-mer", types.get("COMER", 0)),
        ("zonages communaux associés à ces territoires", types.get("COMER-COM", 0)),
    ]
    phrase_repartition = ", ".join(f"{nombre(v)} {n}" for n, v in repartition)
    return "\n".join(
        [
            f"État du dernier cycle complet, observé le **{date_iso(cog.get('observe_le'))}**.",
            "",
            f"L’archive officielle produit **{nombre(cog['nombre_territoires'])} unités territoriales courantes** et **{nombre(cog['nombre_relations'])} relations entre territoires**, avec **{nombre(cog['anomalies_relations'])} relation non résolue**.",
            "",
            f"La répartition comprend {phrase_repartition}.",
            "",
            f"L’Annuaire de l’administration contient **{nombre(res['references_codes_insee'])} références à des codes Insee** portées par **{nombre(res['entites_annuaire_avec_territoire'])} services ou guichets locaux**. **{nombre(res['resolues'])} références** correspondent exactement à une unité territoriale actuelle. Les **{nombre(res['absentes'])} références restantes** correspondent à d’anciens codes attestés par l’historique officiel de l’Insee. **{nombre(res['absentes_sans_trace_historique'])}** référence reste sans trace historique et **{nombre(res['ambigues'])}** cas est ambigu.",
            "",
            f"Le taux de raccordement aux unités territoriales actuelles est de **{str(round(res['taux_resolution'] * 100, 4)).replace('.', ',')} %**. En tenant compte de l’historique officiel, **{str(round(res['taux_references_expliquees'] * 100, 4)).replace('.', ',')} %** des références sont expliquées.",
            "",
            "Le fichier " + chr(96) + "resolution_annuaire_cog.json" + chr(96) + " conserve pour chaque ancien code l’objet concerné, la dernière période historique connue et le dernier événement communal publié par l’Insee.",
        ]
    )


def remplacer_bloc(contenu: str, debut: str, fin: str, nouveau: str) -> str:
    if debut not in contenu or fin not in contenu:
        raise RuntimeError(f"Marqueurs absents: {debut} / {fin}")
    avant, reste = contenu.split(debut, 1)
    _, apres = reste.split(fin, 1)
    return f"{avant}{debut}\n{nouveau}\n{fin}{apres}"


def construire() -> dict[Path, str]:
    roae = lire_json("statistiques_roae.json")
    local = lire_json("statistiques_annuaire_local.json")
    cog = lire_json("statistiques_cog.json")
    return {
        RACINE / "README.md": bloc_readme(roae, local, cog),
        INSTITUTIONNEL / "README.md": bloc_institutionnel(roae, local, cog),
        RACINE / "docs" / "INGESTION_COG_V1.md": bloc_cog(cog),
    }


def actualiser(*, verifier: bool = False) -> list[str]:
    blocs = construire()
    divergences: list[str] = []
    for chemin, bloc in blocs.items():
        debut, fin = MARQUEURS[chemin]
        actuel = chemin.read_text(encoding="utf-8")
        attendu = remplacer_bloc(actuel, debut, fin, bloc)
        if attendu != actuel:
            divergences.append(str(chemin.relative_to(RACINE)))
            if not verifier:
                chemin.write_text(attendu, encoding="utf-8")
    return divergences


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronise les résumés documentaires avec les statistiques canoniques.")
    parser.add_argument("--verifier", action="store_true")
    args = parser.parse_args()
    divergences = actualiser(verifier=args.verifier)
    print(json.dumps({"divergences": divergences, "mode": "verification" if args.verifier else "ecriture"}, ensure_ascii=False))
    if args.verifier and divergences:
        raise SystemExit(4)


if __name__ == "__main__":
    main()
