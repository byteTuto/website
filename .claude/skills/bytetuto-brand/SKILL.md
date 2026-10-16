---
name: bytetuto-brand
description: Charte graphique byteTuto (couleurs, typos, logo ▶_, ton). À utiliser avant toute modification visuelle ou de texte du site — pages HTML, CSS, images, 404, emails.
---

# Charte byteTuto

Concept : **▶_** — le bouton play d'une vidéo qui devient l'invite d'un terminal.
Signature : « Apprends la tech, un byte à la fois. »
Le nom s'écrit **toujours** `byteTuto` (jamais Bytetuto, ByteTuto, BYTETUTO dans le texte courant).

## Couleurs (tokens)

| Token | Clair | Sombre | Usage |
| --- | --- | --- | --- |
| surface | #F6F5F0 | #0E1116 | fond de page |
| surface-raised | #FFFFFF | #171B22 | cartes, blocs de code |
| ink | #0E1116 | #F2F1EC | texte principal |
| ink-muted | #565B66 | #A3A8B3 | texte secondaire |
| line | #DDDBD2 | #2A2F38 | filets, points de la trame |
| byte | #B8F03C | #B8F03C | vert signature : tuile, bouton principal, aplats |
| byte-ink | #3B6B00 | #B8F03C | le vert quand il est du TEXTE |
| byte-tint | #E9F9C8 | #24300F | fond léger, badge |
| on-byte | #0E1116 | #0E1116 | texte posé sur byte ou spark |
| spark | #FF5A1F | #FF6B33 | accent rare : UN seul élément par écran |
| tile | #0E1116 | #1E232C | aplats sombres, bandeaux |
| danger | #C4320A | #FF7A5C | erreurs uniquement |

Règles :
- Jamais `byte` (#B8F03C) en texte sur fond clair → utiliser `byte-ink`.
- Jamais de texte blanc sur `byte` ou `spark` → `on-byte`.
- Pas de dégradé ni d'ombre portée sur le logo. Les lueurs « néon » sont un habillage d'animation, pas le logo.
- Contraste texte/fond ≥ 4,5:1.

## Typographie (Google Fonts)
- Space Grotesk 700 (titres, letter-spacing serré −0,02em à −0,03em)
- IBM Plex Sans 400/600 (texte)
- JetBrains Mono 500 (code, commandes, petites étiquettes façon terminal)

## Formes
Rayons : 6px (badges), 12px (boutons, cartes), 24px (grands blocs, tuile du logo = 23 % du côté).
Motif maison : trame de points en `line` sur fond sombre, blocs `byte`/`spark` qui débordent des bords.

## Logo
Le logotype est un DESSIN (traits monoline de 9 unités, bouts arrondis), pas une police : ne jamais le retaper en texte.
Les tracés sont dans `site/index.html` (SVG `.logo`). Sur fond sombre : « byte » en #F2F1EC, « Tuto » en #B8F03C.
Symbole seul : `site/favicon.svg`.

## Ton
Tutoiement, phrases courtes, verbes d'action. On montre avant d'expliquer.
Pas de jargon non expliqué, pas de promesses gonflées.
Exemples : « Installe Node en 2 minutes », « Le bug qui m'a coûté 4 heures ».

## Accessibilité
Respecter `prefers-reduced-motion` pour toute nouvelle animation. Focus visible (outline `byte`).
