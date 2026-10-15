import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const texte = readFileSync(resolve("site_frontiere/acheteurs-decp.js"), "utf8");
const adresse = "data:text/javascript;base64," + Buffer.from(texte).toString("base64");
const { siretAdmissible, siretAcheteur, appartientAuMemeAcheteur, ordreChronologique } =
  await import(adresse);

const siret = "21590271900016";
const marche = (id, date = "2026-10-01") => ({
  source: "decp", id: siret + "/" + id, date,
  organisme: "Acheteur SIRET " + siret
});

test("ne retenir que l'identité déclarée dans la référence DECP", () => {
  assert.equal(siretAcheteur(marche("CONTRAT-1")), siret);
  assert.equal(siretAcheteur({ ...marche("CONTRAT-1"), source: "boamp" }), null);
  assert.equal(siretAcheteur({ source: "emplois", id: "EMP-1", organisme: siret }), null);
  assert.equal(siretAcheteur({ ...marche("CONTRAT-1"), id: "MARCHE" }), null);
  assert.equal(siretAcheteur({ ...marche("CONTRAT-1"), id: siret + "/" }), null);
  assert.equal(siretAcheteur({ ...marche("CONTRAT-1"), id: "1234567890123/CONTRAT-1" }), null);
  assert.equal(siretAcheteur({ ...marche("CONTRAT-1"), id: siret + "/" + "x".repeat(101) }), null);
});

test("le filtre est une égalité d'identifiants et non un rapprochement de noms", () => {
  assert.ok(siretAdmissible(siret));
  assert.equal(siretAdmissible(siret + "1"), false);
  assert.equal(siretAdmissible(siret + " "), false);
  assert.equal(siretAdmissible("2159027190001x"), false);
  assert.equal(siretAdmissible("<script>"), false);
  assert.equal(appartientAuMemeAcheteur(marche("CONTRAT-2"), siret), true);
  assert.equal(appartientAuMemeAcheteur({
    source: "decp", id: "99999999999999/CONTRAT-2",
    organisme: "Acheteur SIRET " + siret
  }, siret), false);
  assert.equal(appartientAuMemeAcheteur({
    source: "boamp", id: siret + "/CONTRAT-2"
  }, siret), false);
});

test("les notices d'un même acheteur sont ordonnées par date, sans corrélation de projet", () => {
  const lignes = [marche("M-1", "2025-02-01"), marche("M-2", "2026-03-01"),
    marche("M-0", "2026-03-01")];
  assert.deepEqual(lignes.sort(ordreChronologique).map(d => d.id),
    [siret + "/M-0", siret + "/M-2", siret + "/M-1"]);
});
