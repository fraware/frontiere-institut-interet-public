"""Diagnostiquer le type des champs techniques BOAMP sans copier les avis."""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter
from urllib.parse import urlencode

try:
    from scripts.collecter_besoins_publics import BOAMP, recevoir, notice_boamp
except ModuleNotFoundError:
    from collecter_besoins_publics import BOAMP, recevoir, notice_boamp

VERSION = "audit-types-champs-boamp-v1"


def auditer(obtenir=recevoir):
    lien = BOAMP + "?" + urlencode({
        "select": "idweb,dateparution,etat,type_marche,type_marche_facette",
        "order_by": "dateparution desc",
        "limit": 100,
    })
    enveloppe = obtenir(lien, BOAMP)
    if not isinstance(enveloppe, dict) or not isinstance(enveloppe.get("results"), list):
        raise ValueError("Réponse officielle sans liste exploitable.")
    formes, extraits, categories, dates = Counter(), Counter(), Counter(), Counter()
    anomalies = 0
    for ligne in enveloppe["results"]:
        if not isinstance(ligne, dict):
            raise ValueError("Enregistrement officiel non structuré.")
        valeur = ligne.get("type_marche")
        formes[type(valeur).__name__] += 1
        categories[str(valeur)[:100]] += 1
        alternative = ligne.get("type_marche_facette")
        dates[str(ligne.get("dateparution"))[:7]] += 1
        normalisee = notice_boamp(ligne)
        if normalisee is None:
            anomalies += 1
            continue
        extraits[str(normalisee.get("categorie_marche"))] += 1
    return {
        "version": VERSION,
        "total_officiel_declare": enveloppe.get("total_count"),
        "enregistrements_examines": len(enveloppe["results"]),
        "types_python_type_marche": dict(formes),
        "valeurs_source_type_marche": dict(categories.most_common(20)),
        "valeurs_apres_normalisation": dict(extraits),
        "periodes_observees": dict(dates),
        "notices_sans_identifiant_normalisable": anomalies,
        "copie_des_notices_integrales": False,
        "preuve_de_categorie_historique": False,
    }


if __name__ == "__main__":
    print(json.dumps(auditer(), ensure_ascii=False, indent=2))
