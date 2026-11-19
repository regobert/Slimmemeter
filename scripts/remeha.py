"""Haalt dagelijkse energiegegevens van een Remeha-warmtepomp op via de Remeha Home cloud.

Er is geen officiële API. De inlogflow en endpoints volgen de (reverse-engineered) aanpak van
https://github.com/msvisser/remeha_home (custom_components/remeha_home/api.py).

Gebruik (GitHub Actions of lokaal):
    REMEHA_EMAIL=... REMEHA_PASSWORD=... python scripts/remeha.py --test

--test   logt alleen de structuur (velden, aantal dagen, periode) — geen verbruikscijfers,
         want Actions-logs van een openbare repository zijn openbaar. Er wordt niets opgeslagen.
"""
import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
from datetime import date, datetime, timedelta

import requests

LOGIN = "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com"
POLICY = "B2C_1A_RPSignUpSignInNewRoomv3.1"
CLIENT_ID = "6ce007c6-0628-419e-88f4-bee2e6418eec"
REDIRECT = "com.b2c.remehaapp://login-callback"
API = "https://api.bdrthermea.net/Mobile/api"
SUBSCRIPTION_KEY = "df605c5470d846fc91e848b1cc653ddf"  # publieke sleutel van de Remeha Home-app
FIELDS = ["heatingEnergyConsumed", "hotWaterEnergyConsumed", "coolingEnergyConsumed",
          "heatingEnergyDelivered", "hotWaterEnergyDelivered", "coolingEnergyDelivered"]


def secret(name):
    """Leest een secret; tolerant voor een geplakte '.env'-regel ('NAAM=waarde') en aanhalingstekens."""
    v = (os.getenv(name) or "").strip()
    if "=" in v and v.split("=", 1)[0].strip().upper().startswith("REMEHA"):
        v = v.split("=", 1)[1].strip()
    return v.strip('"').strip("'")


def login(session, email, password):
    state = secrets.token_urlsafe()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")

    r = session.get(f"{LOGIN}/oauth2/v2.0/authorize", params={
        "response_type": "code", "client_id": CLIENT_ID, "redirect_uri": REDIRECT,
        "scope": "openid https://bdrb2cprod.onmicrosoft.com/iotdevice/user_impersonation offline_access",
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
        "p": "B2C_1A_RPSignUpSignInNewRoomV3.1", "brand": "remeha", "lang": "en",
        "nonce": "defaultNonce", "prompt": "login", "signUp": "False",
    }, timeout=30)
    r.raise_for_status()
    request_id = r.headers["x-request-id"]
    state_props = base64.urlsafe_b64encode(f'{{"TID":"{request_id}"}}'.encode("ascii")).decode("ascii").rstrip("=")
    csrf = next((c.value for c in session.cookies if c.name == "x-ms-cpim-csrf"), None)
    if not csrf:
        sys.exit("Inloggen mislukt: geen CSRF-token van de Remeha-inlogpagina ontvangen.")

    r = session.post(f"{LOGIN}/{POLICY}/SelfAsserted",
                     params={"tx": "StateProperties=" + state_props, "p": POLICY},
                     headers={"x-csrf-token": csrf},
                     data={"request_type": "RESPONSE", "signInName": email, "password": password}, timeout=30)
    r.raise_for_status()
    if json.loads(r.text).get("status") != "200":
        sys.exit("Inloggen mislukt: e-mailadres of wachtwoord wordt door Remeha niet geaccepteerd. "
                 "Controleer de secrets REMEHA_EMAIL en REMEHA_PASSWORD (alleen de waarde, geen 'NAAM=').")

    r = session.get(f"{LOGIN}/{POLICY}/api/CombinedSigninAndSignup/confirmed", params={
        "rememberMe": "false", "csrf_token": csrf, "tx": "StateProperties=" + state_props, "p": POLICY,
    }, allow_redirects=False, timeout=30)
    r.raise_for_status()
    code = urllib.parse.parse_qs(urllib.parse.urlparse(r.headers["location"]).query)["code"][0]

    r = session.post(f"{LOGIN}/oauth2/v2.0/token?p=B2C_1A_RPSignUpSignInNewRoomV3.1", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
        "code_verifier": verifier, "client_id": CLIENT_ID,
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def api_get(session, token, path):
    r = session.get(API + path, headers={"Authorization": f"Bearer {token}",
                                         "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY}, timeout=30)
    r.raise_for_status()
    return r.json()


def daily(session, token, appliance_id, start, end):
    """Dagwaarden tussen start en end (inclusief), opgehaald per maand."""
    out = []
    d = start
    while d <= end:
        stop = min(end, (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1))
        s = datetime(d.year, d.month, d.day).strftime("%Y-%m-%d %H:%M:%S.%fZ")
        e = datetime(stop.year, stop.month, stop.day, 23, 59, 59).strftime("%Y-%m-%d %H:%M:%S.%fZ")
        try:
            js = api_get(session, token, f"/appliances/{appliance_id}/energyconsumption/daily?startDate={s}&endDate={e}")
            out.extend(js.get("data") or [])
        except requests.HTTPError as err:
            print(f"  {d:%Y-%m}: geen gegevens ({err.response.status_code})")
        d = stop + timedelta(days=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="alleen structuur loggen, niets opslaan")
    ap.add_argument("--van", default="2023-11-01", help="begindatum (JJJJ-MM-DD)")
    args = ap.parse_args()

    email, password = secret("REMEHA_EMAIL"), secret("REMEHA_PASSWORD")
    if not email or not password:
        sys.exit("REMEHA_EMAIL en/of REMEHA_PASSWORD ontbreken (GitHub: Settings > Secrets and variables > Actions).")

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    token = login(session, email, password)
    print("Ingelogd bij Remeha Home.")

    dash = api_get(session, token, "/homes/dashboard")
    appliances = dash.get("appliances") or []
    print(f"Toestellen gevonden: {len(appliances)}")
    start, end = date.fromisoformat(args.van), date.today() - timedelta(days=1)

    for i, app in enumerate(appliances, 1):
        aid = app.get("applianceId")
        try:
            tech = api_get(session, token, f"/appliances/{aid}/technicaldetails")
            model = tech.get("applianceName", "?")
        except requests.HTTPError:
            model = "?"
        print(f"Toestel {i}: model {model}; velden in dashboard: {', '.join(sorted(app.keys()))}")

        rows = daily(session, token, aid, start, end)
        print(f"  Dagwaarden: {len(rows)} records")
        if not rows:
            continue
        keys = sorted({k for r in rows for k in r.keys()})
        print(f"  Velden per dag: {', '.join(keys)}")
        dates = sorted(str(r.get("timeStamp") or r.get("date") or r.get("startDate") or "")[:10] for r in rows)
        print(f"  Periode: {dates[0]} t/m {dates[-1]}")
        for f in FIELDS:
            n = sum(1 for r in rows if (r.get(f) or 0) > 0)
            print(f"  {f}: {n} dagen met een waarde > 0")
        # opbouw van geneste velden (alleen namen en typen, geen waarden)
        def shape(v, depth=0):
            if isinstance(v, dict):
                return "{" + ", ".join(f"{k}: {shape(x, depth + 1)}" for k, x in sorted(v.items())) + "}" if depth < 4 else "{...}"
            if isinstance(v, list):
                return "[" + (shape(v[0], depth + 1) if v else "") + f"] ({len(v)}x)"
            return type(v).__name__
        sample = next((r for r in reversed(rows) if r.get("producerPerformanceStatistics")), None)
        print("  producerPerformanceStatistics: " + (shape(sample["producerPerformanceStatistics"]) if sample else "leeg"))
        n_pps = sum(1 for r in rows if r.get("producerPerformanceStatistics"))
        print(f"  producerPerformanceStatistics gevuld op {n_pps} dagen")
        if not args.test:
            print("  (opslaan volgt pas na akkoord over privacy; nu alleen getest)")


if __name__ == "__main__":
    main()
