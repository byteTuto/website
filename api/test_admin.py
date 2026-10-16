#!/usr/bin/env python3
"""Test de la page admin.
- à travers nginx en HTTPS (CI, certificat de test accepté) : python3 api/test_admin.py https://localhost:8443 "mot de passe"
- directement sur le service : API lancée avec ADMIN_ALLOW_HTTP=1 → python3 api/test_admin.py http://localhost:8001 "mot de passe"
L'API doit avoir ADMIN_SECRET (≥ 32 car.) et ADMIN_PASSWORD_HASH = empreinte du mot de passe, et une base vide.
"""
import json, re, ssl, sys, urllib.error, urllib.request
from urllib.parse import urlencode

BASE, PASSWORD = sys.argv[1].rstrip("/"), sys.argv[2]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None


op = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))


def call(method, path, form=None, cookie=None, ip="198.51.100.1", json_body=None):
    h = {"X-Real-IP": ip}
    body = None
    if form is not None:
        body = urlencode(form).encode(); h["Content-Type"] = "application/x-www-form-urlencoded"
    if json_body is not None:
        body = json.dumps(json_body).encode(); h["Content-Type"] = "application/json"
    if cookie:
        h["Cookie"] = cookie
    try:
        r = op.open(urllib.request.Request(BASE + path, data=body, method=method, headers=h), timeout=10)
    except urllib.error.HTTPError as e:
        r = e
    return r.status, r.read().decode("utf-8", "replace"), r.headers


def check(cond, msg):
    if not cond:
        sys.exit(f"✘ {msg}")
    print(f"✔ {msg}")


for e in ("alice@exemple.fr", "bob@exemple.fr", "chloe@exemple.fr"):
    call("POST", "/api/subscribe", json_body={"email": e}, ip="198.51.100.50")

s, b, h = call("GET", "/admin"); check(s in (301, 303) and h["Location"].endswith("/admin/"), "/admin → /admin/")
s, b, h = call("GET", "/admin/"); check(s == 200 and 'type="password"' in b, "formulaire de connexion")
check("noindex" in (h.get("X-Robots-Tag") or "") and h.get("Cache-Control") == "no-store", "noindex + no-store")
s, b, h = call("GET", "/admin/export.csv"); check(s == 303 and h["Location"] == "/admin/", "CSV refusé sans connexion")
s, b, h = call("POST", "/admin/login", {"password": "mauvais-mot-de-passe"}); check(s == 401 and "incorrect" in b, "mauvais mot de passe refusé")
s, b, h = call("POST", "/admin/login", {"password": PASSWORD})
ck = h.get("Set-Cookie") or ""
check(s == 303 and "HttpOnly" in ck and "SameSite=Strict" in ck and "Path=/admin" in ck, "connexion : cookie HttpOnly + SameSite=Strict")
cookie = ck.split(";")[0]

s, b, h = call("GET", "/admin/", cookie=cookie)
check(s == 200 and "alice@exemple.fr" in b and ">3<" in b, "tableau de bord : 3 inscrits listés")
csrf = re.search(r'name="csrf" value="([^"]+)"', b).group(1)
s, b, h = call("GET", "/admin/?q=bob", cookie=cookie); check("bob@exemple.fr" in b and "alice@" not in b, "recherche")
s, b, h = call("GET", "/admin/?q=%25", cookie=cookie); check("0 résultat" in b, "recherche : % pris littéralement")
s, b, h = call("GET", "/admin/export.csv", cookie=cookie)
check(s == 200 and "text/csv" in h["Content-Type"] and "attachment" in h["Content-Disposition"] and "chloe@exemple.fr" in b, "export CSV")
s, b, h = call("POST", "/admin/delete", {"email": "bob@exemple.fr"}, cookie=cookie); check(s == 403, "suppression sans jeton CSRF refusée")
s, b, h = call("POST", "/admin/delete", {"email": "bob@exemple.fr", "csrf": csrf}, cookie=cookie); check(s == 200 and "Oui, supprimer" in b, "suppression : demande de confirmation")
s, b, h = call("GET", "/api/count"); check(json.loads(b)["count"] == 3, "rien n'est supprimé avant confirmation")
s, b, h = call("POST", "/admin/delete", {"email": "bob@exemple.fr", "csrf": csrf, "confirm": "1"}, cookie=cookie); check(s == 303 and "supprime" in h["Location"], "suppression confirmée")
s, b, h = call("GET", "/api/count"); check(json.loads(b)["count"] == 2, "bob n'est plus compté")
s, b, h = call("GET", "/admin/", cookie=cookie[:-3] + "AAA"); check('type="password"' in b, "cookie trafiqué → reconnexion demandée")
s, b, h = call("POST", "/admin/logout", {"csrf": csrf}, cookie=cookie); check(s == 303 and "Max-Age=0" in h["Set-Cookie"], "déconnexion")
codes = [call("POST", "/admin/login", {"password": f"faux{i}"}, ip="198.51.100.66")[0] for i in range(6)]
check(codes[-1] == 429, f"blocage après 5 échecs ({codes})")
s, b, h = call("POST", "/admin/login", {"password": PASSWORD}, ip="198.51.100.66"); check(s == 429, "même le bon mot de passe est bloqué pendant 15 min")
print("✔ admin OK")
