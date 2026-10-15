/** Test fonctionnel dans Chromium du site public statique, sans accès externe. */
import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { resolve, extname, sep } from "node:path";
import { chromium } from "playwright";

const RACINE = resolve("site_frontiere");
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8" };
async function demarrerServeur() {
  const serveur = createServer(async (req, res) => {
    try {
      const chemin = new URL(req.url, "http://127.0.0.1").pathname;
      const local = resolve(RACINE, "." + (chemin === "/" ? "/index.html" : chemin));
      if (local !== RACINE && !local.startsWith(RACINE + sep)) throw new Error("Traversée");
      const data = await readFile(local);
      res.writeHead(200, { "Content-Type": MIME[extname(local)] || "application/octet-stream", "Cache-Control": "no-store" });
      res.end(data);
    } catch {
      res.writeHead(404); res.end("Introuvable");
    }
  });
  await new Promise(resolve => serveur.listen(0, "127.0.0.1", resolve));
  return { serveur, url: "http://127.0.0.1:" + serveur.address().port };
}

test("navigateur réel : recherche initiale, filtre BOAMP et recherche étendue", { timeout: 90_000 }, async () => {
  const { serveur, url } = await demarrerServeur();
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1100, height: 820 } });
    const erreurs = [];
    page.on("pageerror", e => erreurs.push(String(e)));
    await page.goto(url + "/", { waitUntil: "networkidle" });
    await page.locator("#expression-recherche").waitFor({ state: "visible" });
    await page.waitForFunction(() => !document.querySelector("#expression-recherche").disabled);
    const initial = await page.locator(".resultat").count();
    assert.equal(initial, 12);
    await page.locator("#filtre-source").selectOption("boamp");
    assert.ok(await page.locator(".resultat").count() > 0);
    await page.locator("#expression-recherche").fill("termeintrouvablez987654");
    await page.locator("#formulaire-recherche button[type=submit]").click();
    assert.equal(await page.locator(".resultat").count(), 0);
    assert.match(await page.locator("#etat-recherche").textContent(), /Aucun document/);
    await page.goto(url + "/recherche-etendue.html", { waitUntil: "networkidle" });
    await page.waitForFunction(() => !document.querySelector("#source").disabled);
    await page.locator("#source").selectOption("emplois");
    assert.ok(await page.locator("#annee option").count() > 1);
    await page.locator("#termes").fill("");
    await page.locator("#lancer").click();
    await page.waitForFunction(() => /documents examinés/.test(document.querySelector("#etat").textContent));
    assert.ok(await page.locator("article").count() > 0);
    assert.ok((await page.locator("#etat").textContent()).includes("emplois".toUpperCase()));
    assert.deepEqual(erreurs, []);
  } finally {
    await browser.close();
    await new Promise((resolve, reject) => serveur.close(error => error ? reject(error) : resolve()));
  }
});
