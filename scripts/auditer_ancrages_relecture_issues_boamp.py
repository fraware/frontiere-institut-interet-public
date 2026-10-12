"""Contrôler les pointeurs vers les preuves primaires d'une relecture BOAMP.

Ce contrôle indépendant du classifieur ne fabrique ni étiquette de référence,
ni interprétation causale. Il vérifie le champ JSON effectivement indiqué.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

try:
    from scripts.consolider_relecture_issues_boamp import (
        ouvrir, verifier_formulaire, JugementInvalide,
    )
except ModuleNotFoundError:
    from consolider_relecture_issues_boamp import (
        ouvrir, verifier_formulaire, JugementInvalide,
    )


def pointeur(document: dict, reference: str):
    """JSON Pointer RFC6901, avec décodage explicite du champ BOAMP 'donnees'."""
    if not isinstance(reference, str) or not reference.startswith("/"):
        raise JugementInvalide("Chemin de preuve non absolu.")
    courant = document
    for jeton in reference[1:].split("/"):
        if re.search(r"~(?![01])", jeton):
            raise JugementInvalide("Échappement JSON Pointer invalide.")
        cle = jeton.replace("~1", "/").replace("~0", "~")
        if isinstance(courant, dict):
            if cle not in courant:
                raise JugementInvalide("Champ de preuve absent : " + reference)
            courant = courant[cle]
        elif isinstance(courant, list):
            if not re.fullmatch(r"0|[1-9]\d*", cle) or int(cle) >= len(courant):
                raise JugementInvalide("Indice de preuve invalide : " + reference)
            courant = courant[int(cle)]
        else:
            raise JugementInvalide("Chemin de preuve non résolu : " + reference)
        if cle == "donnees" and isinstance(courant, str):
            try:
                courant = json.loads(courant)
            except json.JSONDecodeError as exc:
                raise JugementInvalide("Formulaire BOAMP imbriqué illisible.") from exc
    return courant


def chaine(x):
    if isinstance(x, dict):
        return x.get("#text")
    return x


def chiffre(x):
    x = chaine(x)
    if type(x) is int and x >= 0:
        return x
    if isinstance(x, str) and x.isascii() and x.isdecimal():
        return int(x)
    raise JugementInvalide("Chiffre officiel non entier ou négatif.")


def verifier_compteur(source, chemin, attendu, code_officiel):
    if not isinstance(chemin, str) or not chemin.endswith("/efbc:StatisticsNumeric"):
        raise JugementInvalide("Pointeur numérique sans champ statistique canonique.")
    valeur = chiffre(pointeur(source, chemin))
    if valeur != attendu:
        raise JugementInvalide("Effectif déclaré incompatible avec le champ source.")
    base = chemin.rsplit("/", 1)[0]
    code = chaine(pointeur(source, base + "/efbc:StatisticsCode"))
    if code != code_officiel:
        raise JugementInvalide("Code de statistique différent du champ allégué.")
    return 1


def verifier_lot(source, lot):
    identifiant = lot["lot"]
    origine_lot = lot.get("preuve_identifiant_lot")
    if not isinstance(origine_lot, str) or "/efac:TenderLot/" not in origine_lot:
        raise JugementInvalide("Preuve d'identifiant de lot absente.")
    if chaine(pointeur(source, origine_lot)) != identifiant:
        raise JugementInvalide("Identifiant de lot différent de la preuve.")
    origine_decision = lot["preuve_decision"]
    if not origine_decision.endswith("/cbc:TenderResultCode/#text"):
        raise JugementInvalide("Preuve de décision sans code eForms officiel.")
    code_decision = pointeur(source, origine_decision)
    etat = {"selec-w": "ATTRIBUE", "clos-nw": "NON_ATTRIBUE"}
    if etat.get(code_decision, "INDETERMINE") != lot["decision"]:
        raise JugementInvalide("Décision de lot différente du code officiel.")
    # Le même nœud de résultat doit porter les deux identifiants.
    origine_resultat = origine_decision.removesuffix("/cbc:TenderResultCode/#text")
    if not origine_lot.startswith(origine_resultat + "/efac:TenderLot/"):
        raise JugementInvalide("Identifiant de lot issu d'une autre décision.")
    code_motif = lot.get("code_motif")
    if code_motif is not None:
        chemin = lot.get("preuve_motif")
        if (not isinstance(chemin, str)
                or not chemin.startswith(origine_resultat + "/")
                or not chemin.endswith("/efbc:DecisionReasonCode/#text")
                or pointeur(source, chemin) != code_motif):
            raise JugementInvalide("Motif officiel sans pointeur conforme.")
    total = lot.get("offres_totales")
    electronique = lot.get("offres_electroniques")
    comptes = 0
    if total is not None:
        origine = lot.get("preuve_offres_totales")
        if not isinstance(origine, str) or not origine.startswith(origine_resultat + "/"):
            raise JugementInvalide("Preuve du total d'offres non rattachée au lot.")
        comptes += verifier_compteur(source, origine, total, "tenders")
    if electronique is not None:
        origine = lot.get("preuve_offres_electroniques")
        if not isinstance(origine, str) or not origine.startswith(origine_resultat + "/"):
            raise JugementInvalide("Preuve électronique non rattachée au lot.")
        comptes += verifier_compteur(source, origine, electronique, "t-esubm")
    return comptes


def auditer(paquet_path: Path, formulaire_path: Path, sources: Path):
    paquet = ouvrir(paquet_path)
    digest = hashlib.sha256(paquet_path.read_bytes()).hexdigest()
    formulaire = verifier_formulaire(paquet, formulaire_path, digest)
    nombres = {"avis_controles": 0, "lots_ancres": 0, "statistiques_verifiees": 0}
    for cas, jugement in zip(paquet["cas"], formulaire["jugements"]):
        ident = cas["cas"]
        chemin_source = sources / (ident + ".json")
        if not chemin_source.is_file():
            raise JugementInvalide("Réponse BOAMP absente : " + ident)
        raw = chemin_source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != cas["sha256_source"]:
            raise JugementInvalide("Empreinte source incompatible : " + ident)
        source = json.loads(raw)
        if source.get("total_count") != 1 or len(source.get("results", [])) != 1:
            raise JugementInvalide("Réponse non unique : " + ident)
        avis = source["results"][0]
        if avis.get("idweb") != cas["avis"]:
            raise JugementInvalide("Mauvaise réponse officielle : " + ident)
        origine_statut = jugement["preuve_statut"]
        if origine_statut != "/results/0/nature":
            raise JugementInvalide("Le statut doit citer /results/0/nature.")
        nature = pointeur(source, origine_statut)
        if jugement["statut_avis"] in {"RESULTATS_PAR_LOT", "ATTRIBUTION_SANS_LOT"}:
            if nature != "ATTRIBUTION":
                raise JugementInvalide("Statut d'attribution contredit par la nature de l'avis.")
        elif nature == "ATTRIBUTION" and jugement["statut_avis"] == "SANS_RESULTAT_DANS_CET_AVIS":
            raise JugementInvalide("Avis d'attribution déclaré sans résultat dans la notice.")
        nombres["avis_controles"] += 1
        for lot in jugement["lots"]:
            nombres["statistiques_verifiees"] += verifier_lot(source, lot)
            nombres["lots_ancres"] += 1
    return {
        "version": "audit-ancrages-sources-boamp-v1",
        **nombres, "sha256_paquet": digest,
        "sha256_formulaire": hashlib.sha256(formulaire_path.read_bytes()).hexdigest(),
        "independance_des_lecteurs_etablie": False,
        "validite_causale_etablie": False,
        "interpretation": (
            "Les chemins cités conduisent aux valeurs officielles ; "
            "cela ne démontre pas l'exhaustivité des lots ou la qualité du jugement."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paquet", type=Path, required=True)
    p.add_argument("--jugements", type=Path, required=True)
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    if a.sortie.exists() or a.sortie.is_symlink():
        p.exit(1, "Sortie existante : aucun écrasement.\n")
    try:
        rapport = auditer(a.paquet, a.jugements, a.sources)
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        with a.sortie.open("x", encoding="utf-8") as f:
            json.dump(rapport, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        print(json.dumps(rapport, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.exit(1, f"Preuve documentaire non validée : {exc}\n")


if __name__ == "__main__":
    main()
