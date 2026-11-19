# Mijn Energie Dashboard — instructies voor Claude

## Remeha Elga Ace (warmtepomp) — afgerond

- `scripts/remeha.py` logt in op de (onofficiële) Remeha Home cloud-API (aanpak van
  msvisser/remeha_home) en schrijft dagwaarden naar `remeha_data.js`
  (`window.REMEHA_DATA = {"JJJJ-MM-DD": {in, uit, wp_in, wp_uit, ketel_in, ketel_uit, ketel_ww_in, ...}}`, kWh;
  wp = warmtepomp/stroom, ketel = cv-ketel/gas, *_in = verbruikt, *_uit = geleverde warmte).
- Draait als stap in `energiedata.yml` (`continue-on-error`), secrets `REMEHA_EMAIL` / `REMEHA_PASSWORD`.
  `remeha-test.yml` = handmatige test die alleen structuur logt (Actions-logs zijn openbaar).
- De gebruiker heeft gekozen: warmtepompdata mag openbaar in de repository (net als de meterdata).
- Weergave: 📊 Inzichten → "Warmtepomp (Remeha)" (aandeel WP, COP, WP-stroom t.o.v. afname, ketelgas).
- Warm water komt bij deze hybride van de cv-ketel (hotWater-velden zijn 0).

## Project in het kort

- Statische site via GitHub Pages: `https://regobert.github.io/Slimmemeter/` (branch `main`).
- `index.html`: één bestand met CSS + JS (Chart.js, PDF.js, SheetJS lazy via cdnjs). **CRLF-regeleinden**;
  behoud die bij bewerken. UI-teksten in het Nederlands.
- `alle_data.js`: `window.ENERGIE_DATA = { "YYYY-MM-DD": { elektriciteit: [...96 kwartieren], gas: [...24 uren], temp: {gemiddeld, uren} } }`.
  Getallen als Nederlandse tekst (`"0,02"`), `time` = einde van het interval. Velden:
  `delivery_high/low`, `returned_delivery_high/low`, gas `delivery`.
- `scripts/update_data.py` + `.github/workflows/energiedata.yml`: dagelijks 02:07 (wintertijd) via
  GitHub Actions; secret `SLIMME_METER_RJE` (Slimmemeterportal API-sleutel). De Windows-taakplanner
  van de gebruiker staat uit (die overschreef eerder `index.html` met een oude versie).

## Belangrijke afspraken

- **Persoonlijke gegevens nooit in de repository**: contracten, tarieven, termijnen en Excel-historie
  staan alleen in `localStorage` van de browser (`energie_contracts_v1`, `energie_termijnen_v1`,
  `energie_hist_v1`, `energie_histtemp_v1`, `energie_gd_v1`, `energie_wp_v1`, `energie_theme_v2`).
  Overzetten tussen apparaten gaat via back-up/contractbestanden (.json) in de app.
- Kostenmodel: saldering per contract (`auto` = per contractjaar t/m 31-12-2026, daarna per dag;
  `jaar`; `dag`; `geen` = dynamisch, afname en teruglevering elk tegen eigen maandtarief).
  Maandtarieven per contract (`maandTarieven["YYYY-MM"]`) overschrijven de vaste tarieven.
- Contractnamen worden automatisch gemaakt: leverancier + maand/jaar van de start.
- Bij twijfel over cijfers: vergelijk met de echte nota's; verschil van ~2% op gas komt door de
  calorische correctie (nota's) versus ruwe m³ (Excel/meter).

## Werkwijze

- Test wijzigingen met Playwright (Chromium is voorgeïnstalleerd). CDN's zijn in de sandbox
  geblokkeerd: route `chart.umd.min.js`, `xlsx.full.min.js`, `pdf.min.js`/`pdf.worker.min.js`
  naar lokale npm-pakketten (chart.js@4.4.3, xlsx@0.18.5, pdfjs-dist@3.11.174).
- De gebruiker wil wijzigingen direct live op `main` (fast-forward). Shallow clone: als git een
  push ten onrechte als non-fast-forward weigert, controleer `.git/shallow`.
- Commits als `regobert <regobert@users.noreply.github.com>`.
