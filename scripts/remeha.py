"""Haalt dagelijkse energiegegevens van een Remeha-warmtepomp op via de Remeha Home cloud.

Er is geen officiële API. De inlogflow en endpoints volgen de (reverse-engineered) aanpak van
https://github.com/msvisser/remeha_home (custom_components/remeha_home/api.py).

Gebruik (GitHub Actions of lokaal):
    REMEHA_EMAIL=... REMEHA_PASSWORD=... python scripts/remeha.py --test

Zonder --test: werkt remeha_data.js bij (dagwaarden in kWh; wp = warmtepomp/stroom,
ketel = cv-ketel/gas; *_in = verbruikte energie, *_uit = geleverde warmte, ww = warm water).
--test   logt alleen de structuur — geen verbruikscijfers, want Actions-logs van een openbare
         repository zijn openbaar — en slaat niets op.
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
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

LOGIN = "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com"
POLICY = "B2C_1A_RPSignUpSignInNewRoomv3.1"
CLIENT_ID = "6ce007c6-0628-419e-88f4-bee2e6418eec"
REDIRECT = "com.b2c.remehaapp://login-callback"
API = "https://api.bdrthermea.net/Mobile/api"
SUBSCRIPTION_KEY = "df605c5470d846fc91e848b1cc653ddf"  # publieke sleutel van de Remeha Home-app
DATA_FILE = Path(__file__).resolve().parent.parent / "remeha_data.js"
PREFIX = "window.REMEHA_DATA = "
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


def classify(p):
    """Warmtepomp ('wp', stroom) of cv-ketel ('ketel', gas) op basis van energyType/producerType."""
    t = f"{p.get('energyType', '')} {p.get('producerType', '')}".lower()
    if "elec" in t or "pump" in t or "heatpump" in t or "hp" == t.strip():
        return "wp"
    if "gas" in t or "boiler" in t or "ketel" in t:
        return "ketel"
    return None


def day_key(ts):
    """timeStamp -> 'JJJJ-MM-DD' in Nederlandse tijd."""
    s = str(ts or "")
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(ZoneInfo("Europe/Amsterdam"))
        return dt.date().isoformat()
    except ValueError:
        return s[:10]


def to_day(r):
    """Compacte dagwaarden (kWh). wp = warmtepomp (stroom), ketel = cv-ketel (gas)."""
    num = lambda v: float(v) if isinstance(v, (int, float)) else 0.0
    d = {"in": num(r.get("heatingEnergyConsumed")) + num(r.get("hotWaterEnergyConsumed")),
         "uit": num(r.get("heatingEnergyDelivered")) + num(r.get("hotWaterEnergyDelivered"))}
    for p in (r.get("producerPerformanceStatistics") or {}).get("producers") or []:
        k = classify(p)
        if not k:
            continue
        d[k + "_in"] = d.get(k + "_in", 0) + num(p.get("energyConsumptionCH"))
        d[k + "_uit"] = d.get(k + "_uit", 0) + num(p.get("energyProductionCH"))
        d[k + "_ww_in"] = d.get(k + "_ww_in", 0) + num(p.get("energyConsumptionDHW"))
        d[k + "_ww_uit"] = d.get(k + "_ww_uit", 0) + num(p.get("energyProductionDHW"))
    return {k: round(v, 3) for k, v in d.items() if v}


def lees_data():
    if not DATA_FILE.exists():
        return {}
    t = DATA_FILE.read_text(encoding="utf-8").strip()
    if t.startswith(PREFIX):
        t = t[len(PREFIX):]
    return json.loads(t.rstrip(";") or "{}")


def schrijf_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(PREFIX)
        json.dump({k: data[k] for k in sorted(data)}, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="alleen structuur loggen, niets opslaan")
    ap.add_argument("--van", default="2023-11-01", help="vroegste begindatum (JJJJ-MM-DD)")
    args = ap.parse_args()

    email, password = secret("REMEHA_EMAIL"), secret("REMEHA_PASSWORD")
    if not email or not password:
        sys.exit("REMEHA_EMAIL en/of REMEHA_PASSWORD ontbreken (GitHub: Settings > Secrets and variables > Actions).")

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    token = login(session, email, password)
    print("Ingelogd bij Remeha Home.")

    dash = api_get(session, token, "/homes/dashboard")
    appliances = [a for a in (dash.get("appliances") or []) if a.get("capabilityEnergyConsumption", True)]
    print(f"Toestellen met energiegegevens: {len(appliances)}")
    if not appliances:
        return

    data = {} if args.test else lees_data()
    end = date.today() - timedelta(days=1)
    start = date.fromisoformat(args.van)
    if data and not args.test:
        start = max(start, date.fromisoformat(max(data)) - timedelta(days=7))  # laatste week opnieuw (late correcties)
    print(f"Ophalen {start} t/m {end}")

    nieuw = {}
    for app in appliances:
        rows = daily(session, token, app.get("applianceId"), start, end)
        print(f"  Dagwaarden ontvangen: {len(rows)}")
        if args.test:
            types = sorted({f"{p.get('producerType')}/{p.get('energyType')}" for r in rows
                            for p in (r.get("producerPerformanceStatistics") or {}).get("producers") or []})
            print(f"  Producenten (type/energie): {', '.join(types)} -> " +
                  ", ".join(f"{t}={classify({'producerType': t.split('/')[0], 'energyType': t.split('/')[1]})}" for t in types))
        for r in rows:
            k = day_key(r.get("timeStamp"))
            v = to_day(r)
            if not k or not v:
                continue
            if k in nieuw:  # meerdere toestellen: optellen
                for f, x in v.items():
                    nieuw[k][f] = round(nieuw[k].get(f, 0) + x, 3)
            else:
                nieuw[k] = v

    if args.test:
        velden = sorted({f for v in nieuw.values() for f in v})
        print(f"  Dagen met gegevens: {len(nieuw)}; velden: {', '.join(velden)} (test: niets opgeslagen)")
        return

    gewijzigd = sum(1 for k, v in nieuw.items() if data.get(k) != v)
    data.update(nieuw)
    if gewijzigd:
        schrijf_data(data)
        print(f"remeha_data.js bijgewerkt: {gewijzigd} dag(en), nu {len(data)} dagen t/m {max(data)}")
    else:
        print("Geen wijzigingen.")


if __name__ == "__main__":
    main()
