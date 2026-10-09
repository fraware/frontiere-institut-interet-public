"""Comparer des journées BOAMP déjà archivées avec leur état public actuel.

Les clichés initiaux sont conservés tels quels. Une différence documentée
produit un nouveau cliché adressé par empreinte et un constat d'écart.
Un contrôle réussi sans différence actualise uniquement le compte rendu.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

try:
    from scripts.collecter_historique_boamp import (
        DOSSIER, BOAMP, HistoriqueIncomplet, lire_jour, serialiser,
    )
    from scripts.rechercher_historique_boamp import avis_archive, ArchiveIncoherente
except ModuleNotFoundError:
    from collecter_historique_boamp import (
        DOSSIER, BOAMP, HistoriqueIncomplet, lire_jour, serialiser,
    )
    from rechercher_historique_boamp import avis_archive, ArchiveIncoherente

VERSION = "surveillance-revisions-boamp-v1"
ETAT = "etat_revisions_boamp.json"
DOSSIER_REVISIONS = "revisions_boamp"
JOURS_RECENTS = 2
JOURS_ROTATION = 4
JOUR_RE = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")


class RelectureInvalide(ValueError):
    """Contrôle rétrospectif incomplet ou incohérent."""


def jours_archives(dossier: Path) -> list[Path]:
    racine = dossier / "historique_boamp"
    if not racine.is_dir():
        raise RelectureInvalide("Aucune archive historique présente.")
    fiches = sorted(racine.glob("20??/??/20??-??-??.json"))
    if not fiches:
        raise RelectureInvalide("Aucune journée historique disponible.")
    return fiches


def choisir_jours(fiches: list[Path], dernier_jour: str | None,
                  recents: int = JOURS_RECENTS,
                  rotation: int = JOURS_ROTATION) -> tuple[list[Path], str]:
    """Combiner journées récentes et tour circulaire des dates historiques."""
    if not 1 <= recents <= 5 or not 1 <= rotation <= 10:
        raise RelectureInvalide("Nombre de journées à surveiller incorrect.")
    identifiants = [p.stem for p in fiches]
    if len(identifiants) != len(set(identifiants)):
        raise RelectureInvalide("Journées historiques répétées.")
    if any(not JOUR_RE.fullmatch(x) for x in identifiants):
        raise RelectureInvalide("Jour du dossier invalide.")
    if dernier_jour is not None and (
        not isinstance(dernier_jour, str) or not JOUR_RE.fullmatch(dernier_jour)
    ):
        raise RelectureInvalide("Curseur de relecture incorrect.")
    choix = {p.stem: p for p in fiches[-recents:]}
    debut = bisect_right(identifiants, dernier_jour) if dernier_jour else 0
    index = debut % len(fiches)
    for _ in range(min(rotation, len(fiches))):
        choix[fiches[index].stem] = fiches[index]
        index = (index + 1) % len(fiches)
    derniere = fiches[(index - 1) % len(fiches)].stem
    return [choix[j] for j in sorted(choix)], derniere


def repertoires_revision(dossier: Path, jour: str, empreinte: str) -> tuple[Path, Path]:
    if not JOUR_RE.fullmatch(jour) or not SHA_RE.fullmatch(empreinte):
        raise RelectureInvalide("Nom du fichier de révision incorrect.")
    racine = dossier / DOSSIER_REVISIONS / jour[:4] / jour[5:7] / jour
    return racine / (empreinte + ".jsonl.gz"), racine / (empreinte + ".json")


def conserver_revision(dossier: Path, jour: str, ancien_hash: str,
                       ancienne: list[dict], nouveau: list[dict],
                       observe_le: datetime) -> dict:
    brut, empreinte_source = serialiser(nouveau)
    gzip_hash = hashlib.sha256(brut).hexdigest()
    archive, fiche = repertoires_revision(dossier, jour, empreinte_source)
    origine = {x["id"]: x for x in ancienne}
    courant = {x["id"]: x for x in nouveau}
    ajoutes = sorted(courant.keys() - origine.keys())
    disparus = sorted(origine.keys() - courant.keys())
    modifies = sorted(
        cle for cle in courant.keys() & origine.keys() if courant[cle] != origine[cle]
    )
    constat = {
        "version": VERSION,
        "source": BOAMP,
        "jour_parution": jour,
        "recontrole_le": observe_le.replace(microsecond=0).isoformat(),
        "cliche_initial_sha256_gzip": ancien_hash,
        "cliche_revise_sha256_gzip": gzip_hash,
        "cliche_revise_sha256_decompresse": empreinte_source,
        "cliche_revise_octets": len(brut),
        "archive_relative": archive.relative_to(dossier).as_posix(),
        "nombre_initial": len(ancienne),
        "nombre_revise": len(nouveau),
        "identifiants_ajoutes": ajoutes,
        "identifiants_absents_du_releve": disparus,
        "identifiants_modifies": modifies,
        "interpretation": "Variation entre deux relevés d'avis publics; sa cause n'est pas établie.",
        "completude_historique_etablie": False,
    }
    if archive.exists() or fiche.exists():
        if not archive.is_file() or not fiche.is_file():
            raise RelectureInvalide("Révision existante incomplète.")
        if hashlib.sha256(archive.read_bytes()).hexdigest() != gzip_hash:
            raise RelectureInvalide("Archive de révision existante altérée.")
        ancien_constat = json.loads(fiche.read_text(encoding="utf-8"))
        if (ancien_constat.get("cliche_revise_sha256_gzip") != gzip_hash or
                ancien_constat.get("jour_parution") != jour or
                ancien_constat.get("cliche_initial_sha256_gzip") != ancien_hash):
            raise RelectureInvalide("Provenance de révision existante incohérente.")
        return {"jour": jour, "variation": True, "revision_deja_conservee": True,
                "ajoutes": len(ajoutes), "absents": len(disparus), "modifies": len(modifies)}
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporaire = archive.with_suffix(".gz.temp")
    temporaire.write_bytes(brut)
    temporaire.replace(archive)
    tmp_fiche = fiche.with_suffix(".json.temp")
    tmp_fiche.write_text(
        json.dumps(constat, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_fiche.replace(fiche)
    return {"jour": jour, "variation": True, "revision_deja_conservee": False,
            "ajoutes": len(ajoutes), "absents": len(disparus), "modifies": len(modifies)}


def surveiller(dossier: Path = DOSSIER, obtenir=None, patienter=time.sleep,
               instant: datetime | None = None, recents: int = JOURS_RECENTS,
               rotation: int = JOURS_ROTATION) -> dict:
    maintenant = instant or datetime.now(timezone.utc)
    if maintenant.tzinfo is None:
        raise RelectureInvalide("Horodatage sans fuseau horaire.")
    etat_path = dossier / ETAT
    precedent = json.loads(etat_path.read_text(encoding="utf-8")) if etat_path.is_file() else {}
    fiches, curseur = choisir_jours(
        jours_archives(dossier), precedent.get("dernier_jour_relecture_circulaire"),
        recents, rotation,
    )
    controles, erreurs = [], []
    for fiche in fiches:
        try:
            jour, archive, ancien_hash, anciens = avis_archive(fiche, dossier)
            # La source garde sa politique de requêtes et ses limites habituelles.
            from datetime import date
            jour_date = date.fromisoformat(jour)
            kwargs = {"patienter": patienter}
            if obtenir is not None:
                kwargs["obtenir"] = obtenir
            nouveaux, _total = lire_jour(jour_date, **kwargs)
            anciens_tries = sorted(anciens, key=lambda x: x["id"])
            if anciens_tries == nouveaux:
                controles.append({"jour": jour, "variation": False})
            else:
                controles.append(conserver_revision(
                    dossier, jour, ancien_hash, anciens_tries, nouveaux, maintenant,
                ))
        except (OSError, ValueError, EOFError, json.JSONDecodeError) as erreur:
            erreurs.append({"jour": fiche.stem, "motif": type(erreur).__name__})
            # Un échec de contrôle ne doit pas être considéré comme une absence
            # de changement ; la rotation devra revoir cette journée.
            break
    if erreurs:
        # Ne pas avancer le curseur circulaire : un nouveau lot reprendra la
        # période examinée, y compris toute date en échec.
        curseur = precedent.get("dernier_jour_relecture_circulaire")
    if not controles and erreurs:
        raise RelectureInvalide("Aucune journée réexaminée avec succès.")
    bilan = {
        "version": VERSION,
        "controle_le": maintenant.replace(microsecond=0).isoformat(),
        "jours_controles": len(controles),
        "jours_avec_variation": sum(x["variation"] for x in controles),
        "nouvelles_revisions_archivees": sum(
            x["variation"] and not x.get("revision_deja_conservee", False)
            for x in controles
        ),
        "dernier_jour_relecture_circulaire": curseur,
        "controles": controles,
        "erreurs": erreurs,
        "aucune_variation_ne_prouve_stabilite_totale": True,
        "completude_historique_etablie": False,
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
    parser.add_argument("--recents", type=int, default=JOURS_RECENTS)
    parser.add_argument("--rotation", type=int, default=JOURS_ROTATION)
    args = parser.parse_args()
    try:
        print(json.dumps(surveiller(dossier=args.dossier, recents=args.recents,
                                   rotation=args.rotation), ensure_ascii=False, indent=2))
    except (OSError, ValueError, EOFError) as erreur:
        parser.exit(1, f"Surveillance des révisions interrompue : {type(erreur).__name__}: {erreur}\n")


if __name__ == "__main__":
    main()
