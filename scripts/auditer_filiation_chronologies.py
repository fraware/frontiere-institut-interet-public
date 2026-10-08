"""Auditer automatiquement la filiation des chronologies publiques versionnées.

Le contrôle relève les révisions, fusions et retraits sans consulter les
documents officiels ; il n'attribue aucune validation historique nouvelle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def indexer_chronologies(document: dict) -> dict:
    valeurs = document.get("chronologies")
    if not isinstance(valeurs, list):
        raise ValueError("Chronologies absentes.")
    index = {}
    for chrono in valeurs:
        if not isinstance(chrono, dict):
            raise ValueError("Chronologie non structurée.")
        code = chrono.get("id_signal")
        if not isinstance(code, str) or code in index:
            raise ValueError("Identifiant de chronologie absent ou répété.")
        evenements = chrono.get("evenements")
        if not isinstance(evenements, list):
            raise ValueError(f"{code} : événements absents.")
        items = {}
        for rang, e in enumerate(evenements, 1):
            if not isinstance(e, dict):
                raise ValueError(f"{code} : événement invalide.")
            identifiant = e.get("id_evenement", f"{code}-E{rang:02d}")
            if not isinstance(identifiant, str) or identifiant in items or not identifiant.startswith(code + "-E"):
                raise ValueError(f"{code} : identifiant d'événement absent, étranger ou répété.")
            items[identifiant] = {k: v for k, v in e.items() if k != "id_evenement"}
        index[code] = {
            "faits": items,
            "metadonnees": {k: v for k, v in chrono.items() if k not in {"id_signal", "evenements"}},
        }
    return index


def nouveautes(courant: dict, precedent: dict, champ: str) -> list:
    anciens = precedent.get(champ, []) or []
    actuels = courant.get(champ, []) or []
    if not isinstance(anciens, list) or not isinstance(actuels, list):
        raise ValueError(f"{champ} doit être une liste.")
    if actuels[:len(anciens)] != anciens:
        raise ValueError(f"{champ} : l'historique déclaré a été réécrit.")
    return actuels[len(anciens):]


def controle_filiation(documents: list[dict]) -> dict:
    if not documents:
        raise ValueError("Aucune version à vérifier.")
    erreurs = []
    rapports = []
    precedent = None
    for position, document in enumerate(documents):
        attendu = position + 3
        if not isinstance(document, dict) or str(document.get("version")) != str(attendu):
            erreurs.append(f"Version attendue {attendu} : numéro de version absent ou incorrect.")
            break
        try:
            actuel = indexer_chronologies(document)
        except ValueError as exc:
            erreurs.append(f"Version {attendu} : {exc}")
            break
        if precedent is None:
            precedent = (document, actuel)
            continue
        doc_prec, index_prec = precedent
        version_prec = attendu - 1
        if set(index_prec) != set(actuel):
            erreurs.append(f"Passage {version_prec} → {attendu} : ensemble des dix cas modifié.")
        try:
            rectifications = nouveautes(document, doc_prec, "rectifications")
            fusions = nouveautes(document, doc_prec, "fusions_doublons")
            retraits = nouveautes(document, doc_prec, "retraits_evenements_non_confirmes")
        except ValueError as exc:
            erreurs.append(f"Passage {version_prec} → {attendu} : {exc}")
            rectifications, fusions, retraits = [], [], []

        codes_rectifies = set()
        for r in rectifications:
            if not isinstance(r, dict) or not isinstance(r.get("id_signal"), str):
                erreurs.append(f"Version {attendu} : rectification sans cas.")
                continue
            codes_rectifies.add(r["id_signal"])
            if not isinstance(r.get("nature"), str) or not r["nature"].strip():
                erreurs.append(f"Version {attendu} : rectification sans motif.")
            if not r.get("source") and not r.get("sources"):
                erreurs.append(f"Version {attendu} : rectification sans source.")

        suppressions_autorisees = set()
        for f in fusions:
            if not isinstance(f, dict):
                erreurs.append(f"Version {attendu} : fusion de format incorrect.")
                continue
            supp, conserve = f.get("identifiant_supprime"), f.get("identifiant_canonique")
            if not isinstance(supp, str) or not isinstance(conserve, str):
                erreurs.append(f"Version {attendu} : fusion sans identifiants.")
                continue
            suppressions_autorisees.add(supp)
            if not any(conserve in c["faits"] for c in actuel.values()):
                erreurs.append(f"Version {attendu} : cible de fusion inconnue : {conserve}.")
        for r in retraits:
            if not isinstance(r, dict) or not isinstance(r.get("identifiant_retire"), str):
                erreurs.append(f"Version {attendu} : retrait non identifié.")
                continue
            suppressions_autorisees.add(r["identifiant_retire"])
            if not isinstance(r.get("nature"), str) or not r["nature"].strip():
                erreurs.append(f"Version {attendu} : retrait sans justification.")
            if not r.get("source"):
                erreurs.append(f"Version {attendu} : retrait sans source.")

        modifications, supprimes, ajoutes = set(), [], []
        for code in set(index_prec) & set(actuel):
            ancien, nouveau = index_prec[code], actuel[code]
            avant, apres = ancien["faits"], nouveau["faits"]
            supprimes.extend(sorted(set(avant) - set(apres)))
            ajoutes.extend(sorted(set(apres) - set(avant)))
            if (ancien["metadonnees"] != nouveau["metadonnees"]
                    or any(avant[i] != apres[i] for i in set(avant) & set(apres))):
                modifications.add(code)
        if set(supprimes) != suppressions_autorisees:
            erreurs.append(f"Passage {version_prec} → {attendu} : suppressions non conformes aux fusions/retraits.")
        if ajoutes:
            erreurs.append(f"Passage {version_prec} → {attendu} : nouveaux événements sans dispositif d'ajout tracé.")
        if modifications != codes_rectifies:
            erreurs.append(
                f"Passage {version_prec} → {attendu} : cas modifiés {sorted(modifications)} "
                f"différents des rectifications motivées {sorted(codes_rectifies)}."
            )
        rapports.append({
            "de_version": version_prec,
            "a_version": attendu,
            "cas_rectifies": sorted(modifications),
            "evenements_supprimes": sorted(supprimes),
            "evenements_ajoutes": sorted(ajoutes),
            "rectifications_nouvelles": len(rectifications),
            "fusions_nouvelles": len(fusions),
            "retraits_nouveaux": len(retraits),
            "nombre_evenements": sum(len(x["faits"]) for x in actuel.values()),
        })
        precedent = (document, actuel)
    return {
        "version_schema": "audit-filiation-chronologies-v1",
        "versions_examinees": len(documents),
        "transitions": rapports,
        "valide_structurellement": not erreurs,
        "erreurs": erreurs,
        "limite": (
            "Ce contrôle établit la filiation interne des fichiers et des retraits déclarés ; "
            "il ne vérifie pas la correspondance entre leurs assertions et les pièces officielles."
        ),
    }


def principal() -> None:
    p = argparse.ArgumentParser(description="Vérifier les versions successives du corpus public.")
    p.add_argument("--dossier", type=Path, default=Path("donnees"))
    a = p.parse_args()
    chemins = [a.dossier / f"chronologies_v{n}.json" for n in range(3, 10)]
    docs = [json.loads(f.read_text(encoding="utf-8")) for f in chemins]
    bilan = controle_filiation(docs)
    bilan["empreintes_sha256"] = {
        chemin.name: hashlib.sha256(chemin.read_bytes()).hexdigest()
        for chemin in chemins
    }
    print(json.dumps(bilan, ensure_ascii=False, indent=2))
    if not bilan["valide_structurellement"]:
        raise SystemExit(1)


if __name__ == "__main__":
    principal()
