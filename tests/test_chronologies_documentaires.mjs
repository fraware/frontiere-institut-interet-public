import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const script = readFileSync(resolve("site_frontiere/chronologies-documentaires.js"), "utf8");
const url = "data:text/javascript;base64," + Buffer.from(script).toString("base64");
const { construireChronologieDocumentaire } = await import(url);
const siret = "21060027600013";
const autre = "18002002600019";
const preuve = "a".repeat(64);
const decp = (ref, date = "2025-06-01") => ({
  source: "decp", id: siret + "/" + ref,
  date, titre: "Marché public " + ref,
  lien: "https://www.data.gouv.fr/datasets/api-decp/",
  provenance: "institutionnel/decp/sonde_aife_json.json"
});
const boamp = (id = "25-94670", s = siret, date = "2025-08-26") => ({
  avis_boamp: id, acheteur_siret: s, date_parution: date,
  identites_marches_decp_dans_archives: 5,
  preuve_boamp_sha256: preuve, preuve_administrative_sha256: preuve
});

test("ordonner sans confondre les dates ni identifier un contrat commun", () => {
  const chronologie = construireChronologieDocumentaire(siret, [
    decp("M-1", "2025-08-26"), decp("M-2", "2025-07-01"), decp("M-3", "2026-01-02")
  ], [boamp(), boamp("26-62030", autre, "2026-06-25")]);
  assert.equal(chronologie.version, "frontiere-chronologie-documentaire-v1");
  assert.deepEqual(chronologie.evenements.map(x => x.cle), [
    "decp:" + siret + "/M-3", "boamp:25-94670",
    "decp:" + siret + "/M-1", "decp:" + siret + "/M-2"
  ]);
  assert.deepEqual(chronologie.decomptes,
    { documents_decp_index: 3, avis_boamp_etude: 1 });
  assert.equal(chronologie.evenements.find(x => x.source === "boamp").nature_date,
    "parution_avis_boamp");
  assert.equal(chronologie.evenements.find(x => x.source === "decp").nature_date,
    "date_documentaire_decp");
  assert.ok(chronologie.evenements.every(x =>
    x.identite_contrat_boamp_demonstree === false && x.lien_projet_demonstre === false));
  assert.match(chronologie.limite_interpretation, /ne démontre ni lien contractuel/);
});

test("absence de documents n'autorise pas d'inférence sur l'activité", () => {
  const r = construireChronologieDocumentaire("00000000000000", [], [boamp()]);
  assert.equal(r.evenements.length, 0);
  assert.deepEqual(r.decomptes, { documents_decp_index: 0, avis_boamp_etude: 0 });
});

test("un avis BOAMP sans marché présent dans l'index conserve son statut historique", () => {
  const r = construireChronologieDocumentaire(siret, [], [boamp()]);
  assert.equal(r.evenements.length, 1);
  assert.equal(r.decomptes.documents_decp_index, 0);
  assert.equal(r.evenements[0].identites_decp_historiques, 5);
  assert.equal(r.evenements[0].identite_contrat_boamp_demonstree, false);
});

test("refuser une égalité par nom, les dates impossibles et les doublons", () => {
  const mutations = [
    [decp("M-1"), decp("M-1")],
    [{ ...decp("M-1"), id: autre + "/M-1" }],
    [{ ...decp("M-1"), source: "boamp" }],
    [{ ...decp("M-1"), date: "2026-02-30" }],
    [{ ...decp("M-1"), titre: "" }],
    [{ ...decp("M-1"), provenance: "institutionnel/../prive.json" }]
  ];
  for (const lignes of mutations) {
    assert.throws(() => construireChronologieDocumentaire(siret, lignes, []),
      /Chronologie documentaire/, "Mutation DECP non rejetée");
  }
  for (const candidat of [
    { ...boamp(), date_parution: "2025-13-05" },
    { ...boamp(), preuve_boamp_sha256: "absente" },
    { ...boamp(), avis_boamp: "inconnu" },
    { ...boamp(), identites_marches_decp_dans_archives: 0 }
  ]) {
    assert.throws(() => construireChronologieDocumentaire(siret, [], [candidat]),
      /Chronologie documentaire/, "Avis BOAMP non contrôlé");
  }
  assert.throws(() => construireChronologieDocumentaire(siret, [], [boamp(), boamp()]),
    /dupliqué/);
  assert.throws(() => construireChronologieDocumentaire("<script>", [], []),
    /SIRET non conforme/);
});
