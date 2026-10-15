/* FRONTIÈRE — lecture et recherche locale dans l'index documentaire publié.
 * Aucun serveur de recherche, traceur, compte utilisateur ou appel à un tiers.
 * Les champs provenant des sources sont toujours insérés avec textContent.
 */
const FICHIER = "./recherche-index.json";
const SOURCE = Object.freeze({
  boamp: "BOAMP · consultation", emplois: "Emplois publics · poste",
  decp: "DECP · marché attribué"
});
const PAR_PAGE = 12;
const etat = { documents: [], page: 1, charger: false, filtres: { q: "", source: "" }, meta: null };

function element(tag, texte, classe) {
  const n = document.createElement(tag);
  if (classe) n.className = classe;
  if (texte !== undefined && texte !== null) n.textContent = String(texte);
  return n;
}
function normaliser(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("fr").replace(/\s+/g, " ").trim();
}
function dateLocale(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return "Date non précisée";
  const d = new Date(value + "T00:00:00Z");
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" }).format(d);
}
function lienSecurise(url) {
  try {
    const u = new URL(url);
    return u.protocol === "https:" ? u.href : null;
  } catch { return null; }
}
function texteRecherche(doc) {
  return normaliser([doc.titre, doc.organisme, doc.localisation, doc.code, doc.id].join(" "));
}
function correspond(doc, termes, source) {
  if (source && doc.source !== source) return false;
  const index = texteRecherche(doc);
  return termes.every(terme => index.includes(terme));
}
function notice(doc) {
  const article = element("article", undefined, "resultat");
  const haut = element("div", undefined, "resultat-entete");
  haut.append(element("span", SOURCE[doc.source], "resultat-source"));
  haut.append(element("time", dateLocale(doc.date), "resultat-date"));
  article.append(haut);
  const titre = element("h3", undefined, "resultat-titre");
  const url = lienSecurise(doc.lien);
  if (url) {
    const ancre = element("a", doc.titre);
    ancre.href = url;
    ancre.target = "_blank";
    ancre.rel = "noopener noreferrer";
    titre.append(ancre);
  } else titre.textContent = doc.titre;
  article.append(titre);
  const corps = [doc.organisme, doc.localisation, doc.code].filter(Boolean);
  if (corps.length) article.append(element("p", corps.join(" · "), "resultat-details"));
  const bas = element("p", undefined, "resultat-preuve");
  bas.append(element("span", "Référence " + doc.id + " · "));
  const chemin = doc.provenance;
  if (typeof chemin === "string" && /^[a-z0-9_./-]+$/i.test(chemin) && !chemin.includes("..")) {
    const lien = element("a", "Archive et provenance ↗");
    lien.href = "https://github.com/fraware/frontiere-institut-interet-public/blob/main/" +
      chemin.split("/").map(encodeURIComponent).join("/");
    lien.target = "_blank";
    lien.rel = "noopener noreferrer";
    bas.append(lien);
  }
  article.append(bas);
  return article;
}
function compter(n) {
  return new Intl.NumberFormat("fr-FR").format(n);
}
function afficher() {
  const form = document.getElementById("formulaire-recherche");
  const entree = document.getElementById("expression-recherche");
  const filtre = document.getElementById("filtre-source");
  const zone = document.getElementById("resultats-recherche");
  const message = document.getElementById("etat-recherche");
  const suite = document.getElementById("suite-recherche");
  if (!form || !entree || !filtre || !zone || !message || !suite) return;

  const q = normaliser(entree.value.slice(0, 120));
  const termes = q.split(" ").filter(Boolean).slice(0, 10);
  const source = filtre.value;
  const matches = etat.documents.filter(doc => correspond(doc, termes, source));
  const debut = (etat.page - 1) * PAR_PAGE;
  zone.replaceChildren();
  for (const doc of matches.slice(debut, debut + PAR_PAGE)) zone.append(notice(doc));
  const fin = Math.min(debut + PAR_PAGE, matches.length);
  message.textContent = matches.length
    ? compter(matches.length) + " documents dans cet extrait · " + compter(debut + 1) +
      " à " + compter(fin) + " affichés"
    : "Aucun document dans cet extrait. Essayez des termes plus larges ou changez de source.";
  suite.hidden = fin >= matches.length;
  suite.disabled = fin >= matches.length;
}
async function demarrer() {
  const etatDocument = document.getElementById("etat-index");
  const entree = document.getElementById("expression-recherche");
  const form = document.getElementById("formulaire-recherche");
  const filtre = document.getElementById("filtre-source");
  const suite = document.getElementById("suite-recherche");
  if (!etatDocument || !form || !entree || !filtre || !suite) return;
  form.addEventListener("submit", event => {
    event.preventDefault();
    etat.page = 1;
    afficher();
  });
  filtre.addEventListener("change", () => { etat.page = 1; afficher(); });
  suite.addEventListener("click", () => {
    etat.page += 1;
    afficher();
    document.getElementById("etat-recherche").scrollIntoView({ block: "nearest" });
  });
  try {
    const reponse = await fetch(FICHIER, { cache: "no-cache", credentials: "omit" });
    if (!reponse.ok) throw new Error("HTTP " + reponse.status);
    const doc = await reponse.json();
    if (doc.version !== "frontiere-index-public-borne-v1" ||
        doc.portee !== "echantillon_documentaire_non_exhaustif" ||
        doc.recherche_temps_reel !== false || !Array.isArray(doc.documents) ||
        !doc.sources || doc.documents.length > 1900) {
      throw new Error("Format de l'index incompatible.");
    }
    const autorisees = new Set(Object.keys(SOURCE));
    if (!doc.documents.every(x => x && autorisees.has(x.source) &&
        typeof x.titre === "string" && typeof x.id === "string" &&
        typeof x.date === "string" && typeof x.provenance === "string")) {
      throw new Error("Document public incompatible.");
    }
    etat.documents = doc.documents;
    etat.meta = doc.sources;
    etatDocument.textContent =
      "Extrait consultable : " + compter(doc.documents.length) +
      " documents sélectionnés dans les archives versionnées. " +
      "BOAMP " + compter(doc.sources.boamp.retenus) + " · emplois " +
      compter(doc.sources.emplois.retenus) + " · DECP " +
      compter(doc.sources.decp.retenus) +
      ". Sélection non exhaustive, actualisée lors du dernier déploiement du site.";
    form.classList.remove("en-chargement");
    entree.disabled = false;
    filtre.disabled = false;
    afficher();
  } catch (erreur) {
    etatDocument.textContent =
      "Index documentaire indisponible à ce déploiement. Les archives et leurs manifestes restent accessibles dans GitHub.";
    document.getElementById("etat-recherche").textContent =
      "La recherche ne peut pas être initialisée.";
  }
}
if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", demarrer);
  else demarrer();
}
export { normaliser, correspond, lienSecurise };
