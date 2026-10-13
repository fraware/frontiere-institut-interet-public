"""Confronter les identifiants acheteurs BOAMP à l'API Recherche d'entreprises.

Source gouvernementale en accès public, non exhaustive. Une réponse qui
mentionne seulement une unité légale n'atteste pas l'établissement demandé.
Une réponse négative n'établit pas l'inexistence d'un numéro dans Sirene.
Les octets des réponses et leur empreinte sont conservés sans modification.
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
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

VERSION = "verification-administrative-acheteurs-boamp-v1"
AUDIT_VERSION = "audit-acheteurs-36-boamp-v1"
API = "https://recherche-entreprises.api.gouv.fr/search"
NUMERO = re.compile(r"[0-9]{14}")
EMPREINTE = re.compile(r"[0-9a-f]{64}")
PLAFOND_OCTETS = 5_000_000
PLAFOND_REQUETES = 100


class VerificationInvalide(ValueError):
    """Source, réponse ou preuve incohérente."""


class SansRedirection(HTTPRedirectHandler):
    """Ne jamais suivre un déplacement vers un hôte non étudié."""

    def redirect_request(self, request, fp, code, msg, headers, url):
        raise VerificationInvalide("Redirection du service officiel refusée")


def sha256(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def luhn(numero: str) -> bool:
    """Vérification arithmétique seulement, sans consultation administrative."""
    if not isinstance(numero, str) or NUMERO.fullmatch(numero) is None:
        return False
    chiffres = [int(chiffre) for chiffre in numero]
    total = 0
    for position, nombre in enumerate(reversed(chiffres)):
        if position % 2:
            nombre *= 2
            if nombre > 9:
                nombre -= 9
        total += nombre
    return total % 10 == 0


def charger_identifiants(chemin: Path) -> tuple[dict, list[str], dict]:
    brut = chemin.read_bytes()
    audit = json.loads(brut)
    if (not isinstance(audit, dict)
            or audit.get("version") != AUDIT_VERSION
            or audit.get("verification_registre_sirene_effectuee") is not False
            or audit.get("correspondances_contractuelles_verifiees") != 0
            or audit.get("nombre_avis_tires") != 36
            or audit.get("nombre_avis_distincts") != 36):
        raise VerificationInvalide("Audit BOAMP indépendant non conforme")
    avis = audit.get("avis")
    if not isinstance(avis, list) or len(avis) != 36:
        raise VerificationInvalide("Inventaire BOAMP manquant")
    numeros, occurrences, identifiants_avis = set(), {}, set()
    for fiche in avis:
        if not isinstance(fiche, dict):
            raise VerificationInvalide("Avis mal structuré")
        code = fiche.get("avis")
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{2}-[0-9]{2,8}", code):
            raise VerificationInvalide("Code BOAMP invalide")
        if code in identifiants_avis:
            raise VerificationInvalide("Avis BOAMP répété")
        identifiants_avis.add(code)
        statut = fiche.get("statut_identite")
        numero = fiche.get("identite_acheteur")
        if statut == "identifiant_14_chiffres_sans_schema":
            if not isinstance(numero, str) or NUMERO.fullmatch(numero) is None:
                raise VerificationInvalide("Numéro d'acheteur non qualifié incorrect")
            if not isinstance(fiche.get("champ_identite"), str):
                raise VerificationInvalide("Champ de preuve absent")
            empreinte = fiche.get("sha256_reponse_http")
            if not isinstance(empreinte, str) or EMPREINTE.fullmatch(empreinte) is None:
                raise VerificationInvalide("Empreinte de réponse BOAMP absente")
            numeros.add(numero)
            occurrences.setdefault(numero, []).append({
                "avis": code,
                "sha256_reponse_boamp": empreinte,
                "champ_preuve_boamp": fiche["champ_identite"],
            })
        elif statut == "siret_explicitement_qualifie_dans_avis":
            # Ne pas mélanger deux catégories de preuve dans la cohorte.
            raise VerificationInvalide("Un SIRET explicite n'est pas dans cette cohorte")
        elif numero is not None:
            raise VerificationInvalide("Numéro renseigné malgré identité inconnue")
    n = sum(len(x) for x in occurrences.values())
    if (n != audit.get("identifiants_14_chiffres_non_qualifies")
            or len(numeros) == 0 or len(numeros) > PLAFOND_REQUETES):
        raise VerificationInvalide("Dénominateur de numéros incorrect")
    return audit, sorted(numeros), {
        "sha256_audit_boamp": sha256(brut),
        "observations": n,
        "occurrences_par_numero": occurrences,
    }


def adresse(numero: str) -> str:
    if not isinstance(numero, str) or NUMERO.fullmatch(numero) is None:
        raise VerificationInvalide("Seul un identifiant de quatorze chiffres est autorisé")
    return API + "?" + urlencode({
        "q": numero,
        "per_page": 1,
        "limite_matching_etablissements": 100,
    })


def obtenir_octets(url: str, pause=time.sleep) -> bytes:
    """Une requête par numéro, contrôle des redirections et des limites d'usage."""
    if not url.startswith(API + "?"):
        raise VerificationInvalide("URL de source non autorisée")
    requete = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "FRONTIERE-recherche-institutions/1.0 (audit public documentaire)",
    })
    opener = build_opener(SansRedirection)
    for tentative in range(3):
        try:
            with opener.open(requete, timeout=30) as response:
                if response.status != 200:
                    raise VerificationInvalide("Réponse non conforme à HTTP 200")
                octets = response.read(PLAFOND_OCTETS + 1)
            if not octets or len(octets) > PLAFOND_OCTETS:
                raise VerificationInvalide("Réponse officielle absente ou trop grande")
            return octets
        except HTTPError as exc:
            if exc.code != 429 or tentative == 2:
                raise VerificationInvalide(
                    f"Service administratif indisponible (HTTP {exc.code})"
                ) from exc
            delai = exc.headers.get("Retry-After", "3")
            if not delai.isdigit() or not 1 <= int(delai) <= 30:
                delai = "5"
            pause(int(delai))
        except (URLError, TimeoutError) as exc:
            raise VerificationInvalide("Service administratif injoignable") from exc
    raise VerificationInvalide("Réponse administrative indisponible")


def classer_reponse(numero: str, brut: bytes) -> dict:
    """Exiger le SIRET exact dans un établissement explicitement retourné."""
    if not isinstance(brut, bytes) or len(brut) > PLAFOND_OCTETS:
        raise VerificationInvalide("Corps de réponse trop volumineux")
    try:
        document = json.loads(brut)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationInvalide("Réponse administrative non JSON") from exc
    if not isinstance(document, dict):
        raise VerificationInvalide("Réponse administrative non structurée")
    total = document.get("total_results")
    resultats = document.get("results")
    if (type(total) is not int or total < 0
            or not isinstance(resultats, list)
            or (total == 0 and resultats)
            or (total > 0 and not resultats)):
        raise VerificationInvalide("Pagination ou schéma de résultats incohérent")
    if total == 0:
        return {
            "classe": "non_retrouve_dans_api_non_exhaustive",
            "siret_exact_dans_etablissement": False,
            "chemin_siret": None,
            "siren_unite_legale": None,
            "denomination_publique": None,
            "existence_sirene_exhaustivement_verifiee": False,
            "rattachement_acheteur_avis_confirme": False,
            "identite_contractuelle_confirmee": False,
        }
    entreprises_valides = []
    identifiants_exacts = []
    for idx, unite in enumerate(resultats):
        if not isinstance(unite, dict):
            raise VerificationInvalide("Unité légale non structurée")
        siren = unite.get("siren")
        if not isinstance(siren, str) or not re.fullmatch(r"[0-9]{9}", siren):
            raise VerificationInvalide("SIREN d'unité légale incorrect")
        if siren != numero[:9]:
            continue
        entreprises_valides.append((idx, unite))
        candidats = [
            ("siege", unite.get("siege")),
        ]
        matching = unite.get("matching_etablissements")
        if matching is not None:
            if not isinstance(matching, list):
                raise VerificationInvalide("Établissements correspondants non structurés")
            candidats.extend((f"matching_etablissements/{i}", e)
                             for i, e in enumerate(matching))
        for parcours, etablissement in candidats:
            if etablissement is None:
                continue
            if not isinstance(etablissement, dict):
                raise VerificationInvalide("Établissement non structuré")
            if etablissement.get("siret") == numero:
                identifiants_exacts.append((
                    f"/results/{idx}/{parcours}/siret", unite
                ))
    if len(identifiants_exacts) > 1:
        # Deux emplacements identiques ne constituent pas deux établissements,
        # mais la première occurrence conserve un chemin de preuve sans
        # augmenter artificiellement le nombre de vérifications.
        identifiants_exacts = identifiants_exacts[:1]
    if identifiants_exacts:
        chemin, unite = identifiants_exacts[0]
        statut = "siret_exact_retourne_par_api_publique"
    elif entreprises_valides:
        chemin, unite = None, entreprises_valides[0][1]
        statut = "unite_legale_associee_etablissement_non_atteste"
    else:
        chemin, unite = None, None
        statut = "reponse_sans_identite_exacte"
    denomination = None
    if unite:
        nom = unite.get("nom_complet")
        if isinstance(nom, str):
            denomination = nom[:250]
    return {
        "classe": statut,
        "siret_exact_dans_etablissement": bool(identifiants_exacts),
        "chemin_siret": chemin,
        "siren_unite_legale": unite.get("siren") if unite else None,
        "denomination_publique": denomination,
        "existence_sirene_exhaustivement_verifiee": False,
        "rattachement_acheteur_avis_confirme": False,
        "identite_contractuelle_confirmee": False,
    }


def verifier(audit: Path, sortie: Path, obtenir=obtenir_octets,
             pause=time.sleep, instant: datetime | None = None) -> dict:
    """Conserver toutes les réponses seulement si la collecte complète réussit."""
    source, numeros, origine = charger_identifiants(audit)
    horodatage = instant or datetime.now(timezone.utc)
    if horodatage.tzinfo is None or horodatage.utcoffset() is None:
        raise VerificationInvalide("Horodatage sans fuseau")
    if sortie.exists() or sortie.is_symlink():
        raise VerificationInvalide("Refus d'écraser une vérification antérieure")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    temporaire = Path(tempfile.mkdtemp(prefix=".verification-siret-", dir=sortie.parent))
    try:
        fiches = []
        for i, numero in enumerate(numeros):
            if i:
                pause(1.25)
            url = adresse(numero)
            octets = obtenir(url)
            if not isinstance(octets, bytes):
                raise VerificationInvalide("Réponse non binaire")
            classement = classer_reponse(numero, octets)
            fichier = numero + ".json"
            (temporaire / fichier).write_bytes(octets)
            fiches.append({
                "identifiant_candidat": numero,
                "cle_luhn_valide": luhn(numero),
                "source_api": url,
                "sha256_reponse": sha256(octets),
                "octets_reponse": len(octets),
                "fichier_reponse": fichier,
                "avis_boamp": origine["occurrences_par_numero"][numero],
                **classement,
            })
        classes = Counter(f["classe"] for f in fiches)
        rapport = {
            "version": VERSION,
            "observe_le": horodatage.astimezone(timezone.utc).isoformat(),
            "source_audit_boamp_sha256": origine["sha256_audit_boamp"],
            "nombre_avis_origine": source["nombre_avis_tires"],
            "nombre_occurrences_identifiants": origine["observations"],
            "nombre_identifiants_distincts": len(numeros),
            "nombre_reponses_officielles_archivees": len(fiches),
            "categories": dict(sorted(classes.items())),
            "nombre_numeros_luhn_valides": sum(f["cle_luhn_valide"] for f in fiches),
            "identites_etablissements_mentionnees_explicitement": classes[
                "siret_exact_retourne_par_api_publique"
            ],
            "aucune_preuve_absence_pour_les_non_retrouves": True,
            "rattachements_acheteurs_verifies": 0,
            "contrats_juridiquement_identifies": 0,
            "verification_insee_exhaustive": False,
            "limite": (
                "La recherche publique est non exhaustive. Une unité légale "
                "retournée ne suffit pas à vérifier l'établissement demandé. "
                "L'égalité d'un SIRET dans la réponse n'établit ni le rôle exact "
                "du cocontractant ni l'identité du marché."
            ),
            "identifiants": fiches,
        }
        (temporaire / "rapport.json").write_text(
            json.dumps(rapport, sort_keys=True, ensure_ascii=False,
                       indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        os.replace(temporaire, sortie)
        return rapport
    finally:
        if temporaire.exists():
            shutil.rmtree(temporaire)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-boamp", type=Path, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    try:
        rapport = verifier(args.audit_boamp, args.sortie)
        print(json.dumps({
            "identifiants": rapport["nombre_identifiants_distincts"],
            "categories": rapport["categories"],
            "siret_exacts": rapport["identites_etablissements_mentionnees_explicitement"],
            "contrats_verifies": 0,
        }, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"Vérification administrative refusée : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
