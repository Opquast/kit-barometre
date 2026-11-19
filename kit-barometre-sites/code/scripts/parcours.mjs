// Parcours réels sans commande ni saisie de données personnelles (Playwright, Chromium).
//
// Pour chaque site :
// - 30, 58, 87 : ajout d'un produit au panier (comme le bouton « Ajouter au panier »), ouverture du paiement Shopify,
//   puis relevé de la page : commande possible sans compte, moyens de paiement affichés, liste des étapes. On s'arrête
//   là : aucun champ rempli, aucune commande. Le panier vit dans un contexte de navigateur jetable.
// - 79, 80 : sur le formulaire newsletter de l'accueil, une adresse invalide (« test@ ») est saisie puis la validation
//   du navigateur est interrogée (checkValidity) SANS envoyer le formulaire : on relève si le champ fautif est signalé
//   et le message affiché.
// - 166 : accueil puis fiche produit au clavier seul : tabulations, Entrée sur « Ajouter au panier », Échap.
// - 165 : capture des 6 premiers éléments atteints au clavier, pour vérifier à l'œil que le focus se voit.
//
// Usage : node scripts/parcours.mjs [--service "Boutique A"]
// Sorties : resultats/parcours-AAAA-MM-JJ/parcours.json ; captures dans le dossier passé par --captures (hors dépôt).
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

const RACINE = new URL('..', import.meta.url).pathname;
const args = process.argv.slice(2);
const opt = n => (args.includes(n) ? args[args.indexOf(n) + 1] : null);
const seul = opt('--service');
const captures = opt('--captures');
const pause = ms => new Promise(ok => setTimeout(ok, ms));

const lignes = readFileSync(`${RACINE}scripts/ecrans_en_ligne.csv`, 'utf8').trim().split('\n').slice(1).map(l => {
  const [service, gabarit, ...u] = l.split(',');
  return { service, gabarit, url: u.join(',') };
});
const sites = [...new Set(lignes.map(l => l.service))].filter(s => !seul || s === seul);
const date = new Date().toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/parcours-${date}`;
mkdirSync(dossier, { recursive: true });
if (captures) mkdirSync(captures, { recursive: true });
const res = {};
const navigateur = await chromium.launch();

async function fermerPopups(page) {
  await page.keyboard.press('Escape').catch(() => {});
  for (const s of ['#onetrust-reject-all-handler', 'button:has-text("Refuser")', 'button:has-text("Tout refuser")', 'button:has-text("Continuer sans accepter")']) {
    const b = page.locator(s).first();
    if (await b.isVisible().catch(() => false)) { await b.click({ timeout: 3000 }).catch(() => {}); break; }
  }
}

for (const nom of sites) {
  const accueil = lignes.find(l => l.service === nom && l.gabarit.startsWith('Accueil')).url;
  const produit = lignes.find(l => l.service === nom && l.gabarit === 'Produit').url;
  const r = (res[nom] = {});
  const ctx = await navigateur.newContext({ viewport: { width: 1366, height: 900 }, locale: 'fr-FR' });
  const page = await ctx.newPage();
  try {
    // 165 et 166 sur l'accueil
    await page.goto(accueil, { waitUntil: 'load', timeout: 45000 });
    await pause(4000);
    await fermerPopups(page);
    await pause(800);
    const tabs = [];
    for (let i = 0; i < 25; i++) {
      await page.keyboard.press('Tab');
      await pause(120);
      const f = await page.evaluate(() => {
        const a = document.activeElement;
        if (!a || a === document.body) return null;
        const b = a.getBoundingClientRect();
        const cs = getComputedStyle(a);
        return { tag: a.tagName.toLowerCase(), texte: (a.innerText || a.getAttribute('aria-label') || a.value || '').trim().slice(0, 40),
          visible: b.width > 0 && b.height > 0 && b.bottom > 0 && b.top < innerHeight + 2000, outline: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0,
          ombre: cs.boxShadow !== 'none', zone: [Math.max(0, b.x - 8), Math.max(0, b.y - 8), b.width + 16, b.height + 16] };
      });
      tabs.push(f);
      if (captures && f && f.visible && i < 6 && f.zone[2] > 4) {
        await page.screenshot({ path: `${captures}/${nom.replace(/\W+/g, '_')}_focus_${i + 1}.png`, clip: { x: f.zone[0], y: f.zone[1], width: Math.min(f.zone[2], 600), height: Math.min(f.zone[3], 200) } }).catch(() => {});
      }
    }
    const atteints = tabs.filter(Boolean);
    r.clavier_accueil = { tabulations: 25, elements_atteints: atteints.length, invisibles: atteints.filter(t => !t.visible).length,
      sans_indicateur: atteints.filter(t => t.visible && !t.outline && !t.ombre).length, premiers: atteints.slice(0, 8).map(t => `${t.tag} « ${t.texte} »`) };

    // 79, 80 : validation du formulaire newsletter sans envoi
    r.formulaire = await page.evaluate(() => {
      const champ = [...document.querySelectorAll('footer input[type=email], input[type=email]')].find(x => x.offsetParent !== null) || document.querySelector('input[type=email]');
      if (!champ) return { trouve: false };
      champ.value = 'test@';
      const ok = champ.form ? champ.form.checkValidity() : champ.checkValidity();
      return { trouve: true, valide: ok, message_navigateur: champ.validationMessage, type: champ.type, requis: champ.required,
        message_propre_au_site: !!(champ.form && champ.form.noValidate), aria_invalid: champ.getAttribute('aria-invalid') };
    });

    // 166 : fiche produit au clavier
    await page.goto(produit, { waitUntil: 'load', timeout: 45000 });
    await pause(3000);
    await fermerPopups(page);
    let trouve = -1;
    for (let i = 0; i < 400; i++) {  // 400 : certains méga-menus font passer près de 300 liens avant le bouton
      await page.keyboard.press('Tab');
      const t = await page.evaluate(() => { const a = document.activeElement; if (!a) return ''; if (a.closest('form[action*="/cart/add"]') && (a.type === 'submit' || a.name === 'add')) return 'ajouter au panier'; return ((a.innerText || a.value || a.getAttribute('aria-label') || '') + ' ' + (a.name || '')).toLowerCase(); });
      if (/ajouter au panier|add to cart|ajouter|précommander|add$/.test(t.trim())) { trouve = i + 1; break; }
    }
    let ajoute = false;
    if (trouve > 0) {
      await page.keyboard.press('Enter');
      await pause(3000);
      ajoute = await page.evaluate(async () => (await (await fetch('/cart.js')).json()).item_count > 0).catch(() => false);
      await page.keyboard.press('Escape');
    }
    r.clavier_produit = { bouton_panier_atteint_en_tabulations: trouve > 0 ? trouve : null, ajout_au_clavier: ajoute };

    // ajout de secours (comme le bouton) si le clavier n'a pas suffi, pour atteindre le paiement
    if (!ajoute) {
      ajoute = await page.evaluate(async () => {
        const p = await (await fetch(location.pathname.replace(/\/$/, '') + '.js')).json();
        const v = p.variants.find(x => x.available) || p.variants[0];
        const rep = await fetch('/cart/add.js', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items: [{ id: v.id, quantity: 1 }] }) });
        return rep.ok;
      }).catch(() => false);
    }

    // 30, 58, 87 : page de paiement, relevé seul
    if (ajoute) {
      await page.goto(new URL('/checkout', accueil).href, { waitUntil: 'load', timeout: 60000 });
      await pause(7000);
      const u = new URL(page.url());
      r.paiement = await page.evaluate(() => {
        const txt = document.body.innerText;
        const imgs = [...document.querySelectorAll('img[alt], svg[aria-label], [aria-label]')].map(x => x.getAttribute('alt') || x.getAttribute('aria-label') || '');
        const moyens = ['Visa', 'Mastercard', 'American Express', 'Amex', 'PayPal', 'Apple Pay', 'Google Pay', 'Shop Pay', 'Klarna', 'Alma', 'Oney', 'Scalapay', 'Carte bancaire', 'Cartes bancaires', 'Bancontact', 'Maestro', 'Cartes Bancaires', 'Union Pay', 'Meta Pay']
          .filter(m => txt.includes(m) || imgs.some(a => a.toLowerCase().includes(m.toLowerCase())));
        const fil = [...document.querySelectorAll('nav[aria-label] ol li, nav ol li')].map(x => x.innerText.trim()).filter(Boolean).slice(0, 8);
        return {
          champ_email_ou_tel: !!document.querySelector('input[type=email], input[name=email], input[autocomplete=email], input#email'),
          connexion_obligatoire: /connectez-vous pour (continuer|commander)|log in to (continue|check out)/i.test(txt),
          lien_connexion_facultatif: /se connecter|connexion|log in|sign in/i.test(txt),
          moyens_paiement: [...new Map(moyens.map(m => [m.toLowerCase().replace('amex', 'american express'), m])).values()], paiement_express: /paiement express|express checkout/i.test(txt),
          etapes: fil, titre: document.title,
          cases_precochees: [...document.querySelectorAll('input[type=checkbox]')].filter(c => c.checked).map(c => ((c.labels && c.labels[0] && c.labels[0].innerText) || c.getAttribute('aria-label') || c.name || '').trim().slice(0, 90)),
          verification_humaine: /captcha|vérifi(ez|cation) que vous|are you human/i.test(txt),
        };
      });
      r.paiement.url = `${u.hostname}${u.pathname.replace(/\/(cn|c)\/[^/]+/, '/$1/…').replace(/[A-Za-z0-9]{20,}/g, '…')}`;
      if (captures) await page.screenshot({ path: `${captures}/${nom.replace(/\W+/g, '_')}_paiement.png`, fullPage: false }).catch(() => {});
    } else r.paiement = { non_teste: 'ajout au panier impossible' };
  } catch (err) { r.erreur = String(err.message).split('\n')[0]; }
  await ctx.close();
  console.log(nom, JSON.stringify(r).slice(0, 600));
  writeFileSync(`${dossier}/parcours.json`, JSON.stringify(res, null, 1));
  await pause(5000);
}
await navigateur.close();
