// Relevé navigateur pour trancher les règles Opquast jusqu'ici écartées (lecture seule, aucune saisie, aucune commande).
//
// Par site : les écrans du baromètre, les pages légales et d'aide trouvées dans le pied de page (mentions légales,
// CGV, confidentialité, cookies, livraison, retours, FAQ, contact, accessibilité), une page 404, l'accueil laissé
// 12 secondes (popups), l'accueil et la fiche produit en mode impression, le panier avec un article (ajouté comme le
// bouton « Ajouter au panier », panier jetable), et des mesures sur le code et les styles.
// Les textes complets restent dans un dossier passé en argument (hors dépôt) ; le JSON garde des faits courts.
//
// Usage : node scripts/releve_regles.mjs <dossier des textes> [--service "Boutique A"]
// Sortie : resultats/releve-AAAA-MM-JJ/releve.json
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';

const RACINE = new URL('..', import.meta.url).pathname;
const TEXTES = process.argv[2];
const args = process.argv.slice(3);
const seul = args.includes('--service') ? args[args.indexOf('--service') + 1] : null;
const pause = ms => new Promise(ok => setTimeout(ok, ms));
const lignes = readFileSync(`${RACINE}scripts/ecrans_en_ligne.csv`, 'utf8').trim().split('\n').slice(1).map(l => {
  const [service, gabarit, ...u] = l.split(','); return { service, gabarit, url: u.join(',') };
}).filter(e => !seul || e.service === seul);
const date = new Date().toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/releve-${date}`;
mkdirSync(dossier, { recursive: true }); mkdirSync(TEXTES, { recursive: true });
const fichier = `${dossier}/releve.json`;
const res = existsSync(fichier) ? JSON.parse(readFileSync(fichier, 'utf8')) : {};
const sauver = () => writeFileSync(fichier, JSON.stringify(res, null, 1));
const LEGAL = /mentions|l[ée]gal|cgv|conditions|confidentialit|privacy|cookie|livraison|exp[ée]dition|shipping|retour|rembours|faq|questions|contact|accessibilit|plan du site|sitemap|aide|help|garantie|sav|service client/i;
const nav = await chromium.launch();

async function ouvrir(ctx, url, attente = 2500) {
  const p = await ctx.newPage();
  const rep = await p.goto(url, { waitUntil: 'load', timeout: 45000 });
  await pause(attente);
  return { p, rep };
}
async function refuserCookies(p) {
  for (const s of ['#onetrust-reject-all-handler', 'button:has-text("Tout refuser")', 'button:has-text("Refuser")', 'button:has-text("Continuer sans accepter")']) {
    const b = p.locator(s).first();
    if (await b.isVisible().catch(() => false)) { await b.click({ timeout: 3000 }).catch(() => {}); return true; }
  }
  return false;
}

// Mesures sur le code et les styles d'une page (règles 2, 14, 139, 141, 142, 144, 184, 188, 189, 192, 93, 94, 74, 231, 126)
const MESURES = () => {
  const txt = document.body.innerText;
  const liens = [...document.querySelectorAll('a[href]')];
  const ext = liens.filter(a => { try { const u = new URL(a.href); return /^https?:/.test(u.protocol) && u.hostname.replace(/^www\./, '') !== location.hostname.replace(/^www\./, '') && !/shopify|shop\.app/.test(u.hostname); } catch { return false; } });
  const extSignales = ext.filter(a => /externe|nouvelle fenêtre|new window|external/i.test((a.getAttribute('aria-label') || '') + (a.title || '') + a.innerText) || a.querySelector('svg[class*=external i], [class*=external i]'));
  // soulignement hors liens (139)
  let soulignesHorsLien = 0, exSouligne = '';
  for (const el of document.querySelectorAll('body *:not(a):not(a *)')) {
    if (!el.childNodes.length || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 2)) continue;
    const cs = getComputedStyle(el);
    if (cs.textDecorationLine.includes('underline') && cs.display !== 'none' && el.getBoundingClientRect().width > 0) { soulignesHorsLien++; exSouligne ||= el.textContent.trim().slice(0, 50); }
  }
  // :visited (141) et contenu généré (188)
  let visited = 0, avantTexte = [];
  for (const sh of [...document.styleSheets]) {
    let rules; try { rules = sh.cssRules; } catch { continue; }
    for (const r of rules || []) {
      const sel = r.selectorText || '';
      if (/:visited/.test(sel)) visited++;
      if (/::?(before|after)/.test(sel) && r.style && /^["'][^"']{3,}["']$/.test((r.style.content || '').trim())) avantTexte.push(`${sel.slice(0, 40)} ${r.style.content.slice(0, 30)}`);
    }
  }
  // pictogrammes typographiques (189)
  const pictos = [];
  const marche = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (marche.nextNode()) {
    const n = marche.currentNode, t = n.textContent;
    const m = t.match(/[★☆✓✔✗✘→←↑↓►▶◄♥❤✉☎✆⚠✱✳]/u);
    if (m && n.parentElement && !n.parentElement.closest('[aria-hidden="true"], script, style') && getComputedStyle(n.parentElement).display !== 'none') {
      const el = n.parentElement;
      const alt = el.closest('[aria-label], [role=img], [title]');
      pictos.push({ car: m[0], contexte: t.trim().slice(0, 40), alternative: !!alt });
    }
  }
  // majuscules écrites en dur (192) : mots de 4 lettres ou plus en capitales dans titres, boutons, liens de menu
  const capsDur = [];
  for (const el of document.querySelectorAll('h1, h2, h3, h4, button, nav a, .button, [class*=title]')) {
    const own = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' ').trim();
    if (/\b[A-ZÀÂÉÈÊËÎÏÔÛÙÇ]{4,}\b/.test(own) && !/^[A-Z0-9 &\-]{2,6}$/.test(own) && getComputedStyle(el).textTransform !== 'uppercase') capsDur.push(own.slice(0, 40));
  }
  // listes d'options (93, 94)
  const selects = [...document.querySelectorAll('select')].filter(s => s.options.length > 5).map(s => {
    const o = [...s.options].map(x => x.text.trim()).filter(Boolean);
    const tri = o.slice(1).every((v, i) => o[i].localeCompare(v, 'fr', { sensitivity: 'base' }) <= 0);
    const num = o.every(v => /^\d/.test(v)) && o.slice(1).every((v, i) => parseFloat(o[i]) <= parseFloat(v));
    return { nom: s.name || s.id, options: o.length, tri_alpha: tri, tri_num: num, optgroup: !!s.querySelector('optgroup'), exemples: o.slice(0, 4) };
  });
  // limites de caractères (74)
  const maxlength = [...document.querySelectorAll('input[maxlength], textarea[maxlength]')].filter(c => c.type !== 'hidden' && +c.maxLength > 0 && +c.maxLength < 200)
    .map(c => ({ nom: c.name, max: c.maxLength, signale: new RegExp(c.maxLength + '|caract', 'i').test((c.labels?.[0]?.innerText || '') + (c.getAttribute('aria-describedby') ? document.getElementById(c.getAttribute('aria-describedby'))?.innerText || '' : '') + (c.placeholder || '')) }));
  // dates (4, 6, 231)
  const times = [...document.querySelectorAll('time[datetime]')].map(t => t.getAttribute('datetime'));
  const metaDate = document.querySelector('meta[property="article:published_time"], meta[property="article:modified_time"], meta[itemprop=datePublished]')?.content || null;
  const ld = [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => s.textContent).join(' ');
  const datesTexte = (txt.match(/\b\d{1,2}[\/.-]\d{1,2}[\/.-]\d{2,4}\b|\b\d{1,2}(er)? (janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre) \d{4}\b/gi) || []).slice(0, 6);
  // carrousels et animations (126, 127)
  const auto = [...document.querySelectorAll('[data-autoplay="true"], [autoplay], [data-autoplay-speed], .swiper[data-autoplay], slideshow-component[data-autoplay="true"], [data-slider-autoplay="true"], marquee, [class*=marquee i], [class*=ticker i], [class*=announcement][data-autorotate="true"]')];
  const pauseBtn = !!document.querySelector('button[class*=pause i], button[aria-label*=pause i], button[aria-label*=Pause], .slideshow__autoplay');
  // désignation par la forme ou la position (184)
  const position = (txt.match(/(ci-dessous|ci-dessus|à droite|à gauche|en haut à|en bas à|bouton (rouge|vert|bleu|rond))[^.\n]{0,40}/gi) || []).slice(0, 4);
  // caractères détournés (14)
  const ascii = (txt.match(/(-{5,}|={5,}|\*{4,}|_{5,}|\.{6,})/g) || []).length;
  return {
    copyright: /©|copyright|tous droits réservés/i.test(document.querySelector('footer')?.innerText || txt.slice(-3000)),
    liens_externes: ext.length, liens_externes_signales: extSignales.length,
    mailto: [...document.querySelectorAll('a[href^="mailto:"]')].map(a => /@/.test(a.innerText) || /mail|écrire|contact/i.test(a.innerText + (a.getAttribute('aria-label') || ''))),
    soulignes_hors_lien: soulignesHorsLien, exemple_souligne: exSouligne, regles_visited: visited, contenus_generes_texte: avantTexte.slice(0, 5),
    pictos: pictos.slice(0, 12), caps_en_dur: capsDur.slice(0, 8), selects, maxlength,
    time_datetime: times.slice(0, 5), meta_date: metaDate, ld_date: /datePublished|dateModified/.test(ld), dates_texte: datesTexte,
    carrousels_auto: auto.length, bouton_pause: pauseBtn, designation_position: position, ascii_decoratif: ascii,
    nouveautes: !!document.querySelector('a[href*="nouveaut" i], a[href*="new" i]') || /nouveaut/i.test(txt),
    tableaux: [...document.querySelectorAll('table')].map(t => ({ th: t.querySelectorAll('th').length, lignes: t.rows.length, role: t.getAttribute('role') })),
    listes_simulees: [...document.querySelectorAll('p, div')].filter(el => /^\s*[-•·▪]\s/m.test(el.innerText || '') && el.children.length < 2 && (el.innerText.match(/\n\s*[-•·▪]\s/g) || []).length >= 2).length,
    images_texte: [...document.querySelectorAll('img[alt]')].filter(i => i.alt.split(' ').length >= 6 && i.naturalWidth > 600).map(i => i.alt.slice(0, 60)).slice(0, 5),
    langues: [...document.querySelectorAll('a[hreflang], link[rel=alternate][hreflang]')].map(a => a.getAttribute('hreflang')).filter((v, i, t) => t.indexOf(v) === i),
    lien_langue_textes: [...document.querySelectorAll('a[hreflang], [class*=locali] a, [class*=language] a, [class*=langue] a')].map(a => ({ texte: a.innerText.trim().slice(0, 20), lang: a.getAttribute('hreflang') || a.getAttribute('lang'), href: (a.getAttribute('href') || '').slice(0, 50) })).slice(0, 8),
  };
};

for (const nom of [...new Set(lignes.map(e => e.service))]) {
  if (res[nom]?.fini) continue;
  const s = (res[nom] = { pages: {}, legales: {} });
  const ecr = lignes.filter(e => e.service === nom);
  const accueil = ecr.find(e => e.gabarit.startsWith('Accueil')).url;
  const produit = ecr.find(e => e.gabarit === 'Produit').url;
  const ctx = await nav.newContext({ viewport: { width: 1366, height: 900 }, locale: 'fr-FR' });
  try {
    // 1. accueil laissé 12 s : popups (154, 160 à 163), refus des cookies ensuite
    const { p } = await ouvrir(ctx, accueil, 12000);
    s.popup = await p.evaluate(() => {
      const cand = [...document.querySelectorAll('body *')].filter(el => {
        const cs = getComputedStyle(el); const b = el.getBoundingClientRect();
        return (cs.position === 'fixed' || cs.position === 'absolute') && +cs.zIndex > 100 && b.width > 280 && b.height > 160 && cs.display !== 'none' && cs.visibility !== 'hidden' && +cs.opacity > 0.1;
      }).filter(el => !/cookie|consent|onetrust|didomi|axeptio|cmp|privacy/i.test(el.id + ' ' + el.className + ' ' + el.innerText.slice(0, 200)));
      const pop = cand.find(el => el.querySelector('input[type=email], form')) || cand.find(el => /newsletter|inscri|offert|-\d+ ?%|code/i.test(el.innerText));
      if (!pop) return { presente: false };
      const fermer = [...pop.querySelectorAll('button, [role=button], a')].find(b => /fermer|close|×|✕|non merci|plus tard/i.test(b.innerText + ' ' + (b.getAttribute('aria-label') || '')));
      const bp = pop.getBoundingClientRect(), bf = fermer?.getBoundingClientRect();
      return { presente: true, texte: pop.innerText.trim().slice(0, 160), bouton_fermer: !!fermer, libelle_fermer: fermer ? (fermer.getAttribute('aria-label') || fermer.innerText).trim().slice(0, 30) : null,
        fermer_dans_la_popup: !!(bf && bf.left >= bp.left - 40 && bf.right <= bp.right + 40 && bf.top >= bp.top - 40 && bf.bottom <= bp.bottom + 40),
        frequence_annoncee: /par (semaine|mois)|\d+ (e-?mails?|fois)|hebdo|mensuel/i.test(pop.innerText) };
    });
    await refuserCookies(p); await pause(800);
    s.bandeau_cookies = await p.evaluate(() => {
      const t = document.body.innerText;
      return { finalites_expliquees: /mesure d'audience|statistique|publicit|personnalis|réseaux sociaux|marketing/i.test(t.slice(0, 200000)) };
    });
    // liens du pied de page vers les pages légales et d'aide
    const liensPied = await p.evaluate(re => {
      const r = new RegExp(re, 'i');
      const zone = document.querySelector('footer') || document.body;
      return [...new Map([...zone.querySelectorAll('a[href]')].filter(a => r.test(a.innerText + ' ' + a.getAttribute('href')) && a.href.startsWith(location.origin))
        .map(a => [a.href.split('#')[0], a.innerText.trim().slice(0, 50)])).entries()].slice(0, 14);
    }, LEGAL.source);
    s.pied_de_page = (await p.evaluate(() => { const f = document.querySelector('footer'); return f ? f.innerText.replace(/\s+/g, ' ').slice(0, 1500) : ''; }))
      .replace(/[\w.+-]+@[\w.-]*/g, '[adresse masquée]').replace(/(\+33 ?|0)[1-9](?:[ .-]?\d{2}){4}/g, '[téléphone masqué]');  // pas de coordonnées dans le dépôt
    s.mesures_accueil = await p.evaluate(MESURES);
    // impression (196) : accueil
    await p.emulateMedia({ media: 'print' });
    s.impression_accueil = await p.evaluate(() => {
      const vis = el => el && getComputedStyle(el).display !== 'none' && getComputedStyle(el).visibility !== 'hidden' && el.getBoundingClientRect().height > 0;
      return { entete_visible: vis(document.querySelector('header, .header, #shopify-section-header, [class*=header]')), nav_visible: vis(document.querySelector('nav, [role=navigation]')),
        pied_visible: vis(document.querySelector('footer')) };
    });
    await p.close();

    // 2. pages légales et d'aide
    for (const [url, lib] of liensPied) {
      try {
        const { p: q, rep } = await ouvrir(ctx, url, 1500);
        const t = await q.evaluate(() => (document.querySelector('main') || document.body).innerText.replace(/[ \t]+/g, ' '));
        const f = `${TEXTES}/${nom.replace(/\W+/g, '_')}__${url.split('/').pop().slice(0, 40).replace(/\W+/g, '_') || 'index'}.txt`;
        writeFileSync(f, `${url}\n${lib}\n\n${t}`);
        s.legales[url] = { libelle: lib, statut: rep?.status(), caracteres: t.length, fichier: f };
        await q.close();
      } catch (err) { s.legales[url] = { libelle: lib, erreur: String(err.message).slice(0, 80) }; }
      await pause(3500);
    }

    // 3. page 404 (225)
    {
      const { p: q, rep } = await ouvrir(ctx, new URL('/page-qui-n-existe-pas-opquast', accueil).href, 1500);
      s.page_404 = await q.evaluate(() => ({ menu: !!document.querySelector('header nav a, nav[role] a, header a[href="/collections/all"], header [class*=menu] a'), liens_entete: document.querySelectorAll('header a').length }));
      s.page_404.code = rep?.status();
      await q.close(); await pause(3000);
    }

    // 4. fiche produit : informations commerciales et impression
    {
      const { p: q } = await ouvrir(ctx, produit, 3000);
      await refuserCookies(q);
      s.produit = await q.evaluate(() => {
        const t = (document.querySelector('main') || document.body).innerText;
        return {
          prix: (t.match(/\d+[,.]\d{2}\s?€|€\s?\d+[,.]\d{2}/) || [''])[0], ttc: /TTC|toutes taxes|taxes incluses|TVA incluse|taxes comprises|tax included/i.test(t),
          caracteristiques: /contenance|poids|\d+\s?(g|kg|ml|cl|l|cm|mm)\b|composition|matière|dimensions|taille|ingrédients/i.test(t),
          disponibilite: /en stock|disponible|rupture|épuisé|plus que \d|derni(er|ère)s? (article|pièce)|sold out|out of stock/i.test(t),
          delai_livraison: /livr(é|aison) (en|sous|entre|d'ici)|\d+ ?(à|-) ?\d+ jours|jours ouvr|expédi(é|tion) (sous|en|le)/i.test(t),
          frais_livraison: /livraison (offerte|gratuite)|frais de (port|livraison)|dès \d+ ?€/i.test(t),
          promo: /-\d+ ?%|promo|soldes|offre|prix barré/i.test(t), promo_dates: /jusqu'(au|à)|valable|du \d+ au \d+|fin le|se termine/i.test(t),
          financement: /alma|klarna|oney|scalapay|\d+x sans frais|en \d+ fois/i.test(t),
          labels: [...document.querySelectorAll('img[alt]')].map(i => i.alt).filter(a => /label|certifi|bio|garanti|ecocert|cosmos|oeko|origine france|vegan|récompens|élu/i.test(a)).slice(0, 5),
          garantie: /garantie|garanti \d/i.test(t),
          video: [...document.querySelectorAll('video')].map(v => ({ controles: v.controls, duree: isFinite(v.duration) ? Math.round(v.duration) : null })),
        };
      });
      s.mesures_produit = await q.evaluate(MESURES);
      s.epuise = await q.evaluate(() => {
        const o = [...document.querySelectorAll('option[disabled], input[disabled] + label, [class*=sold-out i], [class*=soldout i], .disabled')];
        return { variantes_indisponibles: o.length, texte: o.slice(0, 3).map(x => (x.innerText || x.textContent || '').trim().slice(0, 30)) };
      });
      await q.emulateMedia({ media: 'print' });
      s.impression_produit = await q.evaluate(() => { const vis = el => el && getComputedStyle(el).display !== 'none' && el.getBoundingClientRect().height > 0; return { entete_visible: vis(document.querySelector('header, .header, #shopify-section-header')), nav_visible: vis(document.querySelector('nav')) }; });
      // ajout au panier comme le bouton, puis page panier (31, 32, 36, 38, 41)
      await q.emulateMedia({ media: 'screen' });
      const ajout = await q.evaluate(async () => {
        const racine = (window.Shopify && Shopify.routes && Shopify.routes.root) || '/';
        try { const p = await (await fetch(location.pathname.replace(/\/$/, '') + '.js')).json(); const v = p.variants.find(x => x.available) || p.variants[0];
          return (await fetch(racine + 'cart/add.js', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items: [{ id: v.id, quantity: 1 }] }) })).ok; } catch { return false; }
      });
      await q.close();
      if (ajout) {
        const { p: c } = await ouvrir(ctx, accueil.replace(/\/$/, '') + '/cart', 2500);
        s.panier = await c.evaluate(async () => {
          const t = (document.querySelector('main') || document.body).innerText;
          const racine = (window.Shopify && Shopify.routes && Shopify.routes.root) || '/';
          let cart = { item_count: null, items: [] };
          try { cart = await (await fetch(racine + 'cart.js')).json(); } catch {}
          return { articles_dans_panier: cart.item_count, lignes: cart.items.length, ajouts_non_demandes: cart.items.length > 1,
            lien_vers_article: !!document.querySelector('main a[href*="/products/"]'), quantite_modifiable: !!document.querySelector('main input[name*="updates" i], main input[type=number], main button[name=plus], main quantity-input, main [class*=quantity] button'),
            suppression: !!document.querySelector('main a[href*="change"][href*="quantity=0"], main cart-remove-button, main [class*=remove], main button[aria-label*=Supprimer i], main a[aria-label*=Supprimer i]'),
            sous_total: /sous-total|total/i.test(t), frais_livraison: /livraison|frais de port|expédition/i.test(t), taxes: /taxes|TTC|TVA/i.test(t), delai: /\d+ ?(à|-) ?\d+ jours|jours ouvr|livr(é|aison) (en|sous)/i.test(t) };
        });
        await c.close();
      }
    }
    // 5. mesures sur chaque écran du baromètre (blog, collection…) : dates et styles
    for (const e of ecr.filter(x => !/^(Accueil|Produit|Compte|Panier)/.test(x.gabarit))) {
      try { const { p: q } = await ouvrir(ctx, e.url, 2000); s.pages[e.url] = { gabarit: e.gabarit, ...(await q.evaluate(MESURES)) }; await q.close(); }
      catch (err) { s.pages[e.url] = { gabarit: e.gabarit, erreur: String(err.message).slice(0, 80) }; }
      await pause(3500);
    }
    s.fini = true;
  } catch (err) { s.erreur = String(err.message).split('\n')[0].slice(0, 160); }
  await ctx.close();
  console.log(nom, s.erreur || `légales ${Object.keys(s.legales).length}, popup ${s.popup?.presente}, 404 menu ${s.page_404?.menu}, panier ${s.panier ? 'ok' : '-'}`);
  sauver(); await pause(5000);
}
await nav.close();
console.log(fichier);
