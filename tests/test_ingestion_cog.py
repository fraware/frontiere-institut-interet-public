import csv
import importlib.util
import io
import json
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_SCRIPT = RACINE / "scripts" / "ingerer_cog.py"

spec = importlib.util.spec_from_file_location("ingerer_cog", CHEMIN_SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def csv_bytes(champs, lignes):
    tampon = io.StringIO(newline="")
    writer = csv.DictWriter(tampon, fieldnames=champs)
    writer.writeheader()
    writer.writerows(lignes)
    return tampon.getvalue().encode("utf-8")


def archive_cog(path: Path, *, unsafe=False, duplicate_commune=False):
    tables = {
        "v_region_2026.csv": (
            ["REG", "CHEFLIEU", "TNCC", "NCC", "NCCENR", "LIBELLE"],
            [{"REG": "11", "CHEFLIEU": "75056", "TNCC": "0", "NCC": "ILE DE FRANCE", "NCCENR": "Île-de-France", "LIBELLE": "Île-de-France"}],
        ),
        "v_departement_2026.csv": (
            ["DEP", "REG", "CHEFLIEU", "TNCC", "NCC", "NCCENR", "LIBELLE"],
            [{"DEP": "75", "REG": "11", "CHEFLIEU": "75056", "TNCC": "0", "NCC": "PARIS", "NCCENR": "Paris", "LIBELLE": "Paris"}],
        ),
        "v_arrondissement_2026.csv": (
            ["ARR", "DEP", "REG", "CHEFLIEU", "TNCC", "NCC", "NCCENR", "LIBELLE"],
            [{"ARR": "751", "DEP": "75", "REG": "11", "CHEFLIEU": "75056", "TNCC": "0", "NCC": "PARIS", "NCCENR": "Paris", "LIBELLE": "Paris"}],
        ),
        "v_canton_2026.csv": (
            ["CAN", "DEP", "REG", "COMPCT", "BURCENTRAL", "TNCC", "NCC", "NCCENR", "LIBELLE", "TYPECT"],
            [{"CAN": "7599", "DEP": "75", "REG": "11", "COMPCT": "2", "BURCENTRAL": "75056", "TNCC": "0", "NCC": "PARIS", "NCCENR": "Paris", "LIBELLE": "Paris", "TYPECT": "9"}],
        ),
        "v_ctcd_2026.csv": (
            ["CTCD", "REG", "CHEFLIEU", "TNCC", "NCC", "NCCENR", "LIBELLE"],
            [{"CTCD": "75D", "REG": "11", "CHEFLIEU": "75056", "TNCC": "0", "NCC": "PARIS", "NCCENR": "Paris", "LIBELLE": "Département de Paris"}],
        ),
        "v_commune_2026.csv": (
            ["TYPECOM", "COM", "REG", "DEP", "CTCD", "ARR", "TNCC", "NCC", "NCCENR", "LIBELLE", "CAN", "COMPARENT"],
            [
                {"TYPECOM": "COM", "COM": "75056", "REG": "11", "DEP": "75", "CTCD": "75D", "ARR": "751", "TNCC": "0", "NCC": "PARIS", "NCCENR": "Paris", "LIBELLE": "Paris", "CAN": "7599", "COMPARENT": ""},
                {"TYPECOM": "ARM", "COM": "75101", "REG": "11", "DEP": "75", "CTCD": "75D", "ARR": "751", "TNCC": "0", "NCC": "PARIS 1ER ARRONDISSEMENT", "NCCENR": "Paris 1er Arrondissement", "LIBELLE": "Paris 1er Arrondissement", "CAN": "7599", "COMPARENT": "75056"},
            ] + ([{"TYPECOM": "COM", "COM": "75056", "REG": "11", "DEP": "75", "CTCD": "75D", "ARR": "751", "TNCC": "0", "NCC": "PARIS BIS", "NCCENR": "Paris bis", "LIBELLE": "Paris bis", "CAN": "7599", "COMPARENT": ""}] if duplicate_commune else []),
        ),
        "v_comer_2026.csv": (
            ["COMER", "TNCC", "NCC", "NCCENR", "LIBELLE"],
            [{"COMER": "987", "TNCC": "0", "NCC": "POLYNESIE FRANCAISE", "NCCENR": "Polynésie française", "LIBELLE": "Polynésie française"}],
        ),
        "v_commune_comer_2026.csv": (
            ["COM_COMER", "TNCC", "NCC", "NCCENR", "LIBELLE", "NATURE_ZONAGE", "COMER", "LIBELLE_COMER"],
            [{"COM_COMER": "98735", "TNCC": "0", "NCC": "PAPEETE", "NCCENR": "Papeete", "LIBELLE": "Papeete", "NATURE_ZONAGE": "COM", "COMER": "987", "LIBELLE_COMER": "Polynésie française"}],
        ),
        # Fichier historique volontairement présent : il ne doit pas être confondu avec le fichier courant.
        "v_commune_1943_2026.csv": (
            ["TYPECOM", "COM", "TNCC", "NCC", "NCCENR", "LIBELLE", "DATE_DEBUT", "DATE_FIN"],
            [
                {"TYPECOM": "COM", "COM": "75056", "TNCC": "0", "NCC": "PARIS", "NCCENR": "Paris", "LIBELLE": "Paris", "DATE_DEBUT": "1943-01-01", "DATE_FIN": ""},
                {"TYPECOM": "COMD", "COM": "75057", "TNCC": "0", "NCC": "PARIS ANCIENNE", "NCCENR": "Paris ancienne", "LIBELLE": "Paris ancienne", "DATE_DEBUT": "2017-01-01", "DATE_FIN": "2026-01-01"},
            ],
        ),
        "v_mvt_commune_2026.csv": (
            ["MOD", "DATE_EFF", "TYPECOM_AV", "COM_AV", "TNCC_AV", "NCC_AV", "NCCENR_AV", "LIBELLE_AV", "TYPECOM_AP", "COM_AP", "TNCC_AP", "NCC_AP", "NCCENR_AP", "LIBELLE_AP"],
            [
                {"MOD": "35", "DATE_EFF": "2026-01-01", "TYPECOM_AV": "COMD", "COM_AV": "75057", "TNCC_AV": "0", "NCC_AV": "PARIS ANCIENNE", "NCCENR_AV": "Paris ancienne", "LIBELLE_AV": "Paris ancienne", "TYPECOM_AP": "COM", "COM_AP": "75056", "TNCC_AP": "0", "NCC_AP": "PARIS", "NCCENR_AP": "Paris", "LIBELLE_AP": "Paris"}
            ],
        ),
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for nom, (champs, lignes) in tables.items():
            zf.writestr(nom, csv_bytes(champs, lignes))
        if unsafe:
            zf.writestr("../evil.csv", b"A,B\n1,2\n")


def preparer_sorties(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "RACINE", tmp_path)
    monkeypatch.setattr(module, "DOSSIER_TERRITOIRES", tmp_path / "institutionnel/territoires/cog")
    monkeypatch.setattr(module, "DOSSIER_RELATIONS", tmp_path / "institutionnel/relations/territoriales/cog")
    monkeypatch.setattr(module, "MANIFESTE", tmp_path / "institutionnel/instantanes/cog_manifest.json")
    monkeypatch.setattr(module, "MANIFESTE_ANNUAIRE", tmp_path / "institutionnel/instantanes/annuaire_local_manifest.json")
    monkeypatch.setattr(module, "STATISTIQUES", tmp_path / "institutionnel/statistiques_cog.json")
    monkeypatch.setattr(module, "ANOMALIES", tmp_path / "institutionnel/anomalies_cog.json")
    monkeypatch.setattr(module, "RESOLUTION_ANNUAIRE", tmp_path / "institutionnel/resolution_annuaire_cog.json")
    monkeypatch.setattr(module, "DOSSIER_ANNUAIRE", tmp_path / "institutionnel/entites/locales")
    module.STATISTIQUES.parent.mkdir(parents=True, exist_ok=True)
    module.MANIFESTE_ANNUAIRE.parent.mkdir(parents=True, exist_ok=True)
    module.MANIFESTE_ANNUAIRE.write_text(json.dumps({
        "sha256_semantique_export": "annuaire-test",
        "version_transformation": "2.2",
        "nombre_services_locaux": 1,
    }), encoding="utf-8")


def test_archive_synthetique_produit_territoires_relations_et_resolution(tmp_path, monkeypatch):
    preparer_sorties(tmp_path, monkeypatch)
    archive = tmp_path / "cog.zip"
    archive_cog(archive)
    module.DOSSIER_ANNUAIRE.mkdir(parents=True, exist_ok=True)
    (module.DOSSIER_ANNUAIRE / "annuaire_local_000.jsonl").write_text(
        json.dumps({"id": "FRONTIERE-INST-DILA-LOCAL-X", "territoires": ["75056", "98735"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    resultat = module.executer(archive, observe_le="2026-10-06T12:00:00+00:00")

    assert resultat["etat"] == "actualise"
    assert resultat["stats"]["nombre_territoires"] == 8
    assert resultat["stats"]["nombre_relations"] == 19
    assert resultat["stats"]["anomalies_relations"] == 0
    assert resultat["stats"]["types_territoires"]["COM"] == 1
    assert resultat["stats"]["types_territoires"]["ARM"] == 1
    assert "CTCD" not in resultat["stats"]["types_territoires"]
    assert resultat["stats"]["collectivites_competence_departementale_source"] == 1
    assert resultat["stats"]["resolution_annuaire"]["references_codes_insee"] == 2
    assert resultat["stats"]["resolution_annuaire"]["resolues"] == 2
    assert resultat["stats"]["resolution_annuaire"]["absentes"] == 0

    territoires = []
    for p in resultat["manifest"]["partitions_territoires"]:
        chemin = tmp_path / p["fichier"]
        territoires.extend(json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l)
    paris = next(t for t in territoires if t["id"] == "FRONTIERE-TERR-COG-COM-75056")
    assert paris["source_insee"]["NCCENR"] == "Paris"
    assert paris["reference_le"] == "2026-01-01"
    assert paris["provenance"][0]["source_id"] == "insee_cog"


def test_decouverte_classe_les_tables_historiques_sans_les_canonicaliser(tmp_path):
    archive = tmp_path / "cog.zip"
    archive_cog(archive)
    with zipfile.ZipFile(archive) as zf:
        classes, inventaire = module.decouvrir_fichiers(zf)
    assert set(classes) == module.FAMILLES_REQUISES
    historique = next(x for x in inventaire if x["nom"] == "v_commune_1943_2026.csv")
    evenements = next(x for x in inventaire if x["nom"] == "v_mvt_commune_2026.csv")
    assert historique["classe_detectee"] == "communes_historiques"
    assert evenements["classe_detectee"] == "evenements_communes"


def test_refuse_traversee_de_repertoire(tmp_path):
    archive = tmp_path / "cog.zip"
    archive_cog(archive, unsafe=True)
    with zipfile.ZipFile(archive) as zf:
        try:
            module.decouvrir_fichiers(zf)
        except module.ErreurCOG as exc:
            assert "Chemin ZIP dangereux" in str(exc)
        else:
            raise AssertionError("archive dangereuse acceptée")


def test_identite_dupliquee_est_refusee(tmp_path, monkeypatch):
    preparer_sorties(tmp_path, monkeypatch)
    archive = tmp_path / "cog.zip"
    archive_cog(archive, duplicate_commune=True)
    try:
        module.executer(archive, observe_le="2026-10-06T12:00:00+00:00")
    except module.ErreurCOG as exc:
        assert "dupliqués" in str(exc)
    else:
        raise AssertionError("doublon COG accepté")


def test_territoire_inchange_conserve_date_observation():
    ligne = {"REG": "11", "CHEFLIEU": "75056", "TNCC": "0", "NCC": "ILE DE FRANCE", "NCCENR": "Île-de-France", "LIBELLE": "Île-de-France"}
    premier = module.creer_territoire("REG", "11", ligne, "2026-10-06T12:00:00+00:00")
    second = module.creer_territoire("REG", "11", ligne, "2026-10-07T12:00:00+00:00", premier)
    assert second["observe_le"] == premier["observe_le"]
    assert second["provenance"][0]["collecte_le"] == premier["provenance"][0]["collecte_le"]


def test_code_commune_ambigu_sans_commune_principale_reste_ambigu(tmp_path, monkeypatch):
    preparer_sorties(tmp_path, monkeypatch)
    module.DOSSIER_ANNUAIRE.mkdir(parents=True, exist_ok=True)
    (module.DOSSIER_ANNUAIRE / "annuaire_local_000.jsonl").write_text(
        json.dumps({"id": "X", "territoires": ["01001"]}) + "\n",
        encoding="utf-8",
    )
    t1 = {"id": "ARM-X", "type_territoire": "ARM", "code": "01001"}
    t2 = {"id": "COMD-X", "type_territoire": "COMD", "code": "01001"}
    rapport = module.resoudre_annuaire_cog([t1, t2], "2026-10-06T12:00:00+00:00")
    assert rapport["resolues"] == 0
    assert rapport["ambigues"] == 1



def test_code_absent_du_cog_courant_est_explique_par_historique_sans_remappage(tmp_path, monkeypatch):
    preparer_sorties(tmp_path, monkeypatch)
    module.DOSSIER_ANNUAIRE.mkdir(parents=True, exist_ok=True)
    (module.DOSSIER_ANNUAIRE / "annuaire_local_000.jsonl").write_text(
        json.dumps({"id": "X", "territoires": ["75057"]}) + "\n",
        encoding="utf-8",
    )
    territoires = [{"id": "FRONTIERE-TERR-COG-COM-75056", "type_territoire": "COM", "code": "75056"}]
    historique = [
        {
            "TYPECOM": "COMD",
            "COM": "75057",
            "NCCENR": "Paris ancienne",
            "DATE_DEBUT": "2017-01-01",
            "DATE_FIN": "2026-01-01",
        }
    ]
    evenements = [
        {
            "MOD": "35",
            "DATE_EFF": "2026-01-01",
            "TYPECOM_AV": "COMD",
            "COM_AV": "75057",
            "NCCENR_AV": "Paris ancienne",
            "TYPECOM_AP": "COM",
            "COM_AP": "75056",
            "NCCENR_AP": "Paris",
        }
    ]

    rapport = module.resoudre_annuaire_cog(
        territoires,
        "2026-10-06T12:00:00+00:00",
        historique_communes=historique,
        evenements_communes=evenements,
    )

    assert rapport["resolues"] == 0
    assert rapport["absentes"] == 1
    assert rapport["absentes_courantes_expliquees_historiquement"] == 1
    assert rapport["absentes_sans_trace_historique"] == 0
    assert rapport["taux_references_expliquees"] == 1.0
    exemple = rapport["exemples_absents_historiques"][0]
    assert exemple["classification"] == "CODE_HISTORIQUE_ABSENT_DU_COG_COURANT"
    assert exemple["historique_cog"]["periode_terminee_avant_ou_a_la_reference"] is True
    assert exemple["historique_cog"]["dernier_evenement_sortant"][0]["code_ap"] == "75056"
    assert "cible_territoire" not in exemple


def test_code_absent_mais_historique_encore_actif_reste_incoherent(tmp_path, monkeypatch):
    preparer_sorties(tmp_path, monkeypatch)
    module.DOSSIER_ANNUAIRE.mkdir(parents=True, exist_ok=True)
    (module.DOSSIER_ANNUAIRE / "annuaire_local_000.jsonl").write_text(
        json.dumps({"id": "X", "territoires": ["75058"]}) + "\n",
        encoding="utf-8",
    )
    rapport = module.resoudre_annuaire_cog(
        [],
        "2026-10-06T12:00:00+00:00",
        historique_communes=[{
            "TYPECOM": "COM",
            "COM": "75058",
            "NCCENR": "Commune active absente",
            "DATE_DEBUT": "2020-01-01",
            "DATE_FIN": "",
        }],
        evenements_communes=[],
    )
    assert rapport["absentes_courantes_expliquees_historiquement"] == 0
    assert rapport["absentes_sans_trace_historique"] == 1
    assert rapport["exemples_absents_inconnus"][0]["classification"] == "CODE_ABSENT_MAIS_HISTORIQUE_NON_TERMINE"

def test_dependance_annuaire_force_recalcul(tmp_path, monkeypatch):
    preparer_sorties(tmp_path, monkeypatch)
    module.MANIFESTE.write_text(json.dumps({
        "sha256_zip": "cog-hash",
        "version_transformation": module.VERSION_TRANSFORMATION,
        "empreinte_dependance_annuaire": module.empreinte_dependance_annuaire(),
    }), encoding="utf-8")
    empreinte = module.empreinte_dependance_annuaire()
    assert module.source_deja_traitee("cog-hash", empreinte) is True
    module.MANIFESTE_ANNUAIRE.write_text(json.dumps({
        "sha256_semantique_export": "annuaire-change",
        "version_transformation": "2.2",
        "nombre_services_locaux": 2,
    }), encoding="utf-8")
    nouvelle = module.empreinte_dependance_annuaire()
    assert nouvelle != empreinte
    assert module.source_deja_traitee("cog-hash", nouvelle) is False