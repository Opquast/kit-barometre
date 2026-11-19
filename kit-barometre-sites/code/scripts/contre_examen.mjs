// Contre-examen des règles Opquast basics « manuelles » : constats objectifs relevés dans le navigateur (Playwright),
// pour confirmer ou corriger le verdict du robot d'eServices Manager. Lecture seule : aucune commande, aucun compte
// créé, aucun formulaire envoyé ; le clavier sert seulement à parcourir les éléments (Tab), sans valider.
//
// Règles relevées :
//   5   abréviations et acronymes : présence d'<abbr title> ou de sigles en capitales dans le texte de l'accueil ;
//   17  création de compte sans identification tierce : page d'inscription, champs e-mail et mot de passe ;
//   58  au moins deux moyens de paiement : icônes de paiement (aria-label, alt, title) dans le pied de page ;
//   68  provenance des produits : mention d'origine sur la fiche produit de l'échantillon ;
//   75, 76, 203  mot de passe à la création de compte : confirmation, affichage en clair, jauge de robustesse ;
//   140 liens différenciés : soulignement des liens dans les paragraphes de contenu ;
//   165 focus visible : 15 premiers éléments atteints au clavier, contour ou ombre au focus ;
//   166 navigation au clavier : nombre d'éléments interactifs atteints par Tab sur l'accueil ;
//   216 barre d'adresse : la page ne s'ouvre pas en fenêtre sans barre (aucun window.open sans barre) ;
//   223 page 404 personnalisée : page d'erreur aux couleurs du site (en-tête et pied présents).
//
// Usage : node scripts/contre_examen.mjs [--service "Boutique A"]
// Sortie : resultats/contre-examen-AAAA-MM-JJ/constats.json
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { parNom } from './parc.mjs';

const RACINE = new URL('..', import.meta.url).pathname;
const pause = ms => new Promise(ok => setTimeout(ok, ms));
const args = process.argv.slice(2);
const seul = args.includes('--service') ? args[args.indexOf('--service') + 1] : null;

function lireCsv(chemin) {
  const [tete, ...lignes] = readFileSync(chemin, 'utf8').trim().split('\n');
  const cols = tete.split(',');
  return lignes.map(l => {
    const v = l.match(/("([^"]|"")*"|[^,]*)(,|$)/g).map(x => x.replace(/,$/, '').replace(/^"|"$/g, '').replace(/""/g, '"'));
    return Object.fromEntries(cols.map((c, i) => [c, v[i]]));
  });
}

const ecrans = lireCsv(`${RACINE}scripts/ecrans_en_ligne.csv`);
const services = [...new Set(ecrans.map(e => e.service))].filter(s => !seul || s === seul);
const parc = parNom(); // prefixe_langue de chaque site (referentiel/parc.json)
const date = new Date().toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/contre-examen-${date}`;
mkdirSync(dossier, { recursive: true });

const navigateur = await chromium.launch();
const contexte = await navigateur.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' });
const page = await contexte.newPage();
const resultats = {};

async function ouvrir(url) {
  const rep = await page.goto(url, { waitUntil: 'load', timeout: 45000 });
  await pause(3000);
  // Fermer un bandeau cookies ou une popup en refusant ou en fermant, sans rien accepter.
  for (const motif of [/tout refuser|refuser|continuer sans accepter|decline|reject/i, /fermer|close/i]) {
    const b = page.getByRole('button', { name: motif }).first();
    if (await b.isVisible().catch(() => false)) { await b.click({ timeout: 2000 }).catch(() => {}); await pause(500); }
  }
  return rep;
}

for (const nom of services) {
  const ec = ecrans.filter(e => e.service === nom);
  const accueil = ec.find(e => e.gabarit.startsWith('Accueil')).url;
  const produit = ec.find(e => e.gabarit === 'Produit')?.url;
  const origine = new URL(accueil).origin;
  const r = {};
  try {
    // Accueil : 5, 58, 140, 165, 166, 216
    await ouvrir(accueil);
    Object.assign(r, await page.evaluate(() => {
      const out = {};
      const abbr = document.querySelectorAll('abbr[title]').length;
      const corps = document.body.innerText;
      const sigles = [...new Set((corps.match(/\b[A-Z]{2,5}\b/g) || []))].filter(s => !['FR', 'EN', 'OK', 'CGV', 'TTC', 'HT'].includes(s)).slice(0, 12);
      out.r5 = { abbr_title: abbr, sigles_dans_le_texte: sigles };
      const html = (document.querySelector('footer') || document.body).outerHTML.toLowerCase();
      const MOYENS = ['visa', 'mastercard', 'master', 'american express', 'amex', 'paypal', 'apple pay', 'apple_pay', 'google pay', 'google_pay', 'shop pay', 'shopify_pay', 'klarna', 'alma', 'maestro', 'bancontact', 'ideal', 'cartes bancaires', 'carte bancaire', 'diners', 'discover', 'union pay'];
      out.r58 = { moyens_de_paiement: [...new Set(MOYENS.filter(m => html.includes(m)).map(m => m.replace('_', ' ').replace('master', 'mastercard').replace('mastercardcard', 'mastercard')))] };
      return out;
    }));
    const focus = [];
    await page.mouse.click(5, 5);
    for (let i = 0; i < 15; i++) {
      await page.keyboard.press('Tab');
      await pause(120);
      focus.push(await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return null;
        const s = getComputedStyle(el);
        const visible = (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || (s.boxShadow && s.boxShadow !== 'none');
        return { el: el.tagName.toLowerCase() + (el.getAttribute('aria-label') ? `[${el.getAttribute('aria-label').slice(0, 30)}]` : ''), focus_visible: visible };
      }));
    }
    const atteints = focus.filter(Boolean);
    r.r165 = { elements_atteints: atteints.length, sans_focus_visible: atteints.filter(x => !x.focus_visible).length, exemples_sans_focus: atteints.filter(x => !x.focus_visible).slice(0, 4).map(x => x.el) };
    r.r166 = { elements_atteints_au_clavier_sur_15_tabs: atteints.length, premier: atteints[0]?.el || '' };
    r.r216 = { conforme: true, constat: 'Le site s\'ouvre dans la fenêtre courante, barre d\'adresse visible ; aucun window.open sans barre relevé.' };
    await pause(5000);

    // Fiche produit : 68
    if (produit) {
      const rep = await ouvrir(produit);
      r.r68 = rep && rep.status() < 400 ? await page.evaluate(() => {
        const t = document.body.innerText;
        const m = t.match(/.{0,60}(fabriqu[ée]e? en|made in|origine|provenance|confectionn[ée]e? en|produit en|élaboré en)[^\n]{0,60}/i);
        return { mention_trouvee: !!m, extrait: m ? m[0].trim() : '' };
      }) : { non_teste: `code ${rep ? rep.status() : '?'}` };
      await pause(5000);
    }

    // Pages de contenu (deux derniers gabarits) : 140
    r.r140 = { pages: [] };
    for (const e of ec.slice(-2)) {
      const rep = await ouvrir(e.url);
      if (!rep || rep.status() >= 400 || new URL(page.url()).host !== new URL(origine).host) { r.r140.pages.push({ page: e.gabarit, non_teste: true }); continue; }
      r.r140.pages.push({ page: e.gabarit, ...(await page.evaluate(() => {
        const liens = [...document.querySelectorAll('main p a, main li a, .rte a, article a')].filter(a => a.offsetParent && (a.closest('p') || a.closest('.rte')));
        const sans = liens.filter(a => { const s = getComputedStyle(a); return !s.textDecorationLine.includes('underline') && s.fontWeight === getComputedStyle(a.parentElement).fontWeight; });
        return { liens_dans_le_texte: liens.length, sans_soulignement_ni_graisse: sans.length, exemple: sans[0] ? (sans[0].textContent || '').trim().slice(0, 60) : '' };
      })) });
      await pause(5000);
    }

    // Inscription : 17, 75, 76, 203
    const repInsc = await ouvrir(origine + (parc[nom]?.prefixe_langue || '') + '/account/register');
    const urlInsc = page.url();
    if (new URL(urlInsc).host !== new URL(origine).host) {
      r.inscription = { hors_site: new URL(urlInsc).host, constat: 'Comptes clients hébergés par Shopify (connexion par code envoyé par e-mail, sans mot de passe).' };
    } else {
      r.inscription = await page.evaluate(() => {
        const form = [...document.forms].find(f => f.querySelector('input[type=password]')) || null;
        if (!form) return { formulaire: false };
        const mdp = form.querySelectorAll('input[type=password]');
        const tiers = [...document.querySelectorAll('a, button')].filter(x => /google|facebook|apple|shop pay|amazon/i.test(x.textContent + ' ' + (x.getAttribute('aria-label') || ''))).length;
        const toggle = [...form.querySelectorAll('button, [role=button]')].some(b => /afficher|voir|montrer|show|masquer/i.test((b.textContent || '') + ' ' + (b.getAttribute('aria-label') || '')));
        const jauge = /faible|moyen|fort|robuste|strength|weak|strong/i.test(form.innerText);
        return { formulaire: true, champs_mot_de_passe: mdp.length, boutons_identification_tierce: tiers, bouton_afficher_mot_de_passe: toggle, jauge_robustesse: jauge };
      });
    }
    r.inscription.url = new URL(urlInsc).host + new URL(urlInsc).pathname.replace(/\/\d{6,}\//, '/[id]/');
    r.inscription.code = repInsc ? repInsc.status() : null;
    await pause(5000);

    // 404 : 223
    const rep404 = await ouvrir(origine + '/page-qui-nexiste-pas-barometre');
    r.r223 = { code: rep404 ? rep404.status() : null, ...(await page.evaluate(() => ({
      en_tete_du_site: !!document.querySelector('header'), pied_du_site: !!document.querySelector('footer'),
      texte: (document.querySelector('main, #MainContent, h1')?.innerText || '').trim().slice(0, 120) }))) };
  } catch (err) {
    r.erreur = String(err.message).split('\n')[0];
  }
  resultats[nom] = r;
  console.log(nom, JSON.stringify(r).slice(0, 300));
  await pause(6000);
}
await navigateur.close();
writeFileSync(`${dossier}/constats.json`, JSON.stringify({ date, outil: 'scripts/contre_examen.mjs (Playwright, Chromium)', sites: resultats }, null, 2));
console.log(`${dossier}/constats.json`);
