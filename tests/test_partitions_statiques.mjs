import test from "node:test";
import assert from "node:assert/strict";
import { partitionner } from "../scripts/construire_partitions_statiques.mjs";

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
