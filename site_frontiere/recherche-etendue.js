/** Consultation des partitions sélectionnées, sans serveur ni HTML issu des sources. */
const q = id => document.getElementById(id);
const racine = "./partitions/";
const limiteAffichage = 100;
const francais = new Intl.NumberFormat("fr-FR");
let manifeste = null;

function normaliser(v) {
  return String(v || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("fr").replace(/\s+/g, " ").trim();
}
function lien(a, adresse, texte) {
  try {
    const u = new URL(adresse);
    if (u.protocol !== "https:") return;
    a.href = u.href;
    a.textContent = texte;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
  } catch { /* aucune destination externe non vérifiée */ }
}
/** Afficher les seules quantités observées, sans déduire une couverture nationale. */
function afficherBilanSelection(m) {
  const zone = q("bilan-selection");
  if (!m.selection) {
    zone.textContent = "Bilan de sélection indisponible dans cette version du catalogue.";
    return;
  }
  const b = m.selection;
  const sources = ["boamp", "emplois", "decp"];
  if (b.version !== "frontiere-bilan-selection-v1" ||
      b.couverture_nationale_etablie !== false ||
      b.pourcentage_couverture_calculable !== false ||
      !Array.isArray(b.sources) || b.sources.length !== sources.length) {
    throw new Error("Bilan de sélection incompatible.");
  }
  const liste = document.createElement("dl");
  for (const [i, source] of sources.entries()) {
    const ligne = b.sources[i];
    const fragments = m.partitions.filter(p => p.source === source);
    const nombre = fragments.reduce((n, p) => n + p.documents, 0);
    const annees = new Map();
    for (const p of fragments) annees.set(p.annee, (annees.get(p.annee) || 0) + p.documents);
    const declarees = ligne?.annees_indexees;
    if (ligne?.source !== source || !Number.isSafeInteger(ligne.documents_indexes) ||
        ligne.documents_indexes !== nombre ||
        ligne.plafond !== m.limite_par_source?.[source] ||
        ligne.plafond_atteint !== (nombre === ligne.plafond) ||
        !Number.isSafeInteger(ligne.enregistrements_sources_parcourus) ||
        ligne.enregistrements_sources_parcourus < nombre ||
        typeof ligne.unite_enregistrements_sources !== "string" ||
        !Array.isArray(declarees) || declarees.length !== annees.size ||
        !declarees.every(d => /^\\d{4}$/.test(d.annee) && annees.get(d.annee) === d.documents)) {
      throw new Error("Bilan de sélection contradictoire.");
    }
    const nom = document.createElement("dt");
    nom.textContent = source.toUpperCase() + " — " + francais.format(nombre) + " documents indexés";
    const detail = document.createElement("dd");
    const periode = declarees.map(d => d.annee + " (" + francais.format(d.documents) + ")").join(", ");
    detail.textContent = "Plafond : " + francais.format(ligne.plafond) +
      (ligne.plafond_atteint ? " (atteint)" : " (non atteint)") +
      ". Périodes représentées : " + (periode || "aucune") +
      ". Fichier source : " + francais.format(ligne.enregistrements_sources_parcourus) +
      " " + ligne.unite_enregistrements_sources + ".";
    liste.append(nom, detail);
  }
  const precision = document.createElement("p");
  precision.textContent = b.precision;
  zone.replaceChildren(liste, precision);
}

function majAnnees() {
  const source = q("source").value;
  const select = q("annee");
  select.replaceChildren();
  const opt = document.createElement("option");
  opt.value = ""; opt.textContent = "Toutes les années"; select.append(opt);
  const dates = [...new Set(manifeste.partitions.filter(p => p.source === source).map(p => p.annee))]
    .sort((a,b) => b.localeCompare(a));
  for (const annee of dates) {
    const o = document.createElement("option");
    o.value = annee; o.textContent = annee; select.append(o);
  }
  select.disabled = dates.length === 0;
  if (dates.length) select.value = dates[0];
}
async function demarrer() {
  try {
    const r = await fetch(racine + "manifeste.json", { cache: "no-cache", credentials: "omit" });
    if (!r.ok) throw new Error("Manifeste indisponible");
    const m = await r.json();
    if (m.version !== "frontiere-partitions-v1" || !Array.isArray(m.partitions)) throw new Error("Version incompatible");
    if (!m.partitions.every(p =>
      /^(boamp|emplois|decp)$/.test(p.source) &&
      /^\d{4}$/.test(p.annee) &&
      /^part-(boamp|emplois|decp)-\d{4}-\d{3}\.json$/.test(p.fichier) &&
      /^[0-9a-f]{64}$/.test(p.sha256) && p.documents <= 700 &&
      p.fichier.startsWith("part-" + p.source + "-" + p.annee + "-"))) {
      throw new Error("Partitions non conformes");
    }
    afficherBilanSelection(m);
    manifeste = m;
    q("source").disabled = false; q("source").value = "boamp";
    majAnnees();
    q("lancer").disabled = false;
    q("source").addEventListener("change", majAnnees);
    const total = m.partitions.reduce((n,p)=>n+p.documents,0);
    q("etat").textContent = francais.format(total) + " références au maximum dans " +
      m.partitions.length + " fichiers datés, couvrant les seuls extraits archivés.";
  } catch {
    q("etat").textContent = "Le catalogue des partitions est indisponible ; consultez les archives sur GitHub.";
  }
}
async function consulter(e) {
  e.preventDefault();
  if (!manifeste) return;
  const source = q("source").value, annee = q("annee").value;
  const debut = q("date-debut").value, fin = q("date-fin").value;
  const zone=q("resultats");
  if (debut && fin && debut > fin) {
    zone.replaceChildren();
    q("etat").textContent = "Période incohérente : la date de début dépasse la date de fin.";
    return;
  }
  const mots = normaliser(q("termes").value.slice(0,120)).split(" ").filter(Boolean);
  // Préciser le périmètre AVANT les téléchargements : une partition
  // entièrement en dehors de l'intervalle n'est jamais téléchargée.
  const morceaux = manifeste.partitions.filter(p =>
    p.source === source && (!annee || p.annee === annee) &&
    (!debut || p.annee >= debut.slice(0,4)) &&
    (!fin || p.annee <= fin.slice(0,4)));
  zone.replaceChildren();q("lancer").disabled=true;
  q("etat").textContent="Lecture de " + morceaux.length + " fichiers…";
  let correspondant=0, visites=0, affiches=0;
  try {
    for (const p of morceaux) {
      const rep = await fetch(racine + encodeURIComponent(p.fichier), { credentials:"omit" });
      if (!rep.ok) throw new Error("Fichier incomplet");
      const brut = await rep.text();
      const bytes = new TextEncoder().encode(brut);
      if (bytes.length !== p.octets) throw new Error("Taille incorrecte");
      if (!globalThis.crypto?.subtle) throw new Error("Vérification SHA-256 indisponible");
      const empreinte = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
      const hex = Array.from(empreinte, b => b.toString(16).padStart(2, "0")).join("");
      if (hex !== p.sha256) throw new Error("Empreinte incorrecte");
      // Tout le contenu du lot doit correspondre au manifeste publié.
      const lignes = JSON.parse(brut);
      if (!Array.isArray(lignes) || lignes.length !== p.documents) throw new Error("Lot incompatible");
      for (const d of lignes) {
        visites++;
        if ((debut && d.date < debut) || (fin && d.date > fin)) continue;
        if (mots.some(w => !normaliser([d.titre,d.organisme,d.localisation,d.code,d.id].join(" ")).includes(w))) continue;
        correspondant++;
        if (affiches >= limiteAffichage) continue;
        affiches++;
        const el=document.createElement("article");
        const met=document.createElement("div");met.className="meta";
        const s=document.createElement("span");s.textContent=source.toUpperCase();
        const t=document.createElement("time");t.textContent=d.date || "Date absente";
        met.append(s,t);el.append(met);
        const h=document.createElement("h2"),a=document.createElement("a");
        lien(a,d.lien,d.titre); if (!a.href) a.textContent=d.titre;
        h.append(a);el.append(h);
        const org=document.createElement("p");org.textContent=[d.organisme,d.localisation,d.code].filter(Boolean).join(" · ");
        el.append(org);
        const preuve=document.createElement("p");preuve.textContent="Référence " + d.id + " · ";
        const lienSource=document.createElement("a");
        if (/^[a-z0-9_./-]+$/i.test(d.provenance || "") && !d.provenance.includes("..")) {
          const sha=/^[0-9a-f]{40}$/.test(manifeste.revision_sources || "") ? manifeste.revision_sources : "main";
          lien(lienSource,"https://github.com/fraware/frontiere-institut-interet-public/blob/" + sha +
            "/" + d.provenance.split("/").map(encodeURIComponent).join("/"),"Archive et provenance");
          preuve.append(lienSource);
        }
        el.append(preuve);zone.append(el);
      }
    }
    q("etat").textContent = francais.format(correspondant) + " correspondances sur " +
      francais.format(visites) + " documents examinés (" + source.toUpperCase() +
      " · " + (annee || "toutes années") + "). " + Math.min(affiches,correspondant) +
      " affichées (plafond " + limiteAffichage + ").";
  } catch {
    zone.replaceChildren();
    q("etat").textContent="Impossible de vérifier toutes les partitions demandées ; résultats non publiés.";
  } finally { q("lancer").disabled=false; }
}
q("recherche").addEventListener("submit", consulter);
demarrer();
