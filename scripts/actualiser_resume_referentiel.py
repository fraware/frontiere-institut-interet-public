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
            "| Référentiel institutionnel | État |",
            "| --- | ---: |",
            "| Enregistrements du snapshot Annuaire DILA couverts | "
            f"{nombre(local['nombre_enregistrements_export_complet'])} / {nombre(local['nombre_enregistrements_export_complet'])} |",
            f"| Entités SI du ROAE | {nombre(roae['nombre_entites_canoniques'])} |",
            f"| Entités locales SL/SIL | {nombre(local['nombre_entites_canoniques'])} |",
            f"| Relations hiérarchiques SI résolues | {nombre(roae['nombre_relations_hierarchiques'])} |",
            f"| Relations hiérarchiques locales et croisées | {nombre(local['nombre_relations_hierarchiques'])} |",
            f"| Unités territoriales COG 2026 | {nombre(cog['nombre_territoires'])} |",
            f"| Relations territoriales COG | {nombre(cog['nombre_relations'])} |",
            "| Références Annuaire vers le COG courant | "
            f"{nombre(resolution['resolues'])} / {nombre(resolution['references_codes_insee'])} |",
            "| Références territoriales résiduelles expliquées par l’historique COG | "
            f"{nombre(resolution['absentes_courantes_expliquees_historiquement'])} / {nombre(resolution['absentes'])} |",
        ]
    )


def bloc_institutionnel(roae: dict[str, Any], local: dict[str, Any], cog: dict[str, Any]) -> str:
    cat = local["categories_export"]
    res = cog["resolution_annuaire"]
    lignes = [
        "Le dernier cycle complet du référentiel associe les états suivants :",
        "",
        f"- ROAE observé le **{date_iso(roae.get('observe_le'))}** : **{nombre(roae['nombre_entites_canoniques'])} SI** et **{nombre(roae['nombre_relations_hierarchiques'])} relations hiérarchiques** ;",
        f"- Annuaire local observé le **{date_iso(local.get('observe_le'))}** : **{nombre(local['nombre_enregistrements_export_complet'])} enregistrements**, dont **{nombre(cat['SI'])} SI**, **{nombre(cat['SL'])} SL** et **{nombre(cat['SIL'])} SIL** ; les catégories SL/SIL produisent **{nombre(local['nombre_entites_canoniques'])} entités locales** et **{nombre(local['nombre_relations_hierarchiques'])} relations locales ou croisées** ;",
        f"- COG observé le **{date_iso(cog.get('observe_le'))}** : **{nombre(cog['nombre_territoires'])} unités territoriales** et **{nombre(cog['nombre_relations'])} relations territoriales**.",
        "",
        f"Le croisement Annuaire–COG résout **{nombre(res['resolues'])} / {nombre(res['references_codes_insee'])}** références vers le COG courant. Les **{nombre(res['absentes'])}** références résiduelles sont toutes expliquées par les tables historiques officielles du COG ; **{nombre(res['absentes_sans_trace_historique'])}** référence reste sans trace historique et **{nombre(res['ambigues'])}** résolution est ambiguë.",
        "",
        f"Le croisement Annuaire–ROAE ferme **{nombre(local['resolution_croisee_roae']['resolues_par_annuaire_local'])} / {nombre(local['resolution_croisee_roae']['anomalies_roae_initiales'])}** références SI absentes du seul snapshot ROAE. L’Annuaire local conserve **{nombre(local['hierarchie']['anomalies'])}** références hiérarchiques dont la cible n’apparaît dans aucune catégorie courante.",
    ]
    return "\n".join(lignes)


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
            f"L’archive officielle produit **{nombre(cog['nombre_territoires'])} unités territoriales courantes** et **{nombre(cog['nombre_relations'])} relations territoriales** dans FRONTIÈRE, avec **{nombre(cog['anomalies_relations'])} relation territoriale non résolue**.",
            "",
            f"La répartition courante comprend {phrase_repartition}.",
            "",
            f"Le croisement avec l’Annuaire DILA examine **{nombre(res['references_codes_insee'])} références à des codes Insee** portées par **{nombre(res['entites_annuaire_avec_territoire'])} entités locales**. **{nombre(res['resolues'])} références** correspondent exactement à une unité du COG courant. Les **{nombre(res['absentes'])} références restantes** sont attestées par l’historique officiel du COG comme des codes ayant cessé d’être courants ; **{nombre(res['absentes_sans_trace_historique'])}** reste sans trace historique et **{nombre(res['ambigues'])}** cas est ambigu. Le taux de résolution vers le COG courant est de **{str(round(res['taux_resolution'] * 100, 4)).replace('.', ',')} %** et le taux de références expliquées par le COG courant ou son historique est de **{str(round(res['taux_references_expliquees'] * 100, 4)).replace('.', ',')} %**.",
            "",
            "Les écarts historiques ne sont pas réécrits. `resolution_annuaire_cog.json` conserve pour chacun le code DILA, l’entité concernée, la dernière période historique connue et le dernier événement communal publié par l’Insee.",
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
