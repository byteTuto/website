---
name: site-agent-friendly
description: Rendre bytetuto.com lisible par les agents IA et les LLM — une version Markdown (.md) de chaque page, /llms.txt, négociation Accept text/markdown, HTML sémantique et robots.txt. À utiliser pour toute création, modification ou suppression de page dans site/, et dès qu'on parle de .md, llms.txt, agents, ChatGPT/Claude/Perplexity ou crawlers IA.
---

# Site agent-friendly

Principe : **chaque page HTML a un jumeau Markdown** au contenu identique, et les agents savent le trouver.
`python3 scripts/check_seo_agents.py` vérifie tout ce qui suit.

## 1. Le jumeau `.md` de chaque page

| Page HTML | Fichier | URL du Markdown |
| --- | --- | --- |
| `site/index.html` → `/` | `site/index.md` | `/index.md` |
| `site/tutos/git-rebase/index.html` → `/tutos/git-rebase/` | `site/tutos/git-rebase/index.md` | `/tutos/git-rebase/index.md` |

Exception : `404.html` (pas de jumeau).

Quand on crée ou modifie une page, **on modifie les deux fichiers dans le même commit**. Le `.md` n'est pas un résumé : il contient tout le contenu utile de la page (texte, étapes, code, liens), sans la décoration.

Format du `.md` :

~~~markdown
---
title: Git rebase interactif en 3 minutes
description: Réécris tes commits proprement avec git rebase -i, sans rien casser.
url: https://bytetuto.com/tutos/git-rebase/
lang: fr
updated: 2026-10-16
---

# Git rebase interactif en 3 minutes

> Réponse directe en 1-2 phrases : ce que la page apprend.

## Étapes
1. …

```bash
git rebase -i HEAD~3
```

## Voir aussi
- [Annuler un commit](https://bytetuto.com/tutos/annuler-commit/index.md)

Vidéo : https://www.youtube.com/watch?v=…
~~~

Règles :
- Front matter YAML avec `title`, `description`, `url` (= canonical HTML), `lang`, `updated` (mêmes valeurs que la page).
- Un seul `# titre` = le `<h1>`. Hiérarchie `##`/`###` identique au HTML.
- Liens **absolus** (`https://bytetuto.com/…`), et vers le `.md` quand la cible en a un.
- Code dans des blocs ``` avec le langage. Pas de HTML brut, pas d'emoji décoratif, pas d'image sans texte (`![texte alternatif](url)`).
- Dans le HTML : `<link rel="alternate" type="text/markdown" href="…/index.md">` dans le `<head>`.

## 2. `/llms.txt` — le sommaire pour les agents

`site/llms.txt`, au format llmstxt.org : `# byteTuto`, une citation `>` qui résume le site, puis des sections `##` avec une liste de liens vers les `.md` :

```markdown
## Tutos
- [Git rebase interactif](https://bytetuto.com/tutos/git-rebase/index.md): réécrire ses commits proprement.
```
Ajouter / retirer la ligne à chaque page créée / supprimée. Section `## Optional` pour ce qui est secondaire.
Quand il y aura plus de ~10 tutos : générer aussi `site/llms-full.txt` (tous les `.md` concaténés).

## 3. Serveur (déjà configuré dans `nginx/`)

- `.md` servi en `text/markdown; charset=utf-8`, avec `X-Robots-Tag: noindex` (pas de contenu dupliqué dans Google — la version HTML reste la seule indexée).
- Négociation de contenu : une requête avec `Accept: text/markdown` sur `/` ou `/tutos/x/` reçoit directement le `.md` (en-tête `Vary: Accept` sur le HTML).
- Test :
  ```bash
  curl -s http://localhost:8088/index.md | head
  curl -s -H 'Accept: text/markdown' http://localhost:8088/ | head
  curl -sI http://localhost:8088/index.md | grep -i content-type   # text/markdown
  ```

## 4. HTML lisible par un agent qui navigue

- Contenu présent dans le HTML initial (pas seulement rendu en JS).
- Balises sémantiques, `<main>` unique, titres hiérarchisés, listes en `<ol>/<ul>`, code en `<pre><code class="language-…">`.
- Boutons = `<button>`, liens = `<a href>` ; chaque contrôle a un nom accessible (texte visible ou `aria-label`).
- Formulaires (newsletter) : `<label for>` sur chaque champ, `name` et `autocomplete` explicites, message de résultat dans le DOM.
- Pas de contenu derrière une interaction obligatoire (onglets cachés : le contenu reste dans le DOM).
- Données structurées JSON-LD à jour (voir `site-seo`) : les agents s'en servent aussi.

## 5. Crawlers IA (`robots.txt`)

Choix du projet : **on autorise** les crawlers IA (visibilité dans ChatGPT, Claude, Perplexity, Google AI). Ne pas ajouter de `Disallow` pour GPTBot, ClaudeBot, PerplexityBot, Google-Extended, etc. sans décision explicite. Garder `Sitemap:` en bas du fichier.
