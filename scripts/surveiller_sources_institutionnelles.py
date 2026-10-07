from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RACINE = Path(__file__).resolve().parents[1]
REGISTRE = RACINE / "institutionnel" / "sources_v1.json"
SORTIE_DEFAUT = RACINE / "institutionnel" / "etat_sources.json"
ALERTES_DEFAUT = RACINE / "institutionnel" / "alertes_sources.json"

AGENT = "FRONTIERE-referentiel-institutionnel/1.0"
MAX_LECTURE_PAGE = 512 * 1024

SEUILS_JOURS = {
    "quotidienne": 3,
    "quotidienne_ou_evenementielle": 14,
    "frequente": 21,
    "hebdomadaire": 14,
    "reguliere": 120,
    "annuelle": 400,
    "annuelle_avec_verification_hebdomadaire": 400,
}

CADENCES_SANS_FRAICHEUR = {
    "evenementielle",
    "a_chaque_remaniement",
}


def maintenant() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def requete(url: str, *, limite: int | None = None) -> tuple[bytes, dict[str, str], int]:
    entetes = {"User-Agent": AGENT, "Accept": "*/*"}
    if limite:
        entetes["Range"] = f"bytes=0-{limite - 1}"
    req = Request(url, headers=entetes)
    with urlopen(req, timeout=35) as reponse:
        contenu = reponse.read(limite or -1)
        headers = {k.lower(): v for k, v in reponse.headers.items()}
        return contenu, headers, reponse.status


def empreinte(objet: object) -> str:
    brut = json.dumps(objet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def extraire_ressources(data: dict) -> list[dict]:
    ressources = []
    for ressource in data.get("resources", []):
        extras = ressource.get("extras") or {}
        checksum = ressource.get("checksum") or extras.get("analysis:checksum")
        ressources.append(
            {
                "id": ressource.get("id"),
                "titre": ressource.get("title"),
                "format": ressource.get("format"),
                "derniere_modification": ressource.get("last_modified"),
                "url": ressource.get("url"),
                "url_stable": ressource.get("latest"),
                "empreinte_source": checksum,
                "taille": ressource.get("filesize") or extras.get("analysis:content-length"),
                "disponible": extras.get("check:available"),
            }
        )
    ressources.sort(key=lambda item: (item.get("id") or "", item.get("titre") or ""))
    return ressources


def observer_data_gouv(source: dict) -> dict:
    contenu, headers, statut = requete(source["metadata_url"])
    data = json.loads(contenu.decode("utf-8"))
    ressources = extraire_ressources(data)
    noyau = {
        "id_jeu": data.get("id"),
        "titre": data.get("title"),
        "derniere_mise_a_jour": data.get("last_update"),
        "derniere_modification": data.get("last_modified"),
        "licence": data.get("license"),
        "ressources": ressources,
    }
    return {
        "etat_http": statut,
        "type_observation": "metadonnees_data_gouv",
        **noyau,
        "empreinte": empreinte(noyau),
        "etag": headers.get("etag"),
    }


def observer_page(source: dict) -> dict:
    url = source["page_url"]
    contenu, headers, statut = requete(url, limite=MAX_LECTURE_PAGE)
    noyau = {
        "url": url,
        "etat_http": statut,
        "derniere_modification_http": headers.get("last-modified"),
        "etag": headers.get("etag"),
        "taille_http": headers.get("content-length"),
        "empreinte_partielle": hashlib.sha256(contenu).hexdigest(),
    }
    return {
        "type_observation": "page_officielle",
        **noyau,
        "empreinte": empreinte(noyau),
    }


def analyser_date(valeur: str | None) -> datetime | None:
    if not valeur:
        return None
    try:
        return datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError:
        return None


def fraicheur(source: dict, observation: dict, date_observation: datetime) -> dict:
    cadence = source.get("cadence_attendue")
    if cadence in CADENCES_SANS_FRAICHEUR:
        return {
            "statut": "NON_APPLICABLE",
            "seuil_jours": None,
            "age_jours": None,
        }

    seuil = SEUILS_JOURS.get(cadence)
    date_source = analyser_date(observation.get("derniere_mise_a_jour"))
    if date_source is None:
        date_source = analyser_date(observation.get("derniere_modification"))

    if seuil is None or date_source is None:
        return {
            "statut": "INDETERMINE",
            "seuil_jours": seuil,
            "age_jours": None,
        }

    age = max(0, (date_observation - date_source).days)
    return {
        "statut": "FRAIS" if age <= seuil else "A_REVOIR",
        "seuil_jours": seuil,
        "age_jours": age,
    }


def charger_json(chemin: Path, defaut: object) -> object:
    if not chemin.exists():
        return defaut
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return defaut


def construire_alertes(ancien: dict, nouveau: dict) -> list[dict]:
    anciens = {item["source_id"]: item for item in ancien.get("sources", [])}
    alertes = []

    for actuel in nouveau.get("sources", []):
        source_id = actuel["source_id"]
        precedent = anciens.get(source_id)

        if actuel.get("erreur"):
            alertes.append(
                {
                    "source_id": source_id,
                    "type": "SOURCE_INDISPONIBLE",
                    "criticite": actuel.get("criticite"),
                    "detail": actuel["erreur"],
                }
            )
            continue

        if actuel.get("fraicheur", {}).get("statut") == "A_REVOIR":
            alertes.append(
                {
                    "source_id": source_id,
                    "type": "FRAICHEUR_A_REVOIR",
                    "criticite": actuel.get("criticite"),
                    "detail": actuel.get("fraicheur"),
                }
            )

        if precedent is None:
            continue

        ancienne_empreinte = precedent.get("observation", {}).get("empreinte")
        nouvelle_empreinte = actuel.get("observation", {}).get("empreinte")
        if ancienne_empreinte and nouvelle_empreinte and ancienne_empreinte != nouvelle_empreinte:
            alertes.append(
                {
                    "source_id": source_id,
                    "type": "SOURCE_MODIFIEE",
                    "criticite": actuel.get("criticite"),
                    "ancienne_empreinte": ancienne_empreinte,
                    "nouvelle_empreinte": nouvelle_empreinte,
                }
            )

    return alertes


def surveiller(registre: Path, sortie: Path, alertes_sortie: Path) -> tuple[dict, dict]:
    configuration = json.loads(registre.read_text(encoding="utf-8"))
    ancienne = charger_json(sortie, {"sources": []})
    date_observation = maintenant()

    resultats = []
    for source in configuration["sources"]:
        item = {
            "source_id": source["id"],
            "nom": source["nom"],
            "criticite": source["criticite"],
            "cadence_attendue": source["cadence_attendue"],
            "observe_le": iso(date_observation),
        }
        try:
            if source.get("metadata_url"):
                observation = observer_data_gouv(source)
            else:
                observation = observer_page(source)
            item["observation"] = observation
            item["fraicheur"] = fraicheur(source, observation, date_observation)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            item["erreur"] = f"{type(exc).__name__}: {exc}"
            item["fraicheur"] = {"statut": "ERREUR", "seuil_jours": None, "age_jours": None}
        resultats.append(item)

    etat = {
        "version": "1",
        "registre_version": configuration["version"],
        "observe_le": iso(date_observation),
        "nombre_sources": len(resultats),
        "sources": resultats,
    }
    alertes = {
        "version": "1",
        "observe_le": iso(date_observation),
        "alertes": construire_alertes(ancienne if isinstance(ancienne, dict) else {}, etat),
    }

    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(etat, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    alertes_sortie.write_text(json.dumps(alertes, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return etat, alertes


def lister_erreurs_critiques(etat: dict) -> list[str]:
    return [
        source["source_id"]
        for source in etat.get("sources", [])
        if source.get("erreur") and source.get("criticite") == "critique"
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Surveille les sources du référentiel institutionnel FRONTIÈRE.")
    parser.add_argument("--registre", type=Path, default=REGISTRE)
    parser.add_argument("--sortie", type=Path, default=SORTIE_DEFAUT)
    parser.add_argument("--alertes", type=Path, default=ALERTES_DEFAUT)
    args = parser.parse_args()

    etat, alertes = surveiller(args.registre, args.sortie, args.alertes)
    erreurs_critiques = lister_erreurs_critiques(etat)

    print(
        json.dumps(
            {
                "sources": etat["nombre_sources"],
                "alertes": len(alertes["alertes"]),
                "erreurs_critiques": erreurs_critiques,
            },
            ensure_ascii=False,
        )
    )

    if erreurs_critiques:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
