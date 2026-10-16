---
name: site-responsive
description: Règles pour que chaque page de bytetuto.com soit responsive (mobile d'abord, 320 px → 1920 px, sans défilement horizontal). À utiliser pour toute création ou modification de page, de CSS, de mise en page, d'image ou de composant dans site/, et avant de valider une PR qui touche l'affichage.
---

# Site toujours responsive

Une page n'est terminée que si elle passe `python3 scripts/check_responsive.py` (aucun défilement horizontal, rien ne déborde de l'écran, cibles tactiles assez grandes) aux 6 tailles de référence. Ce contrôle tourne aussi dans la CI : une PR qui casse le responsive ne peut pas être déployée.

## Largeurs de référence (à tester toutes)

| Largeur | Cas |
| --- | --- |
| 320 px | petit Android, iPhone SE en zoom |
| 375 px | iPhone standard (cible n° 1 : l'audience vient de TikTok) |
| 414 px | grand téléphone |
| 768 px | tablette portrait |
| 1024 px | tablette paysage / petit portable |
| 1440 px | bureau |

Tailles testées par le script : 320×640, 375×667, 414×896, 768×1024, 1024×600 (écran bas), 1440×900.

## Règles CSS

1. **Mobile d'abord** : styles de base pour 320 px, puis `@media (min-width: …)` pour élargir. Points de rupture : `600px`, `900px`, `1200px` (pas de valeurs magiques ailleurs ; un composant peut utiliser `@container`).
2. **Pas de largeur fixe** supérieure à 280 px sans `min()` / `max-width: 100%` : `width: min(520px, 100%)`.
3. **Typo fluide** avec `clamp()` : titres `clamp(32px, 7vw, 72px)`, texte courant **16 px minimum** (jamais en dessous sur mobile, sinon iOS zoome dans les champs).
4. **Hauteurs** : `min-height: 100svh` (pas `100vh`, qui passe sous la barre d'adresse mobile). Jamais de `height` fixe sur un bloc de texte.
5. **Marges latérales** : gouttière de 16 px sur mobile (`space-4`), + `env(safe-area-inset-left/right)` pour les écrans à encoche (le viewport a déjà `viewport-fit=cover`).
6. **Texte long** : `overflow-wrap: anywhere` sur les URL, commandes et noms de fichiers ; blocs de code en `overflow-x: auto` **dans le bloc**, jamais sur la page.
7. **Grilles** : `grid-template-columns: repeat(auto-fill, minmax(min(280px, 100%), 1fr))` pour les cartes de tutos.
8. **Éléments décoratifs** qui débordent (blocs `byte`/`spark`, canvas) : `position: fixed` ou parent en `overflow: clip`, et tailles en `min(vw, px)`.
9. **Tactile** : boutons et liens isolés ≥ 44 × 44 px (24 px = minimum bloquant du script, WCAG 2.2), 8 px d'écart minimum entre deux cibles. Pas d'information disponible uniquement au survol (`:hover`) : prévoir `:focus-visible` et l'état tactile.
10. **Vidéos et iframes** (YouTube) : `aspect-ratio: 16 / 9; width: 100%; height: auto;` — vidéos TikTok en `9 / 16` avec `max-width: 360px`.

## Images

- Toujours `width` et `height` dans le HTML (évite le décalage de mise en page, CLS) + `max-width: 100%; height: auto` en CSS.
- Formats : SVG pour logos et icônes, WebP/AVIF pour les captures, avec `srcset` + `sizes` (ex. 480w, 960w, 1600w).
- `loading="lazy"` et `decoding="async"` sous la ligne de flottaison ; **jamais** sur l'image principale (LCP), qui prend `fetchpriority="high"`.
- Miniatures de tutos : `aspect-ratio: 16 / 9; object-fit: cover`.

## Viewport (déjà en place, ne pas retirer)

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```
Interdit : `maximum-scale=1`, `user-scalable=no` (bloque le zoom, mauvais pour l'accessibilité).

## Animation et performance mobile

- `prefers-reduced-motion` respecté (règle du projet).
- Canvas : limiter `devicePixelRatio` à 2 et réduire la densité sous 600 px (déjà fait dans `app.js`, garder ce principe).
- Pas de `backdrop-filter` lourd empilé sur mobile.

## Vérifier

```bash
# avec le conteneur de check-site lancé sur :8088, ou sans argument (serveur local sur site/)
python3 scripts/check_responsive.py                 # toutes les pages de site/
python3 scripts/check_responsive.py --shots /tmp/rs # + captures PNG par largeur
```
Le script échoue si `scrollWidth > largeur`, si un élément visible dépasse du bord, si une cible tactile fait moins de 24 px (les liens dans une phrase sont exemptés) ou si le texte courant fait moins de 16 px. Regarder les captures à 320 et 375 px avant de pousser.
