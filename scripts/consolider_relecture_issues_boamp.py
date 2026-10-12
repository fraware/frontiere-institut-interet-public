"""Vérifier et confronter deux relectures BOAMP sans créer un consensus fictif.

Deux fichiers cohérents ne garantissent pas une indépendance réelle. Les
désaccords sont conservés ; aucun résultat n'est promu automatiquement
au statut de référence scientifique.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

try:
    from scripts.preparer_relecture_issues_boamp import VERSION
except ModuleNotFoundError:
    from preparer_relecture_issues_boamp import VERSION

STATUTS = {"RESULTATS_PAR_LOT", "ATTRIBUTION_SANS_LOT",
           "SANS_RESULTAT_DANS_CET_AVIS", "INDETERMINE"}
DECISIONS = {"ATTRIBUE", "NON_ATTRIBUE", "INDETERMINE"}
CAUSES = {"NON_ETABLIE", "DOCUMENTEE", "INDETERMINEE"}
CHAMPS = ("decision", "code_motif", "offres_totales", "offres_electroniques", "cause_non_attribution")


class JugementInvalide(ValueError):
    """Un formulaire ne satisfait pas les critères annoncés."""


def sha(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def ouvrir(chemin: Path) -> dict:
    try:
        objet = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JugementInvalide("Jugements ou paquet non lisibles.") from exc
    if not isinstance(objet, dict):
        raise JugementInvalide("Racine JSON non structurée.")
    return objet


def verifier_formulaire(paquet: dict, fichier: Path, empreinte: str) -> dict:
    formulaire = ouvrir(fichier)
    if (formulaire.get("version") != VERSION
            or formulaire.get("sha256_paquet") != empreinte
            or formulaire.get("declaration_lecture_sans_predictions") is not True):
        raise JugementInvalide("Version, empreinte ou déclaration d'aveuglement absente.")
    identite = formulaire.get("identifiant_relecteur")
    if not isinstance(identite, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", identite):
        raise JugementInvalide("Identifiant de lecteur manquant ou invalide.")
    jugements = formulaire.get("jugements")
    attendu = [c["cas"] for c in paquet["cas"]]
    if (not isinstance(jugements, list)
            or [x.get("cas") for x in jugements if isinstance(x, dict)] != attendu
            or len(jugements) != len(attendu)):
        raise JugementInvalide("Ordre et présence des cas incohérents.")
    for i, j in enumerate(jugements):
        code = attendu[i]
        statut = j.get("statut_avis")
        if statut not in STATUTS:
            raise JugementInvalide("Avis non jugé : " + code)
        if not isinstance(j.get("preuve_statut"), str) or not j["preuve_statut"].strip():
            raise JugementInvalide("Preuve de statut manquante : " + code)
        lots = j.get("lots")
        if not isinstance(lots, list):
            raise JugementInvalide("Liste de lots absente.")
        if (statut == "RESULTATS_PAR_LOT") != bool(lots):
            raise JugementInvalide("Lots incompatibles avec le statut : " + code)
        deja = set()
        for lot in lots:
            if not isinstance(lot, dict):
                raise JugementInvalide("Résultat de lot non structuré.")
            nom = lot.get("lot")
            if (not isinstance(nom, str) or not 1 <= len(nom) <= 100
                    or nom in deja):
                raise JugementInvalide("Numéro de lot manquant ou répété.")
            deja.add(nom)
            if lot.get("decision") not in DECISIONS:
                raise JugementInvalide("Décision de lot invalide.")
            cause = lot.get("cause_non_attribution")
            if lot["decision"] == "ATTRIBUE":
                if cause != "SANS_OBJET":
                    raise JugementInvalide("Cause de non-attribution inappropriée.")
            elif cause not in CAUSES:
                raise JugementInvalide("Cause du lot non jugée.")
            if cause == "DOCUMENTEE" and (
                    not isinstance(lot.get("preuve_causale"), str)
                    or not lot["preuve_causale"].strip()):
                raise JugementInvalide("Cause annoncée sans preuve distincte.")
            if (lot.get("code_motif") is not None and
                    (not isinstance(lot["code_motif"], str)
                     or not lot["code_motif"].strip())):
                raise JugementInvalide("Motif officiel invalide.")
            for champ in ("offres_totales", "offres_electroniques"):
                n = lot.get(champ)
                if n is not None and (type(n) is not int or n < 0):
                    raise JugementInvalide("Effectif d'offres négatif ou non entier.")
            total, electroniques = lot.get("offres_totales"), lot.get("offres_electroniques")
            if total is not None and electroniques is not None and electroniques > total:
                raise JugementInvalide("Effectif électronique supérieur au total.")
            for champ in ("preuve_identifiant_lot", "preuve_decision"):
                if not isinstance(lot.get(champ), str) or not lot[champ].startswith("/"):
                    raise JugementInvalide("Preuve de numéro ou décision de lot manquante.")
            if lot.get("code_motif") is not None and (
                    not isinstance(lot.get("preuve_motif"), str)
                    or not lot["preuve_motif"].startswith("/")):
                raise JugementInvalide("Motif administratif sans preuve source.")
            for nombre, preuve in (
                    ("offres_totales", "preuve_offres_totales"),
                    ("offres_electroniques", "preuve_offres_electroniques")):
                if lot.get(nombre) is not None and (
                        not isinstance(lot.get(preuve), str)
                        or not lot[preuve].startswith("/")):
                    raise JugementInvalide("Chiffres d'offres sans passage source.")
    return formulaire


def consolider(paquet_path: Path, lecture_1: Path, lecture_2: Path,
              sortie: Path, dossier_sources: Path | None = None) -> dict:
    if sortie.exists() or sortie.is_symlink():
        raise JugementInvalide("Sortie existante : aucun écrasement.")
    paquet = ouvrir(paquet_path)
    if (paquet.get("version") != VERSION
            or paquet.get("references_independantes_etablies") is not False
            or paquet.get("prequalifications_automatiques_exclues") is not True
            or paquet.get("nombre_cas") != len(paquet.get("cas", []))):
        raise JugementInvalide("Paquet sans garantie de préparation.")
    empreinte = sha(paquet_path)
    a = verifier_formulaire(paquet, lecture_1, empreinte)
    b = verifier_formulaire(paquet, lecture_2, empreinte)
    if a["identifiant_relecteur"] == b["identifiant_relecteur"]:
        raise JugementInvalide("Les deux fichiers déclarent le même lecteur.")
    ancrages = None
    if dossier_sources is not None:
        try:
            from scripts.auditer_ancrages_relecture_issues_boamp import auditer
        except ModuleNotFoundError:
            from auditer_ancrages_relecture_issues_boamp import auditer
        ancrages = [
            auditer(paquet_path, lecture_1, dossier_sources),
            auditer(paquet_path, lecture_2, dossier_sources),
        ]
    accords = Counter()
    desaccords = []
    resultats = []
    for un, deux in zip(a["jugements"], b["jugements"]):
        code = un["cas"]
        statut_accord = un["statut_avis"] == deux["statut_avis"]
        accords["avis_statut_accord"] += int(statut_accord)
        lots_a = {lot["lot"]: lot for lot in un["lots"]}
        lots_b = {lot["lot"]: lot for lot in deux["lots"]}
        identifiants_egaux = set(lots_a) == set(lots_b)
        accords["avis_ensembles_lots_identiques"] += int(identifiants_egaux)
        if not statut_accord:
            desaccords.append({"cas": code, "dimension": "statut_avis",
                               "lecteur_1": un["statut_avis"],
                               "lecteur_2": deux["statut_avis"]})
        if not identifiants_egaux:
            desaccords.append({"cas": code, "dimension": "identifiants_lots",
                               "lecteur_1": sorted(lots_a),
                               "lecteur_2": sorted(lots_b)})
        for nom in sorted(set(lots_a) & set(lots_b)):
            accords["lots_communs"] += 1
            for champ in CHAMPS:
                concorde = lots_a[nom].get(champ) == lots_b[nom].get(champ)
                accords[champ + "_accord"] += int(concorde)
                if not concorde:
                    desaccords.append({
                        "cas": code, "lot": nom, "dimension": champ,
                        "lecteur_1": lots_a[nom].get(champ),
                        "lecteur_2": lots_b[nom].get(champ),
                    })
        resultats.append({
            "cas": code, "statut_accord": statut_accord,
            "identifiants_lots_accord": identifiants_egaux,
            "aucune_reference_automatiquement_etablie": True,
        })
    resultat = {
        "version": "consolidation-double-lecture-issues-boamp-v1",
        "sha256_paquet": empreinte, "sha256_jugement_1": sha(lecture_1),
        "sha256_jugement_2": sha(lecture_2),
        "nombre_cas": len(resultats),
        "compteurs_accord": dict(sorted(accords.items())),
        "nombre_desaccords": len(desaccords),
        "desaccords": desaccords,
        "cas": resultats,
        "ancrages_sources_verifies": ancrages is not None,
        "rapports_ancrages": [{
            "avis_controles": a["avis_controles"],
            "lots_ancres": a["lots_ancres"],
            "statistiques_verifiees": a["statistiques_verifiees"],
        } for a in ancrages] if ancrages is not None else [],
        "reference_consensuelle_etablie": False,
        "adjudication_independante_effectuee": False,
        "independance_reelle_verifiee_par_logiciel": False,
        "avertissement": ("Concordance entre formulaires déclarés ne prouve ni "
                          "indépendance intellectuelle, ni correction. Aucune "
                          "référence n'est établie automatiquement."),
    }
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with sortie.open("x", encoding="utf-8") as fichier:
        json.dump(resultat, fichier, ensure_ascii=False, sort_keys=True, indent=2)
        fichier.write("\n")
    return resultat


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paquet", type=Path, required=True)
    p.add_argument("--lecture-1", type=Path, required=True)
    p.add_argument("--lecture-2", type=Path, required=True)
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        bilan = consolider(a.paquet, a.lecture_1, a.lecture_2, a.sortie, a.sources)
        print(json.dumps({
            "cas": bilan["nombre_cas"],
            "desaccords": bilan["nombre_desaccords"],
            "reference_etablie": False,
        }, ensure_ascii=False))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        p.exit(1, f"Consolidation refusée : {exc}\n")


if __name__ == "__main__":
    main()
