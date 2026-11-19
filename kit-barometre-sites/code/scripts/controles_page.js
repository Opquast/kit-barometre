// Contrôles déterministes des règles Opquast V5 qui se vérifient en lisant le code d'une page rendue.
//
// À exécuter dans le navigateur, sur la page à contrôler (console des outils de développement,
// ou par l'agent dans le navigateur intégré). Lecture seule : rien n'est cliqué, rien n'est envoyé,
// sauf des requêtes HEAD vers les liens internes de la page (règle 152, 30 liens au plus).
// Même page, même résultat : aucune IA. Les règles de contraste et d'ARIA (182, 185, 244) viennent
// d'axe-core (scripts/axe_navigateur.js), pas de ce script.
//
// Renvoie { url, date, version, resultats: { "<n° de règle>": [statut, détail] } }
// Statuts : conforme, non-conforme, non-applicable, non-testé.
(async () => {
  const VERSION = '0.2.0';  // 12/11 : 69 et 136 sur tous les éléments (popups, tiroirs), 232 avec la position en octets
  const R = {};
  const C = 'conforme', NC = 'non-conforme', NA = 'non-applicable', NT = 'non-testé';
  const set = (n, statut, detail) => { R[n] = [statut, detail]; };
  const visible = el => { const s = getComputedStyle(el); const b = el.getBoundingClientRect(); return s.display !== 'none' && s.visibility !== 'hidden' && b.width > 0 && b.height > 0; };
  const nomAccessible = el => (el.getAttribute('aria-label') || '').trim()
    || (el.getAttribute('aria-labelledby') || '').split(/\s+/).map(id => (document.getElementById(id)?.textContent || '').trim()).join(' ').trim()
    || (el.textContent || '').trim() || [...el.querySelectorAll('img[alt]')].map(i => i.alt.trim()).join(' ')
    || [...el.querySelectorAll('svg title, svg[aria-label]')].map(t => (t.textContent || t.getAttribute('aria-label') || '').trim()).join(' ')
    || (el.getAttribute('title') || '').trim();
  const masqueLecteur = el => !!el.closest('[aria-hidden="true"], [inert]');
  const liens = [...document.querySelectorAll('a[href]')];
  const textes = liens.map(a => ((a.textContent || '') + ' ' + (a.getAttribute('aria-label') || '') + ' ' + a.getAttribute('href')).toLowerCase());
  const lienVers = re => liens.some((a, i) => re.test(textes[i]));
  const corps = document.body.innerText;
  const surPageRecherche = /\/search/.test(location.pathname);
  const accueil = location.pathname === '/' || /^\/[a-z]{2}\/?$/.test(location.pathname);

  // 3 : métadonnée de description
  const desc = document.querySelector('meta[name="description"]')?.content?.trim();
  set(3, desc ? C : NC, desc ? `meta description : ${desc.length} caractères` : 'Aucune meta description');
  // 13 : nombre de résultats sur la page de recherche
  if (surPageRecherche) set(13, /\d+\s*(résultat|result|produit|article)/i.test(corps) ? C : NC, 'Nombre de résultats cherché dans le texte de la page');
  else set(13, NA, 'Pas une page de résultats de recherche');
  // 15 : lien vers la politique de confidentialité
  set(15, lienVers(/confidentialit|privacy|données personnelles|vie privée/) ? C : NC, 'Lien vers la politique de confidentialité cherché dans la page');
  // 27 et 28 : formulaires sensibles en HTTPS, rien de sensible en GET
  const formulaires = [...document.forms];
  const sensibles = formulaires.filter(f => f.querySelector('input[type=password], input[autocomplete^="cc-"], input[name*="card" i]'));
  if (!sensibles.length) { set(27, NA, 'Aucun champ sensible (mot de passe, carte) sur la page'); set(28, NA, 'Aucun champ sensible sur la page'); }
  else {
    const http = sensibles.filter(f => (f.action || location.href).startsWith('http:'));
    set(27, http.length ? NC : C, `${sensibles.length} formulaire(s) sensible(s), ${http.length} envoyé(s) en HTTP`);
    const get = sensibles.filter(f => (f.getAttribute('method') || 'get').toLowerCase() === 'get');
    set(28, get.length ? NC : C, `${get.length} formulaire(s) sensible(s) en méthode GET (données dans l'URL)`);
  }
  // 46 : conditions de vente depuis la page
  set(46, lienVers(/cgv|conditions g[ée]n[ée]rales|conditions de vente|terms|conditions d.utilisation/) ? C : NC, 'Lien vers les conditions générales cherché dans la page');
  // 69 : chaque champ a une étiquette propre
  // tous les champs, y compris ceux des popups et tiroirs fermés au chargement (faux négatif relevé le 12/11)
  const champs = [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=image]):not([type=reset]), select, textarea')]
    .filter(c => !c.disabled && !masqueLecteur(c) && c.tabIndex !== -1);
  const etiquette = c => (c.labels && [...c.labels].some(l => l.textContent.trim())) || (c.getAttribute('aria-label') || '').trim() || c.getAttribute('aria-labelledby') || (c.getAttribute('title') || '').trim();
  const sansEtiquette = champs.filter(c => !etiquette(c));
  const ex69 = sansEtiquette.slice(0, 3).map(c => `${c.tagName.toLowerCase()}${c.name ? '[name=' + c.name + ']' : ''}${visible(c) ? '' : ' (masqué au chargement)'}`).join(', ');
  set(69, !champs.length ? NA : (sansEtiquette.length ? NC : C), `${champs.length} champ(s), dont ${champs.filter(c => !visible(c)).length} masqué(s) au chargement ; ${sansEtiquette.length} sans étiquette` + (ex69 ? ` (${ex69})` : ''));
  // 92 : copier-coller non bloqué dans les champs
  const collerBloque = champs.filter(c => c.hasAttribute('onpaste') || c.hasAttribute('oncopy'));
  set(92, !champs.length ? NA : (collerBloque.length ? NC : C), `${collerBloque.length} champ(s) avec onpaste ou oncopy`);
  // 95 : types de champs adaptés (e-mail, téléphone, recherche…)
  const mauvaisType = champs.filter(c => c.type === 'text' && /mail|phone|tel|search|url|zip|postal/i.test((c.name || '') + (c.id || '') + (c.getAttribute('autocomplete') || '')));
  set(95, !champs.length ? NA : (mauvaisType.length ? NC : C), `${mauvaisType.length} champ(s) e-mail, téléphone ou recherche déclarés en type text`);
  // 97 : autocomplétion signalée sur les champs personnels
  const perso = champs.filter(c => /mail|phone|tel|name|nom|prenom|address|adresse|zip|postal|city|ville/i.test((c.name || '') + (c.id || '')) || ['email', 'tel'].includes(c.type));
  const sansAuto = perso.filter(c => !c.getAttribute('autocomplete'));
  set(97, !perso.length ? NA : (sansAuto.length ? NC : C), `${perso.length} champ(s) personnel(s), ${sansAuto.length} sans attribut autocomplete`);
  // 98 : boutons désactivés non masqués aux lecteurs d'écran
  const desactives = [...document.querySelectorAll('button[disabled], [aria-disabled="true"]')];
  const masques = desactives.filter(b => b.closest('[aria-hidden="true"]'));
  set(98, !desactives.length ? NA : (masques.length ? NC : C), `${desactives.length} bouton(s) désactivé(s), ${masques.length} masqué(s) aux lecteurs d'écran`);
  // 102 : le titre identifie le site
  const site = (document.querySelector('meta[property="og:site_name"]')?.content || location.hostname.replace(/^www\./, '').split('.')[0]).toLowerCase().replace(/[^a-z0-9]/g, '');
  const titre = document.title.toLowerCase().replace(/[^a-z0-9]/g, '');
  set(102, titre.includes(site.slice(0, 8)) ? C : NC, `Titre : « ${document.title} »`);
  // 104 : icône de favori
  set(104, document.querySelector('link[rel~="icon"]') ? C : NC, 'Balise link rel="icon" cherchée');
  // 105 et 107 : coordonnées et moyens de contact
  const tel = /(\+33|0)[1-9]([ .-]?\d{2}){4}/.test(corps);
  const mail = liens.some(a => a.href.startsWith('mailto:')) || /[\w.-]+@[\w-]+\.[a-z]{2,}/i.test(corps);
  const contact = lienVers(/contact/);
  set(105, tel ? C : NC, tel ? 'Numéro de téléphone présent dans la page' : 'Aucun numéro de téléphone dans la page');
  set(107, [tel, mail, contact].filter(Boolean).length >= 2 ? C : NC, `Moyens de contact trouvés : téléphone ${tel ? 'oui' : 'non'}, e-mail ${mail ? 'oui' : 'non'}, page contact ${contact ? 'oui' : 'non'}`);
  // 116 : chaque image a un attribut alt (pertinence : règles 117 et 118, par l'IA)
  const imgs = [...document.querySelectorAll('img')];
  const sansAlt = imgs.filter(i => !i.hasAttribute('alt') && i.getAttribute('role') !== 'presentation' && !i.closest('[aria-hidden="true"]'));
  set(116, !imgs.length ? NA : (sansAlt.length ? NC : C), `${imgs.length} image(s), ${sansAlt.length} sans attribut alt`);
  // 119 : vignettes pas redimensionnées côté client (image chargée au moins 3 fois plus large qu'affichée)
  const tropGrandes = imgs.filter(i => i.complete && i.naturalWidth && i.clientWidth && i.naturalWidth > 3 * i.clientWidth * (window.devicePixelRatio || 1));
  set(119, !imgs.length ? NA : (tropGrandes.length ? NC : C), `${tropGrandes.length} image(s) chargée(s) plus de 3 fois plus large(s) qu'affichée(s)`);
  // 120 : objets inclus (iframe) avec un titre
  const iframes = [...document.querySelectorAll('iframe')].filter(visible);
  const sansTitre = iframes.filter(f => !(f.title || f.getAttribute('aria-label') || '').trim());
  set(120, !iframes.length ? NA : (sansTitre.length ? NC : C), `${iframes.length} iframe(s) visible(s), ${sansTitre.length} sans titre`);
  // 121, 122, 124, 125 : vidéos et sons
  const videos = [...document.querySelectorAll('video, iframe[src*="youtube"], iframe[src*="vimeo"]')];
  const audios = [...document.querySelectorAll('audio')];
  set(121, !videos.length && !audios.length ? NA : NT, videos.length + audios.length ? 'Média présent : transcription à vérifier à la main' : 'Aucun média audio ou vidéo');
  // Les vidéos décoratives (lecture automatique, en boucle, sans commandes) n'ont pas de son à sous-titrer.
  const sansSousTitres = [...document.querySelectorAll('video')].filter(v => !(v.autoplay && v.loop && !v.controls) && !v.querySelector('track[kind="captions"], track[kind="subtitles"]'));
  set(122, !videos.length ? NA : (sansSousTitres.length ? NC : NT), `${videos.length} vidéo(s), ${sansSousTitres.length} avec son et sans piste de sous-titres`);
  const autoVideo = [...document.querySelectorAll('video[autoplay]')].filter(v => !v.muted);
  set(124, !videos.length ? NA : (autoVideo.length ? NC : C), `${autoVideo.length} vidéo(s) lancée(s) automatiquement avec le son`);
  set(125, !audios.length && !document.querySelector('video[autoplay]:not([muted])') ? (audios.length ? C : NA) : NC, `${document.querySelectorAll('audio[autoplay]').length} son(s) en lecture automatique`);
  // 128 : indicatif international sur les liens téléphone
  const telLiens = liens.filter(a => a.href.startsWith('tel:'));
  const sansIndicatif = telLiens.filter(a => !a.getAttribute('href').replace('tel:', '').trim().startsWith('+'));
  set(128, !telLiens.length ? (tel ? NC : NA) : (sansIndicatif.length ? NC : C), `${telLiens.length} lien(s) tel:, ${sansIndicatif.length} sans indicatif international`);
  // 130 : langue de la page
  set(130, document.documentElement.lang ? C : NC, `lang="${document.documentElement.lang || ''}"`);
  // 136 : chaque lien a un intitulé
  // tous les liens exposés aux lecteurs d'écran, y compris ceux des menus et tiroirs fermés (faux négatif relevé le 12/11)
  const liensVides = liens.filter(a => !masqueLecteur(a)).filter(a => !nomAccessible(a));
  const ex136 = liensVides.slice(0, 3).map(a => (a.getAttribute('href') || '').slice(0, 40) + (visible(a) ? '' : ' (masqué)')).join(', ');
  set(136, liensVides.length ? NC : C, `${liensVides.length} lien(s) sans intitulé sur ${liens.length}` + (ex136 ? ` (${ex136})` : ''));
  // 145 : numéros de téléphone activables
  set(145, !tel ? NA : (telLiens.length ? C : NC), `${telLiens.length} lien(s) tel: pour un numéro présent dans la page`);
  // 146 : ouverture de nouvelle fenêtre annoncée
  const blank = liens.filter(a => a.target === '_blank').filter(visible);
  const nonAnnonce = blank.filter(a => !/nouvel|new window|new tab|nouvelle fen|onglet/i.test(nomAccessible(a) + ' ' + (a.title || '')));
  set(146, !blank.length ? NA : (nonAnnonce.length ? NC : C), `${blank.length} lien(s) en nouvelle fenêtre, ${nonAnnonce.length} sans avertissement`);
  // 147 et 148 : format et poids des fichiers en téléchargement
  const fichiers = liens.filter(a => /\.(pdf|docx?|xlsx?|pptx?|zip|odt)(\?|$)/i.test(a.href));
  const sansFormat = fichiers.filter(a => !/pdf|doc|xls|ppt|zip|odt/i.test(nomAccessible(a)));
  const sansPoids = fichiers.filter(a => !/\d+\s*(ko|mo|kb|mb|go)/i.test(nomAccessible(a) + ' ' + (a.title || '')));
  set(147, !fichiers.length ? NA : (sansFormat.length ? NC : C), `${fichiers.length} fichier(s), ${sansFormat.length} sans format indiqué`);
  set(148, !fichiers.length ? NA : (sansPoids.length ? NC : C), `${fichiers.length} fichier(s), ${sansPoids.length} sans poids indiqué`);
  set(240, !fichiers.some(a => /\.pdf/i.test(a.href)) ? NA : NT, 'PDF présents : sélection du texte à vérifier à la main');
  // 152 : liens internes valides (HEAD sur 30 liens internes au plus)
  const internes = [...new Set(liens.map(a => a.href).filter(h => h.startsWith(location.origin) && !h.includes('#')))].slice(0, 30);
  const casses = [];
  for (const h of internes) {
    try { const r = await fetch(h, { method: 'HEAD', redirect: 'follow' }); if (r.status >= 400 && r.status !== 429) casses.push(`${r.status} ${h}`); } catch (e) { /* réseau : ignoré */ }
  }
  set(152, casses.length ? NC : C, `${internes.length} lien(s) interne(s) testé(s), ${casses.length} cassé(s) ${casses.slice(0, 3).join(' ; ')}`);
  // 155 : retour à l'accueil
  set(155, liens.some(a => { try { const u = new URL(a.href); return u.origin === location.origin && /^\/([a-z]{2}\/?)?$/.test(u.pathname); } catch (e) { return false; } }) ? C : NC, 'Lien vers la page d\'accueil cherché');
  // 156 : fil d'Ariane (hors accueil)
  const ariane = document.querySelector('[aria-label*="ariane" i], [aria-label*="breadcrumb" i], .breadcrumb, .breadcrumbs, [itemtype*="BreadcrumbList"], script[type="application/ld+json"]:not(:empty)');
  const arianeOk = ariane && (ariane.tagName !== 'SCRIPT' || /BreadcrumbList/.test(ariane.textContent));
  set(156, accueil ? NA : (arianeOk ? C : NC), accueil ? 'Page d\'accueil' : (arianeOk ? 'Fil d\'Ariane trouvé' : 'Aucun fil d\'Ariane'));
  // 157 : item actif de menu signalé
  set(157, document.querySelector('nav [aria-current], header [aria-current]') ? C : NC, 'aria-current cherché dans la navigation');
  // 164 : lien d'évitement en début de code
  const premier = [...document.querySelectorAll('a[href], button')].slice(0, 3);
  set(164, premier.some(a => (a.getAttribute('href') || '').startsWith('#')) ? C : NC, 'Lien d\'accès rapide cherché parmi les 3 premiers éléments focalisables');
  // 168, 169, 170 : moteur de recherche
  const recherche = document.querySelector('form[action*="search"], form[role="search"], input[type="search"]');
  set(168, recherche ? C : NC, recherche ? 'Formulaire de recherche présent' : 'Aucun moteur de recherche');
  const formRech = document.querySelector('form[action*="search"]');
  set(169, !formRech ? NT : ((formRech.getAttribute('method') || 'get').toLowerCase() === 'get' ? C : NC), 'Méthode du formulaire de recherche');
  set(170, !surPageRecherche ? NA : (recherche ? C : NC), 'Champ de recherche sur la page de résultats');
  // 171 : plan du site
  set(171, lienVers(/plan du site|sitemap|plan-du-site/) ? C : NC, 'Lien vers un plan du site cherché');
  // 186 : taille des éléments cliquables (24 x 24 pixels au moins, WCAG 2.5.8)
  const cliquables = [...document.querySelectorAll('a[href], button')].filter(visible).filter(e => !e.closest('p, li p'));
  const petits = cliquables.filter(e => { const b = e.getBoundingClientRect(); return b.width < 24 || b.height < 24; });
  set(186, petits.length ? NC : C, `${cliquables.length} élément(s) cliquable(s) hors texte, ${petits.length} de moins de 24 x 24 px`);
  // 190 : famille générique de police en dernier recours
  const polices = [...new Set([...document.querySelectorAll('body, p, h1, h2, a, button')].map(e => getComputedStyle(e).fontFamily))];
  const sansGenerique = polices.filter(f => !/(sans-serif|serif|monospace|system-ui|cursive|fantasy)\s*$/i.test(f.trim()));
  set(190, sansGenerique.length ? NC : C, `${polices.length} pile(s) de polices, ${sansGenerique.length} sans famille générique finale`);
  // 191 : texte non justifié
  const justifies = [...document.querySelectorAll('p, li, div')].filter(e => getComputedStyle(e).textAlign === 'justify' && e.innerText.trim().length > 80);
  set(191, justifies.length ? NC : C, `${justifies.length} bloc(s) de texte justifié(s)`);
  // 193 et 194 : zoom et adaptation mobile
  const viewport = document.querySelector('meta[name="viewport"]')?.content || '';
  const zoomBloque = /user-scalable\s*=\s*(no|0)/i.test(viewport) || /maximum-scale\s*=\s*1(\.0)?\b/i.test(viewport);
  set(193, zoomBloque ? NC : C, `viewport : « ${viewport} »`);
  set(194, /width\s*=\s*device-width/i.test(viewport) ? C : NC, 'Meta viewport avec width=device-width');
  // 195 : styles d'impression
  let impression = !!document.querySelector('link[rel="stylesheet"][media*="print"]');
  for (const f of document.styleSheets) { try { if ([...f.cssRules].some(r => r.media && /print/.test(r.media.mediaText))) impression = true; } catch (e) { /* feuille d'un autre domaine */ } }
  set(195, impression ? C : NC, impression ? 'Styles d\'impression trouvés' : 'Aucun style d\'impression lisible');
  // 232, 233 : jeu de caractères
  const B = window.__BRUT;
  const metaCs = document.querySelector('meta[charset], meta[http-equiv="Content-Type" i]');
  if (B && B.taille) {
    // HTML5 : la déclaration doit tenir dans les 1 024 premiers octets du code source (faux négatif relevé le 12/11)
    const ok = B.fin_meta_charset !== null && B.fin_meta_charset <= 1024;
    set(232, ok ? C : NC, B.fin_meta_charset === null ? 'Aucune meta charset dans le code source' : `Meta charset terminée à l'octet ${B.fin_meta_charset} (limite 1 024)` + (B.declarations > 1 ? ` ; ${B.declarations} déclarations` : ''));
  } else {
    set(232, metaCs ? C : NC, 'Meta charset cherchée (position non mesurée : code source brut indisponible)');
  }
  set(233, /utf-?8/i.test(document.characterSet) ? C : NC, `Codage : ${document.characterSet}`);
  // 234 : un seul h1, pas de saut de niveau
  const titres = [...document.querySelectorAll('h1, h2, h3, h4, h5, h6')].filter(visible).map(h => +h.tagName[1]);
  const sauts = titres.filter((n, i) => i > 0 && n > titres[i - 1] + 1).length;
  const h1 = titres.filter(n => n === 1).length;
  set(234, h1 === 1 && !sauts ? C : NC, `${h1} h1, ${titres.length} titre(s), ${sauts} saut(s) de niveau`);
  // 236 : identifiants uniques
  const ids = [...document.querySelectorAll('[id]')].map(e => e.id);
  const doublons = [...new Set(ids.filter((v, i) => ids.indexOf(v) !== i))];
  set(236, doublons.length ? NC : C, `${doublons.length} identifiant(s) en double ${doublons.slice(0, 5).join(', ')}`);
  // 237, 238 : copie et menu contextuel non bloqués
  const corpsStyle = getComputedStyle(document.body).userSelect;
  set(237, document.body.hasAttribute('oncopy') || corpsStyle === 'none' ? NC : C, `user-select du corps : ${corpsStyle}`);
  set(238, document.body.hasAttribute('oncontextmenu') || document.documentElement.hasAttribute('oncontextmenu') ? NC : C, 'oncontextmenu cherché sur html et body');
  // 239 : pas de redirection ni de rafraîchissement automatique côté client
  set(239, document.querySelector('meta[http-equiv="refresh" i]') ? NC : C, 'Meta refresh cherchée');
  // 242, 243 : tableaux de données
  const tableaux = [...document.querySelectorAll('table')].filter(t => t.querySelector('th') && visible(t));
  set(242, !tableaux.length ? NA : (tableaux.every(t => [...t.querySelectorAll('th')].every(th => th.scope || th.id)) ? C : NC), `${tableaux.length} tableau(x) de données`);
  set(243, !tableaux.length ? NA : (tableaux.every(t => t.querySelector('caption') || t.getAttribute('aria-label')) ? C : NC), `${tableaux.length} tableau(x) de données, titre (caption) cherché`);

  return { url: location.href, date: new Date().toISOString(), version: `controles_page.js ${VERSION}`, resultats: R };
})();
