import test from "node:test";
import assert from "node:assert/strict";
import { partitionner, bilanSelection } from "../scripts/construire_partitions_statiques.mjs";

function doc(source, annee, i) {
  return {
    source, date: annee + "-08-12", id: source + "/" + annee + "/" + i,
    titre: "Document " + i, organisme: "Établissement public",
    provenance: "institutionnel/archive.json", lien: "https://www.data.gouv.fr/"
  };
}
test("les partitions sont déterministes, datées, bornées et identifiables", () => {
  const docs = [];
  for (let i = 0; i < 1450; i++) docs.push(doc("boamp", "2026", i));
  for (let i = 0; i < 4; i++) docs.push(doc("emplois", "2025", i));
  const a = partitionner(docs);
  assert.equal(a.length, 4);
  assert.deepEqual(a.map(p => p.documents), [700, 700, 50, 4]);
  assert.ok(a.every(p => p.octets <= 1_000_000));
  assert.equal(a[0].nom, "part-boamp-2026-001.json");
  assert.equal(a[2].nom, "part-boamp-2026-003.json");
  assert.equal(a[3].nom, "part-emplois-2025-001.json");
  assert.deepEqual(a.map(p => p.sha256), partitionner(docs.slice().reverse()).map(p => p.sha256));
});
test("les années et sources non conformes sont rejetées", () => {
  assert.throws(() => partitionner([{...doc("ted","2026",0)}]), /invalide/);
  assert.throws(() => partitionner([{...doc("boamp","2026",0), date:"2026"}]), /invalide/);
});

test("bilan de sélection : années, plafonds et unités hétérogènes", () => {
  const boamp = [doc("boamp", "2025", 1), doc("boamp", "2026", 2)];
  const emplois = [doc("emplois", "2026", 1)];
  const decp = [doc("decp", "2024", 1)];
  const extraits = { boamp: { extraits: boamp, total_candidats: 4 },
    emplois: { extraits: emplois, total_candidats: 28 },
    decp: { extraits: decp, total_candidats: 3 } };
  const partitions = partitionner([...boamp, ...emplois, ...decp]);
  const selection = bilanSelection(extraits, partitions,
    { boamp: 2, emplois: 3, decp: 3 });
  assert.equal(selection.couverture_nationale_etablie, false);
  assert.equal(selection.pourcentage_couverture_calculable, false);
  assert.deepEqual(selection.sources.map(s => s.documents_indexes), [2, 1, 1]);
  assert.deepEqual(selection.sources.map(s => s.plafond_atteint), [true, false, false]);
  assert.deepEqual(selection.sources[0].annees_indexees, [
    { annee: "2025", documents: 1 }, { annee: "2026", documents: 1 }
  ]);
  assert.equal(selection.sources[1].enregistrements_sources_parcourus, 28);
  assert.match(selection.sources[1].unite_enregistrements_sources, /variantes/);
  assert.equal("taux_couverture" in selection.sources[0], false);
});
test("bilan de sélection : refuser des totaux et partitions incohérents", () => {
  const d = doc("boamp", "2026", 1);
  const extraits = { boamp: { extraits: [d], total_candidats: 1 },
    emplois: { extraits: [], total_candidats: 0 },
    decp: { extraits: [], total_candidats: 0 } };
  const limites = { boamp: 2, emplois: 2, decp: 2 };
  assert.throws(() => bilanSelection(extraits, [], limites), /Décompte incohérent/);
  assert.throws(() => bilanSelection(extraits, partitionner([d]), { ...limites, boamp: 0 }),
    /Entrée source invalide/);
  assert.throws(() => bilanSelection(extraits, [
    { source: "boamp", annee: "2026", documents: -1 }
  ], limites), /Partition incompatible/);
});
