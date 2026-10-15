/* Vérifier la recherche documentaire dans le navigateur, sans dépendance. */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const moduleCode = readFileSync(resolve("site_frontiere/recherche.js"), "utf8");
const moduleUrl = "data:text/javascript;base64," + Buffer.from(moduleCode).toString("base64");
const { normaliser, correspond, lienSecurise } = await import(moduleUrl);

test("recherche insensible aux accents et termes multiples", () => {
  const document = {
    id: "B-42", source: "boamp",
    titre: "Équipements pour la recherche scientifique",
    organisme: "Université de Lyon", date: "2026-10-15",
    localisation: "Auvergne-Rhône-Alpes", code: "73000000"
  };
  assert.equal(normaliser("  ÉTUDE\n SCIENTIFIQUE "), "etude scientifique");
  assert.equal(correspond(document, ["equipements", "universite"], ""), true);
  assert.equal(correspond(document, ["equipements"], "decp"), false);
  assert.equal(correspond(document, ["equipements"], "boamp"), true);
  assert.equal(correspond(document, ["informatique"], "boamp"), false);
});

test("ne pas construire de lien dangereux à partir de données publiques", () => {
  assert.equal(lienSecurise("javascript:alert(1)"), null);
  assert.equal(lienSecurise("data:text/html,test"), null);
  assert.equal(lienSecurise("http://example.com"), null);
  assert.equal(lienSecurise("https://www.boamp.fr/avis/42"), "https://www.boamp.fr/avis/42");
});

test("formulaire accessible, données servies localement et aucune télémétrie", () => {
  const html = readFileSync("site_frontiere/index.html", "utf8");
  assert.match(html, /id="formulaire-recherche"/);
  assert.match(html, /id="expression-recherche"/);
  assert.match(html, /id="filtre-source"/);
  assert.match(html, /id="resultats-recherche"/);
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /src="\.\/recherche\.js"/);
  assert.match(html, /non exhaustif/i);
  assert.match(moduleCode, /fetch\(FICHIER/);
  assert.match(moduleCode, /textContent/);
  assert.doesNotMatch(moduleCode, /\.innerHTML\s*=/);
  assert.doesNotMatch(moduleCode, /localStorage|sessionStorage|sendBeacon|analytics/);
  assert.match(moduleCode, /credentials: "omit"/);
});
