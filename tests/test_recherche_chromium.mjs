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
    // Le bilan est celui des partitions réellement publiées, pas une
    // prétendue mesure de couverture nationale.
    const bilan = await page.locator("#bilan-selection").textContent();
    assert.match(bilan, /BOAMP/);
    assert.match(bilan, /EMPLOIS/);
    assert.match(bilan, /DECP/);
    assert.match(bilan, /Plafond/);
    assert.match(bilan, /Aucun pourcentage de couverture nationale/);

    await page.locator("#source").selectOption("emplois");
    assert.ok(await page.locator("#annee option").count() > 1);
    await page.locator("#termes").fill("");
    await page.locator("#lancer").click();
    await page.waitForFunction(() => /documents examinés/.test(document.querySelector("#etat").textContent));
    assert.ok(await page.locator("article").count() > 0);
    assert.ok((await page.locator("#etat").textContent()).includes("emplois".toUpperCase()));

    // Recherche multiannuelle : le choix libre ne filtre plus par une seule année.
    await page.locator("#annee").selectOption("");
    await page.locator("#lancer").click();
    await page.waitForFunction(() => /toutes années/.test(document.querySelector("#etat").textContent));
    assert.ok(await page.locator("article").count() > 0);

    // Intervalle de publication : une période incohérente est refusée
    // sans afficher des résultats appartenant à la recherche précédente.
    await page.locator("#date-debut").fill("2026-11-01");
    await page.locator("#date-fin").fill("2026-10-01");
    await page.locator("#lancer").click();
    assert.match(await page.locator("#etat").textContent(), /Période incohérente/);
    assert.equal(await page.locator("article").count(), 0);
    await page.locator("#date-debut").fill("");
    await page.locator("#date-fin").fill("");

    // Modifier un champ JSON sans modifier sa longueur : la seule
    // vérification de taille ne doit pas suffire à accepter le document.
    await page.route("**/partitions/part-*.json", async route => {
      const reponse = await route.fetch();
      const brut = await reponse.text();
      const fausseCopie = brut.replace('"titre":', '"titRe":');
      assert.notEqual(fausseCopie, brut);
      assert.equal(Buffer.byteLength(fausseCopie), Buffer.byteLength(brut));
      await route.fulfill({ response: reponse, body: fausseCopie });
    });
    await page.locator("#lancer").click();
    await page.waitForFunction(() =>
      /résultats non publiés/.test(document.querySelector("#etat").textContent));
    assert.equal(await page.locator("article").count(), 0);
    assert.deepEqual(erreurs, []);
  } finally {
    await browser.close();
    await new Promise((resolve, reject) => serveur.close(error => error ? reject(error) : resolve()));
  }
});
