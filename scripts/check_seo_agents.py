#!/usr/bin/env python3
"""Contrôle SEO + agent-friendly de toutes les pages de site/ (Python 3, bibliothèque standard).

Usage : python3 scripts/check_seo_agents.py [dossier_site]
Code de sortie 1 s'il y a au moins une erreur. Règles : .claude/skills/site-seo et site-agent-friendly.
"""
import json, re, sys
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

BASE = "https://bytetuto.com"
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "site")
NO_TWIN = {"404.html"}          # pages sans jumeau .md ni entrée sitemap

errors, warnings = [], []
def err(page, msg): errors.append(f"✘ {page}: {msg}")
def warn(page, msg): warnings.append(f"! {page}: {msg}")


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None; self.title = ""; self.meta = {}; self.links = []
        self.headings = []; self.imgs = []; self.jsonld = []; self.mains = 0
        self._in = None; self._buf = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html": self.lang = a.get("lang")
        elif tag == "svg": self.svg = getattr(self, "svg", 0) + 1
        elif tag == "title" and not getattr(self, "svg", 0) and not self.title: self._in, self._buf = "title", ""
        elif tag == "meta":
            k = a.get("name") or a.get("property")
            if k: self.meta[k.lower()] = a.get("content", "")
        elif tag == "link": self.links.append(a)
        elif tag == "img": self.imgs.append(a)
        elif tag == "main": self.mains += 1
        elif tag == "script" and a.get("type") == "application/ld+json": self._in, self._buf = "ld", ""
        elif re.fullmatch(r"h[1-6]", tag): self.headings.append(int(tag[1]))

    def handle_endtag(self, tag):
        if tag == "svg": self.svg -= 1
        elif tag == "title" and self._in == "title": self.title = self._buf.strip(); self._in = None
        elif tag == "script" and self._in == "ld": self.jsonld.append(self._buf); self._in = None

    def handle_data(self, data):
        if self._in: self._buf += data

    def link(self, rel, typ=None):
        for l in self.links:
            if rel in (l.get("rel") or "").split() and (typ is None or l.get("type") == typ):
                return l.get("href")


def url_of(html_path: Path) -> str:
    rel = html_path.relative_to(SITE).as_posix()
    return BASE + "/" + (rel[: -len("index.html")] if rel.endswith("index.html") else rel)


def front_matter(md: str) -> dict:
    m = re.match(r"---\n(.*?)\n---\n", md, re.S)
    if not m: return {}
    return {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)}


# ---- fichiers globaux ----
robots = (SITE / "robots.txt").read_text() if (SITE / "robots.txt").exists() else ""
if f"Sitemap: {BASE}/sitemap.xml" not in robots: err("robots.txt", f"ligne « Sitemap: {BASE}/sitemap.xml » manquante")
if re.search(r"^\s*Disallow:\s*/\s*$", robots, re.M): err("robots.txt", "« Disallow: / » bloque tout le site")

sitemap = set()
try:
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for u in ElementTree.parse(SITE / "sitemap.xml").getroot().findall("s:url", ns):
        sitemap.add(u.findtext("s:loc", namespaces=ns).strip())
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", (u.findtext("s:lastmod", namespaces=ns) or "").strip()):
            err("sitemap.xml", f"lastmod manquant ou invalide pour {u.findtext('s:loc', namespaces=ns)}")
except (FileNotFoundError, ElementTree.ParseError) as e:
    err("sitemap.xml", f"absent ou invalide ({e})")

llms = (SITE / "llms.txt").read_text() if (SITE / "llms.txt").exists() else ""
if not llms.startswith("# "): err("llms.txt", "absent ou ne commence pas par « # Nom du site »")
elif not re.search(r"^> ", llms, re.M): err("llms.txt", "résumé « > … » manquant")

# ---- pages ----
titles, descs, indexable = {}, {}, set()
pages = sorted(SITE.rglob("*.html"))
for f in pages:
    name = f.relative_to(SITE).as_posix()
    p = Page(); p.feed(f.read_text(encoding="utf-8"))
    noindex = "noindex" in p.meta.get("robots", "")

    if p.lang != "fr": err(name, '<html lang="fr"> manquant')
    vp = p.meta.get("viewport", "")
    if "width=device-width" not in vp: err(name, "meta viewport width=device-width manquante")
    if re.search(r"user-scalable\s*=\s*(no|0)|maximum-scale\s*=\s*1(\.0)?\b", vp): err(name, "le viewport bloque le zoom")
    if not p.title: err(name, "<title> manquant")
    if "byteTuto" not in p.title: err(name, "le <title> doit contenir « byteTuto »")
    if p.mains != 1: err(name, f"{p.mains} <main> (1 attendu)")
    if p.headings.count(1) != 1: err(name, f"{p.headings.count(1)} <h1> (1 attendu)")
    for a, b in zip(p.headings, p.headings[1:]):
        if b > a + 1: err(name, f"saut de niveau de titre h{a} → h{b}"); break
    for img in p.imgs:
        src = img.get("src", "?")
        if "alt" not in img: err(name, f"<img {src}> sans attribut alt")
        if not (img.get("width") and img.get("height")): err(name, f"<img {src}> sans width/height (CLS)")

    if noindex or name in NO_TWIN:
        if name in NO_TWIN and not noindex: err(name, 'doit avoir <meta name="robots" content="noindex">')
        continue

    # ---- SEO ----
    url = url_of(f); indexable.add(url)
    if not 30 <= len(p.title) <= 60: err(name, f"<title> de {len(p.title)} caractères (30–60)")
    d = p.meta.get("description", "")
    if not 120 <= len(d) <= 160: err(name, f"meta description de {len(d)} caractères (120–160)")
    if p.title in titles: err(name, f"<title> identique à {titles[p.title]}")
    if d and d in descs: err(name, f"description identique à {descs[d]}")
    titles[p.title] = name; descs[d] = name
    canon = p.link("canonical")
    if canon != url: err(name, f"canonical = {canon!r}, attendu {url!r}")
    for k in ("og:title", "og:description", "og:image", "og:url", "og:type", "og:locale", "twitter:card"):
        if not p.meta.get(k): err(name, f"meta {k} manquante")
    if p.meta.get("og:url") and p.meta["og:url"] != url: err(name, "og:url différent du canonical")
    if not p.meta.get("og:image", "").startswith(BASE): err(name, "og:image doit être une URL absolue https://bytetuto.com/…")
    if url not in sitemap: err(name, f"{url} absent de sitemap.xml")
    if not p.jsonld: err(name, "aucune donnée structurée JSON-LD")
    for raw in p.jsonld:
        try:
            data = json.loads(raw)
            if "@context" not in data: err(name, "JSON-LD sans @context")
        except json.JSONDecodeError as e:
            err(name, f"JSON-LD invalide ({e})")

    # ---- agent-friendly ----
    twin = f.with_suffix(".md")
    twin_url = "/" + twin.relative_to(SITE).as_posix()
    if not twin.exists():
        err(name, f"jumeau Markdown {twin.relative_to(SITE)} manquant"); continue
    if p.link("alternate", "text/markdown") not in (twin_url, BASE + twin_url):
        err(name, f'<link rel="alternate" type="text/markdown" href="{twin_url}"> manquant')
    md = twin.read_text(encoding="utf-8"); fm = front_matter(md)
    tn = twin.relative_to(SITE).as_posix()
    if not fm: err(tn, "front matter YAML (--- … ---) manquant")
    for k in ("title", "description", "url", "lang", "updated"):
        if fm and not fm.get(k): err(tn, f"front matter : « {k} » manquant")
    if fm.get("url") and fm["url"] != url: err(tn, f"url = {fm['url']}, attendu {url}")
    if fm.get("title") and fm["title"] != p.title: warn(tn, "title différent du <title> HTML")
    body = md[md.find("\n---\n", 4) + 5:] if fm else md
    if len(re.findall(r"^# ", body, re.M)) != 1: err(tn, "il faut exactement un titre « # … »")
    if "<div" in body or "<span" in body: err(tn, "HTML brut dans le Markdown")
    if BASE + twin_url not in llms: err("llms.txt", f"lien vers {BASE + twin_url} manquant")

for extra in sitemap - indexable:
    err("sitemap.xml", f"{extra} ne correspond à aucune page indexable")

print(f"{len(pages)} page(s) contrôlée(s) dans {SITE}")
print("\n".join(warnings + errors) or "✔ SEO + agent-friendly OK")
sys.exit(1 if errors else 0)
