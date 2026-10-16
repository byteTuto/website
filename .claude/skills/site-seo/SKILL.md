---
name: site-seo
description: Checklist SEO de bytetuto.com — balises head, données structurées JSON-LD, titres, URL, sitemap, robots, maillage interne et Core Web Vitals. À utiliser pour toute création ou modification de page, de titre, de texte, d'URL ou d'image dans site/, et pour toute question de référencement Google.
---

# SEO excellent, sur chaque page

Une page n'est terminée que si `python3 scripts/check_seo_agents.py` passe (il contrôle aussi les règles du skill `site-agent-friendly`). Il tourne dans la CI : une erreur bloque le déploiement.

## 1. Le `<head>` obligatoire (dans cet ordre)

```html
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Installer Node.js en 2 minutes (Windows, Mac, Linux) — byteTuto</title>
<meta name="description" content="…120 à 160 caractères, avec le mot-clé principal et une promesse concrète…">
<link rel="canonical" href="https://bytetuto.com/tutos/installer-node/">
<link rel="alternate" type="text/markdown" href="/tutos/installer-node/index.md">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#0E1116">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<!-- Open Graph + Twitter -->
<meta property="og:type" content="article">          <!-- website pour l'accueil -->
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="byteTuto">
<meta property="og:title" content="…">
<meta property="og:description" content="…">
<meta property="og:url" content="https://bytetuto.com/…">   <!-- = canonical -->
<meta property="og:image" content="https://bytetuto.com/…1200x630.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="…">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{…}</script>   <!-- données, pas du code : autorisé par la CSP -->
```

Règles :
- **title** : 30 à 60 caractères, mot-clé au début, se termine par ` — byteTuto`. Unique sur tout le site.
- **description** : 120 à 160 caractères, unique, tutoiement, verbe d'action.
- **canonical** : URL absolue `https://bytetuto.com/…`, toujours avec `/` final pour un dossier. `og:url` identique.
- `<html lang="fr">` sur chaque page.
- Pages à ne pas indexer (404, merci, brouillons) : `<meta name="robots" content="noindex">` et **absentes** du sitemap.

## 2. Structure du contenu

- **Un seul `<h1>`**, qui reprend l'intention de recherche. Puis `h2` → `h3` sans sauter de niveau.
- Balises sémantiques : `header`, `nav`, `main`, `article`, `section` avec titre, `footer`. Fil d'Ariane en `<nav aria-label="Fil d'Ariane">`.
- Le texte important est **dans le HTML**, pas injecté par JavaScript (Google et les agents IA le lisent sans exécuter le JS).
- Toute image de contenu a un `alt` descriptif ; image décorative : `alt=""` ou `aria-hidden="true"`.
- Liens : texte explicite (« Voir le tuto Git rebase », jamais « clique ici »). Liens externes `rel="noopener"` ; liens affiliés et sponsorisés `rel="sponsored noopener"` (+ mention « lien affilié » visible, cf. loi influenceurs).
- Tuto : intro de 2-3 phrases qui répond directement, puis étapes numérotées, blocs de code copiables, section « En résumé », vidéo YouTube intégrée si elle existe.
- Maillage : chaque tuto lie 2-3 tutos proches + sa catégorie ; chaque page est à 3 clics maximum de l'accueil.

## 3. URL

- Minuscules, mots séparés par `-`, sans accent ni mot vide : `/tutos/git-rebase-interactif/`.
- Arborescence : `/tutos/<slug>/`, `/categories/<slug>/`, `/outils/`, `/newsletter/`, `/a-propos/`.
- Fichiers : `site/tutos/<slug>/index.html` (+ `index.md`, voir `site-agent-friendly`).
- Ne jamais changer une URL publiée ; si c'est indispensable, redirection 301 dans `nginx/site.inc`.

## 4. Données structurées (JSON-LD, schema.org)

| Page | Type |
| --- | --- |
| Accueil | `WebSite` + `Organization` (logo, `sameAs` YouTube/TikTok, email) |
| Tuto | `TechArticle` (ou `HowTo` si étapes), `author`, `datePublished`, `dateModified`, `image`, `inLanguage: "fr-FR"` |
| Tuto avec vidéo | + `VideoObject` (`name`, `description`, `thumbnailUrl`, `uploadDate`, `duration` ISO 8601, `embedUrl`) |
| Toutes sauf accueil | `BreadcrumbList` |
| FAQ visible | `FAQPage` (seulement si les questions sont affichées sur la page) |

Le JSON doit être valide (le script le parse) et décrire **ce qui est visible** sur la page.

## 5. Fichiers du site

- `site/sitemap.xml` : chaque page indexable avec `<loc>` (= canonical) et `<lastmod>` (AAAA-MM-JJ) mis à jour à chaque modification.
- `site/robots.txt` : `Allow: /` + ligne `Sitemap: https://bytetuto.com/sitemap.xml`. Ne jamais y bloquer CSS/JS.
- `site/og-image.png` 1200×630 par défaut ; une image OG par tuto si possible (miniature YouTube recadrée).

## 6. Performance (Core Web Vitals = critère de classement)

Objectifs mobile : **LCP < 2,5 s, CLS < 0,1, INP < 200 ms**, Lighthouse SEO = 100, Performance ≥ 90.
- Polices : un seul appel Google Fonts avec `display=swap`, uniquement les graisses utilisées, `preconnect` en place.
- Images : `width`/`height`, WebP/AVIF, lazy-loading sous la ligne de flottaison (voir `site-responsive`).
- JS en `defer`, pas de bibliothèque lourde pour une page statique.
- Vidéo YouTube : façade (miniature + bouton ▶) qui charge l'iframe au clic.
- Contrôle : `npx lighthouse https://bytetuto.com/ --preset=desktop` puis sans preset (mobile).

## 7. Après la mise en ligne

- Google Search Console : propriété `bytetuto.com` (vérification DNS), soumettre `https://bytetuto.com/sitemap.xml`.
- Bing Webmaster Tools (alimente aussi plusieurs moteurs IA) : importer depuis Search Console.
- Dans les descriptions YouTube/TikTok : lien vers le tuto correspondant sur bytetuto.com (backlinks + trafic).
