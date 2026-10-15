import { siretAdmissible, siretAcheteur, appartientAuMemeAcheteur, ordreChronologique } from "./acheteurs-decp.js";
import { construireChronologieDocumentaire } from "./chronologies-documentaires.js";
import { qualifierDocument, TYPES_DOCUMENTAIRES, VERSION_QUALIFICATION } from "./qualification-besoins.js";
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
        new Set(declarees.map(d => d?.annee)).size !== annees.size ||
        typeof b.precision !== "string" ||
        !declarees.every(d => /^\d{4}$/.test(d.annee) && annees.get(d.annee) === d.documents)) {
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


/** Attester les compteurs par les lots effectivement annoncés, sans
 * présenter un nombre de documents comme le nombre de besoins ouverts.
 */
function afficherBilanQualifications(m) {
  const zone = q("bilan-qualifications");
  const b = m.qualification_besoins;
  if (!b) {
    zone.textContent = "Qualifications indisponibles dans cette version du catalogue.";
    return;
  }
  const sources = ["boamp", "emplois", "decp"];
  const total = m.partitions.reduce((n, p) => n + p.documents, 0);
  if (b.version !== VERSION_QUALIFICATION ||
      b.documents_qualifies !== total ||
      b.couverture_nationale_demonstree !== false ||
      b.besoins_actuels_non_satisfaits_demonstres !== 0 ||
      b.projets_communs_demonstres !== 0 ||
      b.hypotheses_de_besoins !== 0 ||
      !Array.isArray(b.sources) || b.sources.length !== sources.length ||
      typeof b.precision !== "string") {
    throw new Error("Bilan de qualification non conforme");
  }
  const liste = document.createElement("dl");
  for (const [i, source] of sources.entries()) {
    const e = b.sources[i], type = TYPES_DOCUMENTAIRES[source];
    const attendu = m.partitions.filter(p => p.source === source)
      .reduce((n, p) => n + p.documents, 0);
    if (e?.source !== source || e.type !== type.code ||
        e.documents !== attendu ||
        m.selection?.sources?.[i]?.documents_indexes !== attendu) {
      throw new Error("Comptage documentaire non cohérent");
    }
    const titre = document.createElement("dt");
    titre.textContent = type.titre + " — " + francais.format(attendu) + " documents";
    const definition = document.createElement("dd");
    definition.textContent = type.explication;
    liste.append(titre, definition);
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
    afficherBilanQualifications(m);
    manifeste = m;
    q("source").disabled = false; q("source").value = "boamp";
    majAnnees();
    q("lancer").disabled = false;
    q("source").addEventListener("change", majAnnees);
    q("siret-acheteur").addEventListener("input", () => {
      if (q("siret-acheteur").value) {
        q("source").value = "decp";
        majAnnees();
        q("annee").value = "";
      }
    });
    const total = m.partitions.reduce((n,p)=>n+p.documents,0);
    q("etat").textContent = francais.format(total) + " références au maximum dans " +
      m.partitions.length + " fichiers datés, couvrant les seuls extraits archivés.";
    const parametres = new URLSearchParams(location.search);
    if (parametres.has("acheteur")) {
      const demandes = parametres.getAll("acheteur");
      if (demandes.length !== 1 || !siretAdmissible(demandes[0])) {
        q("etat").textContent = "Identifiant SIRET demandé non conforme : 14 chiffres attendus.";
      } else {
        q("source").value = "decp";
        majAnnees();
        q("annee").value = "";
        q("siret-acheteur").value = demandes[0];
        q("recherche").requestSubmit();
      }
    }
  } catch {
    q("etat").textContent = "Le catalogue des partitions est indisponible ; consultez les archives sur GitHub.";
  }
}
/** Ne restituer les liens qu'à partir de références déjà indexées et contrôlées. */
function ajouterResultat(d, source, zone) {
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
    if (manifeste.qualification_besoins) {
      const regle = TYPES_DOCUMENTAIRES[source];
      const qualif = document.createElement("div");
      qualif.className = "qualification";
      const titreQualif = document.createElement("strong");
      titreQualif.textContent = regle.titre;
      const raison = document.createElement("span");
      raison.textContent = regle.explication;
      qualif.append(titreQualif, raison);
      el.append(qualif);
    }
    const preuve=document.createElement("p");preuve.textContent="Référence " + d.id + " · ";
    const lienSource=document.createElement("a");
    if (/^[a-z0-9_./-]+$/i.test(d.provenance || "") && !d.provenance.includes("..")) {
      const sha=/^[0-9a-f]{40}$/.test(manifeste.revision_sources || "") ? manifeste.revision_sources : "main";
      lien(lienSource,"https://github.com/fraware/frontiere-institut-interet-public/blob/" + sha +
        "/" + d.provenance.split("/").map(encodeURIComponent).join("/"),"Archive et provenance");
      preuve.append(lienSource);
    }
    el.append(preuve);
    const acheteur = siretAcheteur(d);
    if (acheteur) {
      const lienDossier = document.createElement("a");
      lienDossier.className = "lien-acheteur";
      lienDossier.href = "./recherche-etendue.html?acheteur=" + acheteur;
      lienDossier.textContent = "Consulter les marchés indexés du même SIRET déclaré";
      const paragraphe = document.createElement("p");
      paragraphe.append(lienDossier);
      el.append(paragraphe);
    }
    zone.append(el);
}


/** Vérifier séparément le jeu d'identités DILA produit à la construction.
 * Aucun rapprochement n'est autorisé sur le nom d'un organisme.
 */
async function lireRattachementInstitutionnel(siret) {
  const m = manifeste.rattachements_acheteurs;
  if (!m) {
    return "Rattachement institutionnel non disponible dans cette version du catalogue.";
  }
  if (m.fichier !== "rattachements-acheteurs.json" ||
      m.version !== "frontiere-rattachements-acheteurs-dila-v1" ||
      !Number.isSafeInteger(m.octets) || m.octets <= 0 || m.octets > 2_000_000 ||
      !/^[0-9a-f]{64}$/.test(m.sha256) ||
      !Number.isSafeInteger(m.documents_decp_indexes) ||
      m.documents_decp_indexes !== manifeste.selection?.sources?.find(s => s.source === "decp")?.documents_indexes ||
      !Number.isSafeInteger(m.sirets_decp_distincts) ||
      m.sirets_decp_distincts > m.documents_decp_indexes) {
    throw new Error("Manifeste institutionnel non conforme");
  }
  const rep = await fetch(racine + m.fichier, { credentials: "omit" });
  if (!rep.ok) throw new Error("Répertoire institutionnel indisponible");
  const brut = await rep.text(), octets = new TextEncoder().encode(brut);
  if (octets.length !== m.octets || !globalThis.crypto?.subtle) {
    throw new Error("Taille ou contrôle cryptographique indisponible");
  }
  const code = new Uint8Array(await crypto.subtle.digest("SHA-256", octets));
  const empreinte = Array.from(code, n => n.toString(16).padStart(2, "0")).join("");
  if (empreinte !== m.sha256) throw new Error("Empreinte institutionnelle incorrecte");
  const rapport = JSON.parse(brut);
  if (rapport.version !== m.version ||
      rapport.source_achats !== "decp_archives_publiees_extrait_statique" ||
      rapport.verification_juridique_exterieure !== false ||
      rapport.rapprocher_par_nom !== false ||
      rapport.documents_decp_indexes !== m.documents_decp_indexes ||
      rapport.sirets_decp_distincts !== m.sirets_decp_distincts ||
      !rapport.rattachements || typeof rapport.rattachements !== "object" ||
      Array.isArray(rapport.rattachements)) {
    throw new Error("Répertoire institutionnel contradictoire");
  }
  const fiche = Object.hasOwn(rapport.rattachements, siret)
    ? rapport.rattachements[siret] : null;
  if (!fiche) {
    return "Aucun SIRET concordant identifié dans les deux instantanés DILA étudiés. " +
      "Cela ne démontre pas l'absence de l'organisme dans les répertoires nationaux.";
  }
  if (fiche.siret !== siret || !Array.isArray(fiche.candidats) ||
      fiche.candidats.length === 0 || fiche.candidats.length > 120_000 ||
      !fiche.candidats.every(x =>
        /^FRONTIERE-INST-[A-Z0-9-]+$/.test(x?.id) &&
        typeof x.nom === "string" && x.nom.length <= 350 &&
        ["dila_roae", "dila_annuaire_local"].includes(x.source_id))) {
    throw new Error("Entités institutionnelles non conformes");
  }
  if (fiche.statut === "identifiant_exact_unique_dans_les_archives_dila" &&
      fiche.candidats.length === 1 && fiche.candidats[0].etat === "ACTIF") {
    const c = fiche.candidats[0];
    return "Correspondance de SIRET déclarés dans les archives DILA : " + c.nom +
      " (" + c.id + ", " + c.source_id + "). Identité juridique et lien contractuel non revérifiés.";
  }
  if (fiche.statut === "plusieurs_entites_memes_siret" &&
      fiche.candidats.length > 1) {
    return "Plusieurs entrées DILA portent ce SIRET (" + fiche.candidats.length +
      ") : rapprochement institutionnel ambigu, aucune entité choisie.";
  }
  if (fiche.statut === "etat_institutionnel_non_actif_ou_inconnu" &&
      fiche.candidats.length === 1 && fiche.candidats[0].etat !== "ACTIF") {
    return "Un enregistrement DILA porte ce SIRET, avec état " +
      fiche.candidats[0].etat + ". Rattachement actuel non établi.";
  }
  throw new Error("Statut institutionnel non cohérent");
}


/** Afficher uniquement les avis étudiés et corroborés, depuis l'extrait
 * dont le manifeste atteste la taille et l'empreinte cryptographique.
 * Les avis du lot indépendant n'obéissent pas aux filtres DECP courants.
 */
async function afficherAvisBoampCorrobores(siret) {
  const zone = q("avis-boamp-corrobores");
  const m = manifeste.avis_boamp_corroborees;
  if (!m) {
    zone.textContent = "Étude BOAMP indépendante indisponible dans cette version du site.";
    zone.hidden = false;
    return [];
  }
  if (m.fichier !== "avis-boamp-corrobores.json" ||
      m.version !== "frontiere-avis-boamp-corrobores-v1" ||
      !Number.isSafeInteger(m.octets) || m.octets < 100 || m.octets > 20000 ||
      !/^[a-f0-9]{64}$/.test(m.sha256) ||
      m.empreinte_registre !==
        "6dbdd44379ddbc48f2d46f59ae410653613ca880a431a38b716d4a9f7ec544d7" ||
      m.nombre_avis_etudies !== 17 || m.nombre_corroborees !== 2) {
    throw new Error("Métadonnées BOAMP indépendantes incorrectes");
  }
  const reponse = await fetch(racine + m.fichier, { credentials: "omit" });
  if (!reponse.ok) throw new Error("Observations BOAMP indisponibles");
  const octets = new Uint8Array(await reponse.arrayBuffer());
  if (octets.length !== m.octets || !globalThis.crypto?.subtle) {
    throw new Error("Contrôle de taille ou empreinte BOAMP indisponible");
  }
  const empreinte = Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", octets)),
    x => x.toString(16).padStart(2, "0")).join("");
  if (empreinte !== m.sha256) throw new Error("Empreinte des observations BOAMP incorrecte");
  const rapport = JSON.parse(new TextDecoder().decode(octets));
  if (rapport.version !== m.version || rapport.population_avis_etudies !== 17 ||
      rapport.population_sirets_distincts !== 16 ||
      rapport.nombre_avis_corroborees !== 2 ||
      rapport.sha256_registre_source !== m.empreinte_registre ||
      rapport.sources_archives_non_exhaustives !== true ||
      rapport.contrats_communs_demonstres !== 0 ||
      rapport.rapprochement_par_nom !== false ||
      rapport.extrait_decp_public_couvert !== false ||
      !Array.isArray(rapport.avis) || rapport.avis.length !== 2) {
    throw new Error("Portée du rapport BOAMP contradictoire");
  }
  const ids = new Set();
  for (const a of rapport.avis) {
    if (!/^[0-9]{2}-[0-9]{2,8}$/.test(a?.avis_boamp) ||
        ids.has(a.avis_boamp) ||
        !/^20[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(a.date_parution || "") ||
        !siretAdmissible(a.acheteur_siret) ||
        !Number.isSafeInteger(a.identites_marches_decp_dans_archives) ||
        a.identites_marches_decp_dans_archives < 1 ||
        !/^[a-f0-9]{64}$/.test(a.preuve_boamp_sha256 || "") ||
        !/^[a-f0-9]{64}$/.test(a.preuve_administrative_sha256 || "") ||
        !a.chemin_preuve_boamp?.startsWith("/results/0/donnees/EFORMS/")) {
      throw new Error("Avis BOAMP documenté non conforme");
    }
    ids.add(a.avis_boamp);
  }
  const correspondants = rapport.avis.filter(a => a.acheteur_siret === siret);
  const h = document.createElement("h2");
  h.textContent = "Avis BOAMP documentés dans une étude indépendante";
  const precision = document.createElement("p");
  precision.textContent =
    "Enquête limitée à 17 avis (16 établissements distincts). Les concordances " +
    "concernent des SIRET déclarés et contrôlés dans des réponses administratives ; " +
    "elles ne prouvent aucun contrat commun ni besoin encore ouvert. " +
    "Ces avis sont indépendants des filtres et du plafond de l'index DECP.";
  const liste = document.createElement("ol");
  for (const a of correspondants) {
    const ligne = document.createElement("li");
    const description = document.createElement("span");
    description.textContent = "Avis " + a.avis_boamp + " du " + a.date_parution +
      " — " + francais.format(a.identites_marches_decp_dans_archives) +
      (a.identites_marches_decp_dans_archives === 1
        ? " identité de marché" : " identités de marchés") +
      " du même SIRET dans les relevés DECP historiques. ";
    const preuve = document.createElement("a");
    const rev = /^[a-f0-9]{40}$/.test(manifeste.revision_sources || "")
      ? manifeste.revision_sources : "main";
    lien(preuve,
      "https://github.com/fraware/frontiere-institut-interet-public/blob/" + rev +
      "/institutionnel/besoins_publics/correspondances_siret_boamp_decp_17.json",
      "Consulter le registre et les empreintes");
    ligne.append(description, preuve);
    liste.append(ligne);
  }
  zone.replaceChildren(h, precision);
  if (correspondants.length) zone.append(liste);
  else {
    const absence = document.createElement("p");
    absence.textContent = "Aucune concordance observée pour ce SIRET parmi " +
      "les 17 avis étudiés. Cela ne démontre pas l'absence d'autres avis BOAMP.";
    zone.append(absence);
  }
  zone.hidden = false;
  return rapport.avis;
}


/** Présenter l'ordre des dates, sans attribuer aux documents une relation
 * opérationnelle. Les informations DILA n'ont pas de date d'effet fiable
 * dans cet index et restent affichées à part.
 */
function afficherChronologieDocumentaire(siret, marches, avis) {
  const zone = q("chronologie-documentaire");
  const chronologie = construireChronologieDocumentaire(siret, marches, avis);
  const titre = document.createElement("h2");
  titre.textContent = "Chronologie des documents associés au SIRET " + siret;
  const bilan = document.createElement("p");
  bilan.textContent = francais.format(chronologie.decomptes.documents_decp_index) +
    " document(s) DECP dans l'extrait indexé et " +
    francais.format(chronologie.decomptes.avis_boamp_etude) +
    " avis BOAMP corroboré(s) dans l'étude indépendante.";
  const reserve = document.createElement("p");
  reserve.textContent = chronologie.limite_interpretation +
    " Les référentiels administratifs sont présentés séparément, " +
    "sans leur attribuer une date de création ou de changement.";
  const liste = document.createElement("ol");
  for (const evenement of chronologie.evenements.slice(0, 100)) {
    const ligne = document.createElement("li");
    const date = document.createElement("time");
    date.dateTime = evenement.date;
    date.textContent = evenement.date;
    const provenance = document.createElement("span");
    provenance.className = "type";
    provenance.textContent = evenement.source === "boamp"
      ? "BOAMP — date de parution d'avis"
      : "DECP — date documentaire (notification ou publication déclarée)";
    const intitule = document.createElement("span");
    intitule.className = "titre-evt";
    intitule.textContent = evenement.titre + " · Référence " + evenement.reference;
    const archive = document.createElement("a");
    const sha = /^[a-f0-9]{40}$/.test(manifeste.revision_sources || "")
      ? manifeste.revision_sources : "main";
    lien(archive, "https://github.com/fraware/frontiere-institut-interet-public/blob/" +
      sha + "/" + evenement.provenance.split("/").map(encodeURIComponent).join("/"),
      "Source archivée et preuves");
    ligne.append(date, provenance, intitule, archive);
    liste.append(ligne);
  }
  zone.replaceChildren(titre, bilan, reserve);
  if (chronologie.evenements.length > 100) {
    const truncature = document.createElement("p");
    truncature.textContent = "Chronologie limitée aux 100 documents les plus récents parmi " +
      chronologie.evenements.length + " événements documentaires admis.";
    zone.append(truncature);
  }
  if (chronologie.evenements.length) zone.append(liste);
  else {
    const absence = document.createElement("p");
    absence.textContent = "Aucun document daté dans les deux périmètres examinés ; " +
      "cela ne signifie pas absence d'activité de l'établissement.";
    zone.append(absence);
  }
  zone.hidden = false;
}

async function consulter(e) {
  e.preventDefault();
  if (!manifeste) return;
  const source = q("source").value, annee = q("annee").value;
  const debut = q("date-debut").value, fin = q("date-fin").value;
  const zone=q("resultats");
  const situation = q("etat-institution");
  situation.hidden = true;
  situation.textContent = "";
  const boamp = q("avis-boamp-corrobores");
  boamp.hidden = true;
  boamp.replaceChildren();
  const chronologie = q("chronologie-documentaire");
  chronologie.hidden = true;
  chronologie.replaceChildren();
  const acheteurDemande = q("siret-acheteur").value.trim();
  if (acheteurDemande && (!siretAdmissible(acheteurDemande) || source !== "decp")) {
    zone.replaceChildren();
    q("etat").textContent = "Filtre d'acheteur invalide : saisir 14 chiffres et sélectionner DECP.";
    return;
  }
  if (debut && fin && debut > fin) {
    zone.replaceChildren();
    q("etat").textContent = "Période incohérente : la date de début dépasse la date de fin.";
    return;
  }
  const mots = normaliser(q("termes").value.slice(0,120)).split(" ").filter(Boolean);
  // Préciser le périmètre AVANT les téléchargements : une partition
  // entièrement en dehors de l'intervalle n'est jamais téléchargée.
  const morceaux = manifeste.partitions.filter(p =>
    p.source === source && (acheteurDemande || (
      (!annee || p.annee === annee) &&
      (!debut || p.annee >= debut.slice(0,4)) &&
      (!fin || p.annee <= fin.slice(0,4)))));
  zone.replaceChildren();q("lancer").disabled=true;
  q("etat").textContent="Lecture de " + morceaux.length + " fichiers…";
  let correspondant=0, visites=0, affiches=0;
  const documentsAcheteur = [];
  const documentsAcheteurNonFiltres = [];
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
      // Les catégories sont reconstruites indépendamment avant tout affichage.
      // Une incohérence interdit la publication des résultats, même filtrés.
      if (manifeste.qualification_besoins) {
        for (const d of lignes) {
          if (JSON.stringify(d?.qualification) !== JSON.stringify(qualifierDocument(d)) ||
              d.source !== p.source || d.date.slice(0, 4) !== p.annee) {
            throw new Error("Qualification de partition contradictoire");
          }
        }
      }
      for (const d of lignes) {
        visites++;
        if (acheteurDemande) {
          if (!appartientAuMemeAcheteur(d, acheteurDemande)) continue;
          documentsAcheteurNonFiltres.push(d);
        }
        if ((debut && d.date < debut) || (fin && d.date > fin)) continue;
        if (acheteurDemande && annee && d.date.slice(0,4) !== annee) continue;
        if (mots.some(w => !normaliser([d.titre,d.organisme,d.localisation,d.code,d.id].join(" ")).includes(w))) continue;
        correspondant++;
        if (acheteurDemande) {
          // Conserver uniquement les références du SIRET exactement déclaré.
          // Un tri des dates est effectué lorsque tous les lots sont attestés.
          documentsAcheteur.push(d);
        } else if (affiches < limiteAffichage) {
          affiches++;
          ajouterResultat(d, source, zone);
        }
      }
    }
    if (acheteurDemande) {
      situation.textContent = await lireRattachementInstitutionnel(acheteurDemande);
      const avisEtudies = await afficherAvisBoampCorrobores(acheteurDemande);
      afficherChronologieDocumentaire(acheteurDemande, documentsAcheteurNonFiltres, avisEtudies);
      situation.hidden = false;
      documentsAcheteur.sort(ordreChronologique);
      for (const document of documentsAcheteur.slice(0, limiteAffichage)) {
        ajouterResultat(document, source, zone);
        affiches++;
      }
    }
    q("etat").textContent = francais.format(correspondant) + " correspondances sur " +
      francais.format(visites) + " documents examinés (" + source.toUpperCase() +
      " · " + (annee || "toutes années") + "). " + Math.min(affiches,correspondant) +
      " affichées (plafond " + limiteAffichage + ")." +
      (acheteurDemande ? " Regroupement sur SIRET déclaré " + acheteurDemande +
        ", uniquement dans l'extrait DECP indexé ; aucun lien de projet déduit." : "");
  } catch {
    zone.replaceChildren();
    situation.hidden = true;
    situation.textContent = "";
    boamp.hidden = true;
    boamp.replaceChildren();
    chronologie.hidden = true;
    chronologie.replaceChildren();
    q("etat").textContent="Impossible de vérifier toutes les sources demandées ; résultats non publiés.";
  } finally { q("lancer").disabled=false; }
}
q("recherche").addEventListener("submit", consulter);
demarrer();
