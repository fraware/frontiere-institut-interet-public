"""Relever les réponses officielles de l'ensemble d'épreuve enrichi.

La recherche par titre 'infructueux' ne constitue jamais un diagnostic
d'absence d'offres sur le marché ou dans ses lots.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

try:
    from scripts.collecter_notices_pilotes_boamp import adresse, obtenir_octets
    from scripts.relever_issues_echantillon_independant import qualifier
    from scripts.tirer_ensemble_epreuve_infructueux_boamp import (
        VERSION as VERSION_TIRAGE, MOIS, QUOTA, EMPREINTE_BASE,
    )
except ModuleNotFoundError:
    from collecter_notices_pilotes_boamp import adresse, obtenir_octets
    from relever_issues_echantillon_independant import qualifier
    from tirer_ensemble_epreuve_infructueux_boamp import (
        VERSION as VERSION_TIRAGE, MOIS, QUOTA, EMPREINTE_BASE,
    )


class EpreuveInvalide(ValueError):
    """Données d'un relevé non reproductibles."""


def charger(chemin: Path):
    tirage = json.loads(chemin.read_text(encoding="utf-8"))
    lignes = tirage.get("cas")
    if (tirage.get("version") != VERSION_TIRAGE
            or tirage.get("sha256_tirage_original") != EMPREINTE_BASE
            or tirage.get("issues_verifiees_par_lot") is not False
            or tirage.get("ensemble_representatif") is not False
            or not isinstance(lignes, list) or len(lignes) != QUOTA * len(MOIS)):
        raise EpreuveInvalide("Manifeste enrichi incompatible.")
    ids = [x.get("avis") for x in lignes]
    if (len(set(ids)) != len(ids)
            or any(not isinstance(x, str) or not re.fullmatch(r"\d{2}-\d{3,8}", x)
                   for x in ids)):
        raise EpreuveInvalide("Identifiants du prélèvement incorrects.")
    empreinte = hashlib.sha256(json.dumps(
        ids, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()
    if empreinte != tirage.get("sha256_identifiants_ordonnes"):
        raise EpreuveInvalide("Tirage enrichi modifié depuis son engagement.")
    if Counter(x["date_parution"][:7] for x in lignes) != Counter(
            {m: QUOTA for m in MOIS}):
        raise EpreuveInvalide("Stratification temporelle modifiée.")
    return tirage


def relever(chemin_tirage: Path, sortie: Path,
           obtenir=obtenir_octets, instant: datetime | None = None):
    tirage = charger(chemin_tirage)
    maintenant = instant or datetime.now(timezone.utc)
    if maintenant.tzinfo is None or maintenant.utcoffset() is None:
        raise EpreuveInvalide("Horodatage sans fuseau.")
    if sortie.exists() or sortie.is_symlink():
        raise EpreuveInvalide("Sortie déjà existante.")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".epreuve-boamp-", dir=sortie.parent))
    try:
        cas = []
        for item in tirage["cas"]:
            code = item["avis"]
            url = adresse(code)
            brut = obtenir(url)
            resultat = qualifier(brut, code, item["date_parution"])
            nom = code + ".json"
            (temp / nom).write_bytes(brut)
            cas.append({
                "avis": code,
                "date_index": item["date_parution"],
                "source_officielle": url,
                "fichier_reponse": nom,
                "sha256_reponse": hashlib.sha256(brut).hexdigest(),
                "octets": len(brut),
                **resultat,
            })
        compte = Counter(x["statut_releve"] for x in cas)
        issues = Counter(l["qualification_regle_automatique"] for x in cas
                         for l in x["resultats_lots"])
        resultat = {
            "version": "releve-ensemble-epreuve-infructueux-v1",
            "observe_le": maintenant.astimezone(timezone.utc).isoformat(),
            "sha256_fichier_tirage": hashlib.sha256(chemin_tirage.read_bytes()).hexdigest(),
            "sha256_tirage_original_36": EMPREINTE_BASE,
            "nombre_avis": len(cas),
            "statuts": dict(sorted(compte.items())),
            "prequalifications_par_lot": dict(sorted(issues.items())),
            "cas": cas,
            "faux_equivalence_mot_titre_et_absence_offre": False,
            "interpretation_independante_realisee": False,
            "comparaison_avec_les_36_cas_realisee": False,
            "note": (
                "Le mot 'infructueux' dans un titre peut désigner un marché "
                "précédent ou un lot relancé. Une préqualification éventuelle "
                "concerne exclusivement le lot et le résultat codés dans "
                "la notice exacte ; aucune confirmation indépendante acquise."
            ),
        }
        (temp / "rapport.json").write_text(
            json.dumps(resultat, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.rename(temp, sortie)
        return resultat
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tirage", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        resultat = relever(a.tirage, a.sortie)
        print(json.dumps({
            "avis": resultat["nombre_avis"],
            "statuts": resultat["statuts"],
            "lots": resultat["prequalifications_par_lot"],
            "comparaison_independante": False,
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, f"Ensemble enrichi non validé : {exc}\n")


if __name__ == "__main__":
    main()
