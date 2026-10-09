"""Construire un historique journalier borné des avis BOAMP officiels.

Chaque journée close est conservée séparément, après vérification complète
des pages déclarées par l'API. Les journaux antérieurs ne sont ni effacés ni
présentés comme une photographie immuable des données à la source.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode

try:
    from scripts.collecter_besoins_publics import (
        BOAMP, CHAMPS_BOAMP, EchecBesoins, notice_boamp, recevoir,
    )
except ModuleNotFoundError:
    from collecter_besoins_publics import (
        BOAMP, CHAMPS_BOAMP, EchecBesoins, notice_boamp, recevoir,
    )

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "institutionnel" / "besoins_publics"
ETAT = DOSSIER / "etat_historique_boamp.json"
ARCHIVE = "historique_boamp"
VERSION = "boamp-historique-journalier-v1"
PLANCHER = date(2018, 1, 1)
PAGES_MAX = 50
TAILLE_PAGE = 100
JOURS_PAR_EXECUTION = 24
PAUSE_SECONDES = 0.25
DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class HistoriqueIncomplet(ValueError):
    """Une journée n'a pas pu être collectée complètement."""


def adresse_jour(jour: date, page: int, taille: int = TAILLE_PAGE) -> str:
    if type(page) is not int or not 0 <= page < PAGES_MAX:
        raise HistoriqueIncomplet("Page BOAMP hors limites.")
    if type(taille) is not int or not 1 <= taille <= TAILLE_PAGE:
        raise HistoriqueIncomplet("Taille de page BOAMP hors limites.")
    suivant = jour + timedelta(days=1)
    return BOAMP + "?" + urlencode({
        "where": (
            f'dateparution >= "{jour.isoformat()}" AND '
            f'dateparution < "{suivant.isoformat()}"'
        ),
        "order_by": "idweb asc",
        "select": ",".join(CHAMPS_BOAMP),
        "limit": taille,
        "offset": page * taille,
    })


def lire_jour(jour: date, obtenir=recevoir, patienter=time.sleep,
              pages_max: int = PAGES_MAX, taille: int = TAILLE_PAGE) -> tuple[list[dict], int]:
    """Refuser toute page manquante, tout compte instable et toute date erronée."""
    if not 1 <= pages_max <= PAGES_MAX or not 1 <= taille <= TAILLE_PAGE:
        raise HistoriqueIncomplet("Limites de consultation incorrectes.")
    attendus = None
    notices = {}
    compteur = 0
    for page in range(pages_max):
        try:
            enveloppe = obtenir(adresse_jour(jour, page, taille), BOAMP)
        except (OSError, ValueError, TimeoutError) as erreur:
            raise HistoriqueIncomplet(
                f"Réponse indisponible à la page {page + 1} : {type(erreur).__name__}."
            ) from erreur
        if not isinstance(enveloppe, dict):
            raise HistoriqueIncomplet("Réponse officielle incorrecte.")
        total = enveloppe.get("total_count")
        lignes = enveloppe.get("results")
        if type(total) is not int or total < 0 or not isinstance(lignes, list):
            raise HistoriqueIncomplet("Total ou liste de résultats BOAMP incorrect.")
        if attendus is None:
            attendus = total
            if attendus > pages_max * taille:
                raise HistoriqueIncomplet(
                    "Journée dépassant le plafond de pagination : fractionnement nécessaire."
                )
        if total != attendus:
            raise HistoriqueIncomplet("Total déclaré modifié pendant la consultation.")
        taille_attendue = min(taille, attendus - compteur)
        if len(lignes) != taille_attendue:
            raise HistoriqueIncomplet("Page absente, dupliquée ou incomplète.")
        for brut in lignes:
            notice = notice_boamp(brut)
            if notice is None:
                raise HistoriqueIncomplet("Annonce sans identifiant exploitable.")
            parution = notice.get("date_parution")
            if not isinstance(parution, str) or parution[:10] != jour.isoformat():
                raise HistoriqueIncomplet("Date de parution hors de la journée demandée.")
            if notice["id"] in notices:
                if notices[notice["id"]] != notice:
                    raise HistoriqueIncomplet("Un identifiant annonce des contenus divergents.")
                raise HistoriqueIncomplet("Pagination BOAMP dupliquée : comptage non certain.")
            notices[notice["id"]] = notice
        compteur += len(lignes)
        if compteur == attendus:
            return [notices[k] for k in sorted(notices)], attendus
        patienter(PAUSE_SECONDES)
    raise HistoriqueIncomplet("Plafond atteint avant réception de toutes les annonces.")


def serialiser(notices: list[dict]) -> tuple[bytes, str]:
    source = "".join(
        json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for x in notices
    ).encode("utf-8")
    # Compression stable : aucune heure de création introduite dans l'archive.
    return gzip.compress(source, compresslevel=9, mtime=0), hashlib.sha256(source).hexdigest()


def chemins_jour(dossier: Path, jour: date) -> tuple[Path, Path]:
    racine = dossier / ARCHIVE / f"{jour.year:04d}" / f"{jour.month:02d}"
    nom = jour.isoformat()
    return racine / f"{nom}.jsonl.gz", racine / f"{nom}.json"


def publier_jour(dossier: Path, jour: date, notices: list[dict],
                 total: int, instant: datetime) -> dict:
    archive, fiche = chemins_jour(dossier, jour)
    archive.parent.mkdir(parents=True, exist_ok=True)
    brut, empreinte_source = serialiser(notices)
    empreinte_archive = hashlib.sha256(brut).hexdigest()
    fiche_donnees = {
        "version": VERSION,
        "source": BOAMP,
        "attribution": "Direction de l'information légale et administrative (DILA), BOAMP",
        "jour_parution": jour.isoformat(),
        "collecte_le": instant.replace(microsecond=0).isoformat(),
        "avis_recus": total,
        "avis_distincts": len(notices),
        "pages_completes": True,
        "exhaustif_pour_la_journee_au_moment_de_la_collecte": True,
        "exhaustif_pour_l_historique_du_boamp": False,
        "archive_relative": str(archive.relative_to(dossier)).replace("\\", "/"),
        "sha256_octets_decompresses": empreinte_source,
        "sha256_archive_gzip": empreinte_archive,
        "octets_archive": len(brut),
    }
    # Ne plus modifier les octets archivés pour un même jour sans opération
    # d'actualisation distincte ; les corrections à la source restent à suivre.
    if archive.exists() or fiche.exists():
        if not archive.is_file() or not fiche.is_file():
            raise HistoriqueIncomplet("Fichier historique préexistant incomplet.")
        ancien = json.loads(fiche.read_text(encoding="utf-8"))
        if ancien.get("sha256_archive_gzip") != hashlib.sha256(archive.read_bytes()).hexdigest():
            raise HistoriqueIncomplet("Archives existantes altérées.")
        if ancien.get("jour_parution") != jour.isoformat():
            raise HistoriqueIncomplet("Date de l'archive préexistante incohérente.")
        return ancien
    tmp = archive.with_suffix(archive.suffix + ".temp")
    tmp.write_bytes(brut)
    tmp.replace(archive)
    tmp_fiche = fiche.with_suffix(".json.temp")
    tmp_fiche.write_text(
        json.dumps(fiche_donnees, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_fiche.replace(fiche)
    return fiche_donnees


def executer(dossier: Path = DOSSIER, instant: datetime | None = None,
             obtenir=recevoir, patienter=time.sleep,
             jours_par_execution: int = JOURS_PAR_EXECUTION,
             plancher: date = PLANCHER) -> dict:
    if not 1 <= jours_par_execution <= 24:
        raise HistoriqueIncomplet("Nombre de journées par exécution incorrect.")
    maintenant = instant or datetime.now(timezone.utc)
    if maintenant.tzinfo is None:
        raise HistoriqueIncomplet("Horodatage sans fuseau horaire.")
    if plancher > maintenant.date():
        raise HistoriqueIncomplet("Le plancher historique est dans le futur.")
    etat_path = dossier / "etat_historique_boamp.json"
    ancien = json.loads(etat_path.read_text(encoding="utf-8")) if etat_path.is_file() else {}
    valeur = ancien.get("jour_suivant_a_relever")
    if valeur is None:
        # La veille courante traite déjà les sept derniers jours.
        curseur = maintenant.date() - timedelta(days=8)
    else:
        if not isinstance(valeur, str) or not DATE_ISO.fullmatch(valeur):
            raise HistoriqueIncomplet("Curseur historique mal formé.")
        curseur = date.fromisoformat(valeur)
    if curseur > maintenant.date() or curseur < plancher - timedelta(days=1):
        raise HistoriqueIncomplet("Curseur historique hors bornes.")
    acheves, erreurs, premier = [], [], curseur
    for _ in range(jours_par_execution):
        if curseur < plancher:
            break
        try:
            notices, total = lire_jour(curseur, obtenir=obtenir, patienter=patienter)
            fiche = publier_jour(dossier, curseur, notices, total, maintenant)
            acheves.append({"jour": curseur.isoformat(), "avis": fiche["avis_distincts"]})
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError) as exc:
            erreurs.append({"jour": curseur.isoformat(), "motif": type(exc).__name__})
            break
        curseur -= timedelta(days=1)
    if not acheves and erreurs:
        raise HistoriqueIncomplet(
            "Aucune journée complètement archivée : état antérieur conservé."
        )
    bilan = {
        "version": VERSION,
        "controle_le": maintenant.replace(microsecond=0).isoformat(),
        "jour_initial_cette_execution": premier.isoformat(),
        "jour_suivant_a_relever": curseur.isoformat() if curseur >= plancher else None,
        "jours_complets_cette_execution": len(acheves),
        "avis_distincts_cette_execution": sum(x["avis"] for x in acheves),
        "jours": acheves,
        "erreurs": erreurs,
        "plancher": plancher.isoformat(),
        "historique_integral_non_etabli": True,
        "modifications_retroactives_non_suivies": True,
    }
    etat_path.parent.mkdir(parents=True, exist_ok=True)
    temp = etat_path.with_suffix(".json.temp")
    temp.write_text(json.dumps(bilan, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")
    temp.replace(etat_path)
    return bilan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dossier", type=Path, default=DOSSIER)
    parser.add_argument("--jours", type=int, default=JOURS_PAR_EXECUTION)
    args = parser.parse_args()
    try:
        print(json.dumps(executer(dossier=args.dossier, jours_par_execution=args.jours),
                         ensure_ascii=False, indent=2))
    except (OSError, ValueError, TimeoutError) as erreur:
        parser.exit(1, f"Rattrapage BOAMP interrompu : {type(erreur).__name__}: {erreur}\n")


if __name__ == "__main__":
    main()
