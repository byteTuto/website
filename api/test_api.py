#!/usr/bin/env python3
"""Test de bout en bout du service d'inscription, à travers nginx.
usage : python3 api/test_api.py http://localhost:8080
"""
import json, sys, urllib.error, urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None


opener = urllib.request.build_opener(NoRedirect)


def call(method, path, data=None, form=False, ip="203.0.113.1"):
    headers = {"X-Real-IP": ip}
    body = None
    if data is not None:
        if form:
            from urllib.parse import urlencode
            body = urlencode(data).encode(); headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode(); headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        r = opener.open(req, timeout=5)
    except urllib.error.HTTPError as e:
        r = e
    raw = r.read().decode() if r.status != 303 else ""
    return r.status, (json.loads(raw) if raw.startswith("{") else raw), r.headers


def check(cond, msg):
    if not cond:
        sys.exit(f"✘ {msg}")
    print(f"✔ {msg}")


s, d, _ = call("GET", "/api/health"); check(s == 200 and d["ok"], "santé de l'API")
s, d, _ = call("GET", "/api/count"); check(s == 200 and d["count"] == 0 and d["show"] is False, "compteur à 0, masqué")
s, d, _ = call("POST", "/api/subscribe", {"email": "Test@Exemple.fr"}); check(s == 201 and d["rank"] == 1, "nouvelle inscription (rang 1)")
s, d, _ = call("POST", "/api/subscribe", {"email": "test@exemple.fr"}); check(s == 200 and d["new"] is False and "rank" not in d, "doublon accepté sans rang (email normalisé)")
s, d, _ = call("POST", "/api/subscribe", {"email": "pas-un-email"}); check(s == 422 and d["error"] == "invalid_email", "email invalide refusé")
s, d, _ = call("POST", "/api/subscribe", {"email": "robot@exemple.fr", "website": "spam"}, ip="203.0.113.2"); check(s == 200 and d["new"] is False, "pot de miel ignoré en silence")
s, d, _ = call("GET", "/api/count"); check(d["count"] == 1, "le robot n'a pas été compté")
s, _, h = call("POST", "/api/subscribe", {"email": "sansjs@exemple.fr"}, form=True, ip="203.0.113.3"); check(s == 303 and h["Location"].endswith("/#merci"), "formulaire sans JavaScript → /#merci")
s, _, h = call("POST", "/api/subscribe", {"email": "nope"}, form=True, ip="203.0.113.3"); check(s == 303 and h["Location"].endswith("/#email-invalide"), "formulaire sans JS, email invalide → /#email-invalide")
# nginx remplace X-Real-IP par la vraie adresse : tous ces appels viennent de la même IP (lancer l'API avec RATE_MAX=8)
codes = [call("POST", "/api/subscribe", {"email": f"r{i}@exemple.fr"}, ip="203.0.113.9")[0] for i in range(8)]
check(429 in codes, f"limite de débit ({codes})")
s, d, _ = call("GET", "/api/nexiste-pas"); check(s == 404, "route inconnue → 404")
print("✔ API OK")
