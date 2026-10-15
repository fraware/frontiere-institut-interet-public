"""Proposer des similitudes documentaires BOAMP–TED sans inférer de lien juridique.

Le rapprochement repose uniquement sur les libellés d'acheteur, le texte
des titres et les dates publiées. Les pièces sources et leurs identifiants
sont conservés ; un même nom ne démontre aucune identité institutionnelle.
"""
from __future__ import annotations

from datetime import date
import re
import unicodedata

from app.recherche_nationale import Chemins, rechercher

MOTS_GENERIQUES = frozenset({
    "pour", "avec", "dans", "sur", "aux", "des", "les", "une", "par", "and",
    "the", "for", "de", "du", "au", "la", "le", "un", "et", "en", "a",
    "marches", "marche", "publics", "public", "appel", "avis", "lot",
    "fourniture", "fournitures", "service", "services", "contrat",
    "prestations", "prestation", "accord", "cadre", "framework",
    "contract", "notice", "tender", "procurement",
})


def normaliser(texte: str) -> str:
    canon = unicodedata.normalize("NFKD", texte or "")
    sans_accents = "".join(
        x for x in canon if not unicodedata.combining(x)
    ).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", sans_accents))


def termes(titre: str) -> set[str]:
    return {
        m for m in normaliser(titre).split()
        if len(m) >= 4 and m not in MOTS_GENERIQUES
    }


def mesure(a: dict, b: dict, *, ecart_max_jours: int = 60) -> dict | None:
    """Retourner des indices reproductibles, jamais une probabilité juridique."""
    if a.get("source") != "boamp" or b.get("source") != "ted":
        return None
    acheteur_a = normaliser(a.get("organisme") or "")
    acheteur_b = normaliser(b.get("organisme") or "")
    if len(acheteur_a) < 4 or not acheteur_a or acheteur_a != acheteur_b:
        return None
    aa, bb = termes(a.get("titre") or ""), termes(b.get("titre") or "")
    communs = aa & bb
    if len(communs) < 3:
        return None
    similitude = len(communs) / len(aa | bb)
    if similitude < 0.65:
        return None
    try:
        date_a = date.fromisoformat((a.get("date_publication") or "")[:10])
        date_b = date.fromisoformat((b.get("date_publication") or "")[:10])
    except ValueError:
        return None
    ecart = abs((date_a - date_b).days)
    if ecart > ecart_max_jours:
        return None
    return {
        "qualification": "hypothese_documentaire",
        "identite_institutionnelle_etablie": False,
        "meme_procedure_etablie": False,
        "preuves": {
            "acheteur_libelle_normalise_identique": True,
            "termes_communs": sorted(communs),
            "similarite_jaccard_titres": round(similitude, 4),
            "ecart_dates_publication_jours": ecart,
        },
        "avis_boamp": {
            "identifiant": a["identifiant"],
            "titre": a["titre"],
            "organisme": a["organisme"],
            "date_publication": a["date_publication"],
            "url_source": a["url_document"],
            "empreinte_version": a.get("empreinte_version"),
        },
        "avis_ted": {
            "identifiant": b["identifiant"],
            "titre": b["titre"],
            "organisme": b["organisme"],
            "date_publication": b["date_publication"],
            "url_source": b["url_document"],
            "empreinte_version": b.get("empreinte_version"),
        },
    }


def rapprocher(
    chemins: Chemins, expression: str, *, limite: int = 20,
    exploration_par_source: int = 100,
) -> dict:
    if type(limite) is not int or not 1 <= limite <= 50:
        raise ValueError("Limite de propositions incorrecte.")
    if (type(exploration_par_source) is not int or
            not 1 <= exploration_par_source <= 100):
        raise ValueError("Volume d'exploration incorrect.")
    # Deux requêtes distinctes empêchent un corpus d'évincer l'autre
    # avant le rapprochement. Aucune base source n'est modifiée.
    boamp = rechercher(
        chemins, expression, limite=exploration_par_source,
        sources=("boamp",),
    )
    ted = rechercher(
        chemins, expression, limite=exploration_par_source,
        sources=("ted",),
    )
    resultats = []
    for a in boamp["resultats"]:
        for b in ted["resultats"]:
            candidat = mesure(a, b)
            if candidat is not None:
                resultats.append(candidat)
    resultats.sort(
        key=lambda x: (
            -x["preuves"]["similarite_jaccard_titres"],
            x["preuves"]["ecart_dates_publication_jours"],
            x["avis_boamp"]["identifiant"],
            x["avis_ted"]["identifiant"],
        )
    )
    return {
        "expression": expression.strip(),
        "qualification": "hypotheses_uniquement",
        "liens_contractuels_etablis": 0,
        "resultats": resultats[:limite],
        "propositions_identifiees": len(resultats),
        "propositions_retournees": min(len(resultats), limite),
        "troncature": len(resultats) > limite,
        "documents_examines": {
            "boamp": len(boamp["resultats"]),
            "ted": len(ted["resultats"]),
        },
        "sources": {
            "boamp": boamp["sources"]["boamp"],
            "ted": ted["sources"]["ted"],
        },
        "precision": (
            "Un acheteur nommé à l'identique, des titres semblables et "
            "des dates proches suggèrent un examen des actes originaux. "
            "Aucun identifiant de procédure ni lien juridique commun "
            "n'est démontré par ces critères."
        ),
    }
