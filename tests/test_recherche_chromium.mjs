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

test("regroupement DECP : SIRET exact, années multiples et lien partageable", { timeout: 90_000 }, async () => {
  const { serveur, url } = await demarrerServeur();
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1100, height: 820 } });
    const erreurs = [];
    page.on("pageerror", erreur => erreurs.push(String(erreur)));
    await page.goto(url + "/recherche-etendue.html", { waitUntil: "networkidle" });
    await page.waitForFunction(() => !document.querySelector("#source").disabled);
    await page.locator("#source").selectOption("decp");
    await page.locator("#annee").selectOption("");
    await page.locator("#lancer").click();
    await page.waitForFunction(() => /documents examinés/.test(document.querySelector("#etat").textContent));
    const premier = page.locator("article .lien-acheteur").first();
    assert.ok(await premier.count() > 0, "Le corpus réel doit contenir au moins un SIRET DECP indexé");
    const urlDossier = new URL(await premier.getAttribute("href"), page.url());
    const siret = urlDossier.searchParams.get("acheteur");
    assert.match(siret, /^[0-9]{14}$/);

    // Le lien force un regroupement sur toutes les années de l'extrait.
    await page.goto(urlDossier.href, { waitUntil: "networkidle" });
    await page.waitForFunction(() => /Regroupement sur SIRET déclaré/.test(document.querySelector("#etat").textContent));
    assert.equal(await page.locator("#source").inputValue(), "decp");
    assert.equal(await page.locator("#annee").inputValue(), "");
    assert.equal(await page.locator("#siret-acheteur").inputValue(), siret);
    assert.ok(await page.locator("article").count() > 0);
    const liens = await page.locator("article .lien-acheteur").evaluateAll(
      elems => elems.map(a => new URL(a.href).searchParams.get("acheteur")));
    assert.ok(liens.length > 0 && liens.every(id => id === siret));
    assert.match(await page.locator("#etat").textContent(), /aucun lien de projet déduit/);

    // Un identifiant correctement formé mais absent ne produit aucune correspondance.
    await page.locator("#siret-acheteur").fill("00000000000000");
    await page.locator("#lancer").click();
    await page.waitForFunction(() => /Regroupement sur SIRET déclaré 00000000000000/.test(
      document.querySelector("#etat").textContent));
    assert.equal(await page.locator("article").count(), 0);

    // Les paramètres non conformes sont rejetés avant consultation des lots.
    await page.goto(url + "/recherche-etendue.html?acheteur=%3Cscript%3E", { waitUntil: "networkidle" });
    assert.match(await page.locator("#etat").textContent(), /non conforme/);
    assert.equal(await page.locator("article").count(), 0);
    assert.deepEqual(erreurs, []);
  } finally {
    await browser.close();
    await new Promise((resolve, reject) => serveur.close(error => error ? reject(error) : resolve()));
  }
});


test("SIRET DECP–DILA : rattachement exact, ambiguïtés et altération interdite",
  { timeout: 90_000 }, async () => {
  const { serveur, url } = await demarrerServeur();
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1100, height: 820 } });
    const erreurs = [];
    page.on("pageerror", erreur => erreurs.push(String(erreur)));
    const r = await page.request.get(url + "/partitions/rattachements-acheteurs.json");
    assert.equal(r.ok(), true);
    const rapprochements = await r.json();
    assert.equal(rapprochements.verification_juridique_exterieure, false);

    // Privilégier une correspondance réellement constatée dans le corpus.
    let numero = Object.keys(rapprochements.rattachements)[0];
    if (!numero) {
      await page.goto(url + "/recherche-etendue.html", { waitUntil: "networkidle" });
      await page.waitForFunction(() => !document.querySelector("#source").disabled);
      await page.locator("#source").selectOption("decp");
      await page.locator("#annee").selectOption("");
      await page.locator("#lancer").click();
      await page.waitForFunction(() => /documents examinés/.test(
        document.querySelector("#etat").textContent));
      const lien = page.locator("article .lien-acheteur").first();
      numero = new URL(await lien.getAttribute("href"), page.url())
        .searchParams.get("acheteur");
    }
    assert.match(numero, /^[0-9]{14}$/);
    const consulter = url + "/recherche-etendue.html?acheteur=" + numero;
    await page.goto(consulter, { waitUntil: "networkidle" });
    await page.waitForFunction(() => !document.querySelector("#etat-institution").hidden);
    const resultat = await page.locator("#etat-institution").textContent();
    const dossier = rapprochements.rattachements[numero];
    if (!dossier) {
      assert.match(resultat, /Aucun SIRET concordant/);
    } else if (dossier.statut === "plusieurs_entites_memes_siret") {
      assert.match(resultat, /ambigu/);
    } else if (dossier.statut === "etat_institutionnel_non_actif_ou_inconnu") {
      assert.match(resultat, /non établi/);
    } else {
      assert.match(resultat, /Correspondance de SIRET déclarés/);
      assert.ok(resultat.includes(dossier.candidats[0].id));
    }
    assert.match(await page.locator("#etat").textContent(), /aucun lien de projet déduit/);

    // À taille identique, un octet modifié annule intégralement la restitution.
    await page.route("**/partitions/rattachements-acheteurs.json", async route => {
      const reponse = await route.fetch();
      const source = await reponse.text();
      const corrompu = source.replace('"version":', '"versiOn":');
      assert.notEqual(corrompu, source);
      assert.equal(Buffer.byteLength(corrompu), Buffer.byteLength(source));
      await route.fulfill({ response: reponse, body: corrompu });
    });
    await page.goto(consulter, { waitUntil: "networkidle" });
    await page.waitForFunction(() => /résultats non publiés/.test(
      document.querySelector("#etat").textContent));
    assert.equal(await page.locator("article").count(), 0);
    assert.deepEqual(erreurs, []);
  } finally {
    await browser.close();
    await new Promise((resolve, reject) => serveur.close(error => error ? reject(error) : resolve()));
  }
});


test("BOAMP–DECP : deux concordances datées séparées du résultat des marchés",
  { timeout: 120_000 }, async () => {
  const { serveur, url } = await demarrerServeur();
  const navigateur = await chromium.launch({ headless: true });
  try {
    const page = await navigateur.newPage();
    const erreurs = [];
    page.on("pageerror", e => erreurs.push(String(e)));
    const cas = [
      ["21060027600013", "25-94670", "5 identités"],
      ["18002002600019", "26-62030", "1 identités"]
    ];
    for (const [numero, avis, nombre] of cas) {
      await page.goto(url + "/recherche-etendue.html?acheteur=" + numero,
        { waitUntil: "networkidle" });
      await page.waitForFunction(() =>
        !document.querySelector("#avis-boamp-corrobores").hidden);
      const section = page.locator("#avis-boamp-corrobores");
      assert.match(await section.textContent(), new RegExp(avis));
      // Le décompte provient d'archives historiques distinctes de l'index.
      assert.match(await section.textContent(), /relevés DECP historiques/);
      assert.match(await section.textContent(), /aucun contrat commun ni besoin encore ouvert/);
      assert.equal(await section.locator("li").count(), 1);
      assert.ok((await section.locator("a").getAttribute("href")).includes(
        "correspondances_siret_boamp_decp_17.json"));
      assert.match(await page.locator("#etat").textContent(), /aucun lien de projet déduit/);
    }

    await page.goto(url + "/recherche-etendue.html?acheteur=00000000000000",
      { waitUntil: "networkidle" });
    await page.waitForFunction(() =>
      !document.querySelector("#avis-boamp-corrobores").hidden);
    assert.match(await page.locator("#avis-boamp-corrobores").textContent(),
      /ne démontre pas l'absence d'autres avis BOAMP/);
    assert.equal(await page.locator("#avis-boamp-corrobores li").count(), 0);

    // Une corruption qui conserve la taille invalide aussi le rendu des marchés :
    // aucune donnée possiblement contradictoire n'est publiée.
    await page.route("**/partitions/avis-boamp-corrobores.json", async route => {
      const response = await route.fetch();
      const original = await response.text();
      const altered = original.replace('"version":', '"versiOn":');
      assert.notEqual(original, altered);
      assert.equal(Buffer.byteLength(original), Buffer.byteLength(altered));
      await route.fulfill({ response, body: altered });
    });
    await page.goto(url + "/recherche-etendue.html?acheteur=21060027600013",
      { waitUntil: "networkidle" });
    await page.waitForFunction(() => /résultats non publiés/.test(
      document.querySelector("#etat").textContent));
    assert.equal(await page.locator("article").count(), 0);
    assert.equal(await page.locator("#avis-boamp-corrobores").isHidden(), true);
    assert.deepEqual(erreurs, []);
  } finally {
    await navigateur.close();
    await new Promise((resolve, reject) =>
      serveur.close(error => error ? reject(error) : resolve()));
  }
});
