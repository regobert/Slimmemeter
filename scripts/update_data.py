"""Werkt alle_data.js bij met nieuwe Slimmemeterportal-data en buitentemperaturen.

Draait in GitHub Actions (zie .github/workflows/energiedata.yml), maar ook lokaal:
    SMP_API_KEY=... python scripts/update_data.py

Er is geen lokale opslag nodig: het bestaande alle_data.js in de repository is de
bron. Alleen ontbrekende of onvolledige dagen worden opnieuw opgehaald.
"""
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

BASE_URL = "https://app.slimmemeterportal.nl/userapi/v1"
LAT, LON = 52.2658, 6.7931  # Hengelo (Overijssel)
DATA_FILE = Path(__file__).resolve().parent.parent / "alle_data.js"
PREFIX = "window.ENERGIE_DATA = "

TERUGKIJKEN_DAGEN = int(os.getenv("TERUGKIJKEN_DAGEN", "14"))  # zoveel dagen terug controleren
OPNIEUW_DAGEN = 3  # de laatste dagen altijd opnieuw ophalen (data kan nog aangevuld worden)
MIN_REGELS = {"elektriciteit": 92, "gas": 23}  # minder dan dit = onvolledige dag


def lees_data():
    if not DATA_FILE.exists():
        return {}
    tekst = DATA_FILE.read_text(encoding="utf-8").strip()
    if tekst.startswith(PREFIX):
        tekst = tekst[len(PREFIX):]
    return json.loads(tekst.rstrip(";"))


def schrijf_data(data):
    geordend = {k: data[k] for k in sorted(data)}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(PREFIX)
        json.dump(geordend, f, ensure_ascii=False)
        f.write(";")


def dag_onvolledig(dag, soort):
    return dag is None or len(dag.get(soort) or []) < MIN_REGELS.get(soort, 1)


def haal_meterdata(data, api_key):
    headers = {"API-Key": api_key, "Accept": "application/json"}
    r = requests.get(f"{BASE_URL}/connections", headers=headers, timeout=30)
    if r.status_code != 200:
        hint = ""
        if r.status_code in (401, 403):
            hint = (" -> Sleutel geweigerd. Controleer of de secret exact dezelfde sleutel bevat als SMP_API_KEY"
                    " in je .env, of dat Slimmemeterportal verzoeken vanaf GitHub-servers blokkeert.")
        sys.exit(f"Fout bij ophalen aansluitingen ({r.status_code}): {r.text[:200]}{hint}")
    connections = [c for c in r.json() if c.get("end_date") is None]
    print(f"Aansluitingen: {', '.join(c.get('connection_type', '?') for c in connections)}")

    gisteren = date.today() - timedelta(days=1)
    gewijzigd = 0
    for terug in range(TERUGKIJKEN_DAGEN):
        d = gisteren - timedelta(days=terug)
        sleutel = d.isoformat()
        for conn in connections:
            soort = conn.get("connection_type", "onbekend")
            if terug >= OPNIEUW_DAGEN and not dag_onvolledig(data.get(sleutel), soort):
                continue
            url = f"{BASE_URL}/connections/{conn.get('meter_identifier')}/usage/{d.strftime('%d-%m-%Y')}"
            resp = requests.get(url, headers=headers, timeout=30)
            time.sleep(1.1)  # rustig aan met de API
            if resp.status_code != 200:
                print(f"  {soort} {sleutel}: geen data ({resp.status_code})")
                continue
            usages = resp.json().get("usages", [])
            if not usages:
                print(f"  {soort} {sleutel}: leeg")
                continue
            dag = data.setdefault(sleutel, {"elektriciteit": [], "gas": [], "temp": None})
            if dag.get(soort) != usages:
                dag[soort] = usages
                gewijzigd += 1
                print(f"  {soort} {sleutel}: {len(usages)} regels bijgewerkt")
    return gewijzigd


def temp_onvolledig(t):
    return not t or t.get("gemiddeld") is None or len(t.get("uren") or {}) < 24 or any(v is None for v in t["uren"].values())


def haal_temperaturen(data):
    ontbrekend = sorted(d for d, info in data.items() if temp_onvolledig(info.get("temp")))
    if not ontbrekend:
        return 0
    bronnen = [
        ("https://archive-api.open-meteo.com/v1/archive", {"start_date": ontbrekend[0], "end_date": ontbrekend[-1]}),
        ("https://api.open-meteo.com/v1/forecast", {"past_days": 30, "forecast_days": 1}),  # archief loopt een paar dagen achter
    ]
    gewijzigd = 0
    for url, extra in bronnen:
        nog = [d for d in ontbrekend if temp_onvolledig(data[d].get("temp"))]
        if not nog:
            break
        params = {"latitude": LAT, "longitude": LON, "hourly": "temperature_2m",
                  "daily": "temperature_2m_mean", "timezone": "Europe/Amsterdam", **extra}
        try:
            js = requests.get(url, params=params, timeout=30).json()
        except Exception as e:  # temperatuur is bijzaak: nooit de hele update laten mislukken
            print(f"  Temperatuur ({url}) niet beschikbaar: {e}")
            continue
        uren = {}
        for t, v in zip(js.get("hourly", {}).get("time", []), js.get("hourly", {}).get("temperature_2m", [])):
            uren.setdefault(t[:10], {})[str(int(t[11:13]))] = v
        for d, gem in zip(js.get("daily", {}).get("time", []), js.get("daily", {}).get("temperature_2m_mean", [])):
            if d in nog and gem is not None:
                nieuw = {"gemiddeld": round(gem, 1), "uren": uren.get(d, {})}
                if not temp_onvolledig(nieuw) or temp_onvolledig(data[d].get("temp")):
                    data[d]["temp"] = nieuw
                    gewijzigd += 1
    print(f"Temperaturen bijgewerkt: {gewijzigd} dag(en)")
    return gewijzigd


def main():
    api_key = (os.getenv("SMP_API_KEY") or "").strip()
    # hele regel uit .env geplakt ("SMP_API_KEY=...")? Dan alleen het deel na '=' gebruiken
    if api_key.upper().startswith("SMP_API_KEY="):
        api_key = api_key.split("=", 1)[1].strip()
    api_key = api_key.strip('"').strip("'")
    print(f"API-sleutel: {len(api_key)} tekens")  # alleen de lengte, nooit de sleutel zelf
    if not api_key:
        sys.exit("SMP_API_KEY ontbreekt (GitHub-secret SLIMME_METER_RJE onder Settings > Secrets and variables > Actions).")
    data = lees_data()
    print(f"Bestaande data: {len(data)} dagen ({min(data, default='-')} t/m {max(data, default='-')})")
    n = haal_meterdata(data, api_key)
    n += haal_temperaturen(data)
    if n:
        schrijf_data(data)
        print(f"alle_data.js bijgewerkt ({n} wijzigingen), nu t/m {max(data)}")
    else:
        print("Geen wijzigingen.")


if __name__ == "__main__":
    main()
