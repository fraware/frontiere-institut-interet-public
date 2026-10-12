"""Enrichir un échantillon BOAMP indépendant par les résultats primaires publiés.

Les observations eForms par lot ne constituent PAS des étiquettes de
référence établies en aveugle ; une seconde validation indépendante est nécessaire.
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
    from scripts.reconstituer_chronologies_pilotes_boamp import analyser_attribution
    from scripts.qualifier_attributions_autres_formats_boamp import qualification_hors_eforms
    from scripts.tirer_jeu_independant_boamp import VERSION as VERSION_TIRAGE, MOIS, QUOTA, EXCLUS
except ModuleNotFoundError:
    from collecter_notices_pilotes_boamp import adresse, obtenir_octets
    from reconstituer_chronologies_pilotes_boamp import analyser_attribution
    from qualifier_attributions_autres_formats_boamp import qualification_hors_eforms
    from tirer_jeu_independant_boamp import VERSION as VERSION_TIRAGE, MOIS, QUOTA, EXCLUS

VERSION = "releve-issues-boamp-independant-v2"


class ReleveInvalide(ValueError):
    """Identité, contenu ou enregistrement non vérifiables."""


def charger_tirage(chemin: Path):
    tirage = json.loads(chemin.read_text(encoding="utf-8"))
    if (tirage.get("version") != VERSION_TIRAGE
            or tirage.get("nombre_cas") != QUOTA * len(MOIS)
            or tirage.get("etiquettes_officielles_verifiees") is not False
            or tirage.get("comparaison_de_methodes_effectuee") is not False):
        raise ReleveInvalide("Tirage indépendant ou indicateurs non conformes.")
    cas = tirage.get("cas")
    if not isinstance(cas, list) or len(cas) != QUOTA * len(MOIS):
        raise ReleveInvalide("Inventaire de tirage incompatible.")
    attendus = [x.get("avis") for x in cas]
    if (len(set(attendus)) != len(attendus) or set(attendus) & EXCLUS
            or any(not isinstance(x, str) or not re.fullmatch(r"\d{2}-\d{3,8}", x)
                   for x in attendus)):
        raise ReleveInvalide("Avis dupliqué ou appartenant aux pilotes.")
    empreinte = hashlib.sha256(json.dumps(
        attendus, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()
    if empreinte != tirage.get("sha256_identifiants_ordonnes"):
        raise ReleveInvalide("Empreinte du tirage non reproductible.")
    mois = Counter(x["date_parution"][:7] for x in cas)
    if mois != Counter({m: QUOTA for m in MOIS}):
        raise ReleveInvalide("Quotas de dates modifiés depuis le tirage.")
    return tirage


def qualifier(brut: bytes, identifiant: str, date_attendue: str):
    if not isinstance(brut, bytes) or not brut or len(brut) > 5_000_000:
        raise ReleveInvalide("Corps de réponse HTTP vide ou trop volumineux.")
    try:
        envelope = json.loads(brut)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleveInvalide("Réponse BOAMP non JSON.") from exc
    if not isinstance(envelope, dict):
        raise ReleveInvalide("Enveloppe BOAMP non structurée.")
    n, items = envelope.get("total_count"), envelope.get("results")
    if type(n) is not int or n not in (0, 1) or not isinstance(items, list) or len(items) != n:
        raise ReleveInvalide("Réponse BOAMP dupliquée ou contradictoire.")
    if n == 0:
        return {"statut_releve": "non_retrouve_lors_du_releve", "nature": None,
                "resultats_lots": [], "erreur_extracteur": None}
    notice = items[0]
    if not isinstance(notice, dict) or notice.get("idweb") != identifiant:
        raise ReleveInvalide("Avis officiel avec identifiant contradictoire.")
    if notice.get("dateparution") != date_attendue:
        return {"statut_releve": "date_officielle_divergente", "nature": notice.get("nature"),
                "date_officielle": notice.get("dateparution"),
                "date_attendue_index": date_attendue,
                "resultats_lots": [], "erreur_extracteur": None}
    if notice.get("nature") != "ATTRIBUTION":
        return {
            "statut_releve": "avis_observe_sans_resultat_attribution",
            "nature": notice.get("nature"), "resultats_lots": [],
            "erreur_extracteur": None,
        }
    try:
        formulaire = json.loads(notice.get("donnees") or "null")
        if not isinstance(formulaire, dict):
            raise ValueError("Formulaire absent ou non structuré.")
        if "EFORMS" not in formulaire:
            return qualification_hors_eforms(notice)
        resultat = analyser_attribution(notice)
    except (ValueError, KeyError, TypeError) as exc:
        format_source = (
            next(iter(formulaire), "non_reconnu")
            if isinstance(formulaire, dict) else "non_reconnu"
        )
        return {
            "statut_releve": "resultat_officiel_structure_non_interpretee",
            "nature": "ATTRIBUTION", "resultats_lots": [],
            "observations_hors_lots": [],
            "format_source": format_source.lower(),
            "erreur_extracteur": type(exc).__name__,
        }
    issues = []
    for lot in resultat["resultats_par_lot"]:
        if lot["statut_lot"] == "attribue":
            issue = "attribue_dans_cet_avis"
        elif lot["statut_lot"] == "non_attribue" and lot["motif_officiel"] == "no-rece":
            issue = "absence_offre_explicite"
        elif lot["statut_lot"] == "non_attribue":
            issue = "non_attribue_autre_motif"
        else:
            issue = "non_classe"
        issues.append({
            "lot": lot["identifiant_lot"],
            "qualification_regle_automatique": issue,
            "code_resultat": lot["code_resultat_officiel"],
            "code_motif": lot["motif_officiel"],
            "statistiques": lot["statistiques_soumissions"],
            "origine_resultat": lot["origine_resultat"],
            "confirmation_independante": False,
        })
    return {
        "statut_releve": "attribution_officielle_avec_resultats",
        "nature": "ATTRIBUTION",
        "format_source": "eforms",
        "observations_hors_lots": [],
        "resultats_lots": issues, "erreur_extracteur": None,
    }


def capturer(tirage_path: Path, sortie: Path, obtenir=obtenir_octets,
            maintenant: datetime | None = None):
    tirage = charger_tirage(tirage_path)
    instant = maintenant or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ReleveInvalide("Horodatage sans fuseau.")
    if sortie.exists() or sortie.is_symlink():
        raise ReleveInvalide("Sortie déjà existante.")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".issues-independantes-", dir=sortie.parent))
    try:
        cas = []
        for entree in tirage["cas"]:
            identifiant = entree["avis"]
            url = adresse(identifiant)
            brut = obtenir(url)
            qual = qualifier(brut, identifiant, entree["date_parution"])
            chemin = temp / (identifiant + ".json")
            chemin.write_bytes(brut)
            cas.append({
                "avis": identifiant, "date_parution_index": entree["date_parution"],
                "sha256_reponse_http": hashlib.sha256(brut).hexdigest(),
                "octets_reponse_http": len(brut), "source_officielle": url,
                "fichier_reponse": chemin.name, **qual,
            })
        rapport = {
            "version": VERSION,
            "observe_le": instant.astimezone(timezone.utc).isoformat(),
            "sha256_fichier_tirage": hashlib.sha256(tirage_path.read_bytes()).hexdigest(),
            "sha256_identifiants_ordonnes": tirage["sha256_identifiants_ordonnes"],
            "nombre_cas": len(cas),
            "statuts_releve": dict(sorted(Counter(x["statut_releve"] for x in cas).items())),
            "issues_lots_couvertes": dict(sorted(Counter(
                lot["qualification_regle_automatique"]
                for x in cas for lot in x["resultats_lots"]
            ).items())),
            "observations_hors_lots": sum(
                len(x.get("observations_hors_lots", [])) for x in cas
            ),
            "cas": cas,
            "resultats_independamment_etiquetes": False,
            "comparaison_avec_classifications_concurrentes_effectuee": False,
            "preuve_disponibilite_competences": False,
            "mise_en_garde": (
                "Le relevé contient des préqualifications automatiques provenant "
                "des formulaires officiels. Les avis sans résultat d'attribution "
                "ne sont PAS des marchés sans offre ; les résultats restent "
                "inconnus pour ces avis. La notation indépendante reste à faire."
            ),
        }
        (temp / "rapport.json").write_text(json.dumps(
            rapport, ensure_ascii=False, sort_keys=True, indent=2
        ) + "\n", encoding="utf-8")
        if len(cas) != len(tirage["cas"]):
            raise ReleveInvalide("Nombre d'avis exploités modifié.")
        os.rename(temp, sortie)
        return rapport
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--echantillon", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        rapport = capturer(a.echantillon, a.sortie)
        print(json.dumps({
            "cas": rapport["nombre_cas"],
            "statuts": rapport["statuts_releve"],
            "lots": rapport["issues_lots_couvertes"],
            "etiquettes_independantes": rapport["resultats_independamment_etiquetes"],
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, f"Relevé indépendant non validé : {exc}\n")


if __name__ == "__main__":
    main()
