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
function majAnnees() {
  const source = q("source").value;
  const select = q("annee");
  select.replaceChildren();
  const opt = document.createElement("option");
  opt.value = ""; opt.textContent = "Choisir"; select.append(opt);
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
  const mots = normaliser(q("termes").value.slice(0,120)).split(" ").filter(Boolean);
  const morceaux = manifeste.partitions.filter(p => p.source === source && p.annee === annee);
  const zone=q("resultats");
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
      // Le manifeste rend explicite le SHA calculé au build. La correspondance
      // des octets est vérifiée ici ; la CI atteste les empreintes à la publication.
      const lignes = JSON.parse(brut);
      if (!Array.isArray(lignes) || lignes.length !== p.documents) throw new Error("Lot incompatible");
      for (const d of lignes) {
        visites++;
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
      " · " + annee + "). " + Math.min(affiches,correspondant) +
      " affichées (plafond " + limiteAffichage + ").";
  } catch {
    zone.replaceChildren();
    q("etat").textContent="Impossible de vérifier toutes les partitions demandées ; résultats non publiés.";
  } finally { q("lancer").disabled=false; }
}
q("recherche").addEventListener("submit", consulter);
demarrer();
