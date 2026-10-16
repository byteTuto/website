#!/usr/bin/env python3
"""Contrôle responsive de toutes les pages de site/ avec Playwright (Chromium).

Usage :
  python3 scripts/check_responsive.py                         # sert site/ en local sur un port libre
  python3 scripts/check_responsive.py --base http://localhost:8088   # teste un serveur déjà lancé (conteneur)
  python3 scripts/check_responsive.py --shots /tmp/rs          # + captures PNG par page et largeur
Prérequis : pip install playwright && python3 -m playwright install chromium
Règles : .claude/skills/site-responsive
"""
import argparse, functools, http.server, sys, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent / "site"
VIEWPORTS = [(320, 640), (375, 667), (414, 896), (768, 1024), (1024, 600), (1440, 900)]
SETTLE_MS = 2600   # laisse finir les animations d'entrée

# Renvoie la liste des problèmes de la page, vus dans le navigateur.
PROBE = r"""
() => {
  const W = document.documentElement.clientWidth, out = [];
  const sw = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
  if (sw > W + 1) out.push(`défilement horizontal : page de ${sw}px pour un écran de ${W}px`);
  const visible = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity !== 0; };
  const skip = el => el.closest('[aria-hidden="true"], canvas, svg *, pre, code, .term__body') ||
    [...ancestors(el)].some(a => { const s = getComputedStyle(a); return s.position === 'fixed' || /hidden|clip|auto|scroll/.test(s.overflowX); });
  function* ancestors(el) { for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) yield a; }
  const name = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.classList.length ? '.' + [...el.classList].join('.') : '');
  for (const el of document.querySelectorAll('body *')) {
    if (!visible(el) || skip(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width && (r.right > W + 1 || r.left < -1)) out.push(`déborde de l'écran : ${name(el)} (${Math.round(r.left)} → ${Math.round(r.right)}px)`);
  }
  for (const el of document.querySelectorAll('a[href], button, input, select, textarea, [role=button]')) {
    if (!visible(el) || el.closest('[aria-hidden="true"]')) continue;
    if (getComputedStyle(el).display === 'inline' && el.closest('p, li, footer, figcaption, td')) continue; // lien dans une phrase
    const r = el.getBoundingClientRect();
    if (Math.min(r.width, r.height) < 24) out.push(`cible tactile trop petite : ${name(el)} ${Math.round(r.width)}×${Math.round(r.height)}px (min 24, idéal 44)`);
  }
  const fs = parseFloat(getComputedStyle(document.body).fontSize);
  if (fs < 16) out.push(`texte courant à ${fs}px (min 16px)`);
  return [...new Set(out)].slice(0, 15);
}
"""


def pages():
    for f in sorted(SITE.rglob("*.html")):
        rel = f.relative_to(SITE).as_posix()
        yield "/" + (rel[: -len("index.html")] if rel.endswith("index.html") else rel)


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    handler = functools.partial(Quiet, directory=str(SITE))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_port}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base"); ap.add_argument("--shots")
    args = ap.parse_args()
    base = (args.base or serve()).rstrip("/")
    shots = Path(args.shots) if args.shots else None
    if shots: shots.mkdir(parents=True, exist_ok=True)
    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for path in pages():
            for w, h in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                                          is_mobile=w < 768, has_touch=w < 1024)
                page = ctx.new_page()
                page.goto(base + path, wait_until="networkidle")
                page.wait_for_timeout(SETTLE_MS)
                problems = page.evaluate(PROBE)
                if shots:
                    slug = path.strip("/").replace("/", "_").replace(".html", "") or "index"
                    page.screenshot(path=str(shots / f"{slug}-{w}x{h}.png"), full_page=True)
                status = "✔" if not problems else "✘"
                print(f"{status} {path} @ {w}×{h}")
                for pb in problems: print(f"    - {pb}")
                failures += bool(problems)
                ctx.close()
        browser.close()
    print("✔ responsive OK" if not failures else f"✘ {failures} combinaison(s) page × largeur en échec")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
