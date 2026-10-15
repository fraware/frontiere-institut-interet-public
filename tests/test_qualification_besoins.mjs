import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const source = readFileSync(resolve("site_frontiere/qualification-besoins.js"), "utf8");
const moduleUrl = "data:text/javascript;base64," + Buffer.from(source).toString("base64");
const { VERSION_QUALIFICATION, TYPES_DOCUMENTAIRES,
  qualifierDocument, bilanQualifications } = await import(moduleUrl);

const origine = {
  boamp: "institutionnel/besoins_publics/annonces_boamp.json",
  emplois: "institutionnel/besoins_publics/offres_postes/lot_00.jsonl",
  decp: "institutionnel/decp/sonde_aife_json.json"
};
function doc(source, id, date = "2026-10-01") {
  return {
    source, id, date, titre: "Observation publique documentée",
    organisme: "Organisme", provenance: origine[source]
  };
}
const exemplaires = [
  doc("boamp", "26-105050"),
  doc("emplois", "OFFRE-123"),
  doc("decp", "21590271900016/MARCHE-1")
];

test("qualifier sans extrapoler les besoins et sans confondre attribution et exécution", () => {
  const codes = [
    "avis_commande_publique_publie",
    "recrutement_public_annonce",
    "marche_public_attribue_declare"
  ];
  assert.deepEqual(exemplaires.map(d => qualifierDocument(d).type), codes);
  assert.deepEqual(exemplaires.map(d => qualifierDocument(d).besoin), [
    "non_etablie", "recherche_de_competences_a_la_publication",
    "besoin_actuel_non_etabli"
  ]);
  for (const d of exemplaires) {
    const qualification = qualifierDocument(d);
    assert.equal(qualification.version, VERSION_QUALIFICATION);
    assert.equal(qualification.etat_actuel, "non_etabli");
    assert.equal(qualification.execution, "non_etablie");
    assert.match(TYPES_DOCUMENTAIRES[d.source].explication, /ne prouve|sans établir/);
  }
});

test("bilan exact, déterministe, sans besoins manquants inventés", () => {
  const lignes = exemplaires.map(d => ({ ...d, qualification: qualifierDocument(d) }));
  const result = bilanQualifications(lignes);
  assert.equal(result.documents_qualifies, 3);
  assert.deepEqual(result.sources.map(s => s.documents), [1, 1, 1]);
  assert.equal(result.besoins_actuels_non_satisfaits_demonstres, 0);
  assert.equal(result.hypotheses_de_besoins, 0);
  assert.equal(result.projets_communs_demonstres, 0);
  assert.equal(result.couverture_nationale_demonstree, false);
  assert.deepEqual(result, bilanQualifications([...lignes].reverse()));
});

test("rejeter les catégories auto-promues, doublons et identifiants trompeurs", () => {
  const lignes = exemplaires.map(d => ({ ...d, qualification: qualifierDocument(d) }));
  assert.throws(() => bilanQualifications([...lignes, lignes[0]]), /dupliquée/);
  assert.throws(() => bilanQualifications([{
    ...lignes[1], qualification: { ...lignes[1].qualification,
      etat_actuel: "besoin_encore_ouvert" }
  }]), /incohérente/);
  assert.throws(() => qualifierDocument({ ...exemplaires[0], source: "decp" }),
    /sans provenance/);
  assert.throws(() => qualifierDocument({ ...exemplaires[2], id: "MARCHE-1" }),
    /SIRET/);
  assert.throws(() => qualifierDocument({ ...exemplaires[1],
    provenance: "institutionnel/decp/sonde_aife_json.json" }), /sans provenance/);
  assert.throws(() => qualifierDocument({ ...exemplaires[0], date: "2026-02-30" }),
    /sans provenance/);
  assert.throws(() => qualifierDocument({ ...exemplaires[0], source: "autre" }),
    /sans provenance/);
  assert.throws(() => bilanQualifications(null), /absents/);
});
