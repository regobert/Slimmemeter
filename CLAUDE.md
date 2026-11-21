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
  `energie_hist_v1`, `energie_histtemp_v1`, `energie_gd_v1`, `energie_wp_v1`, `energie_theme_v2`,
  `energie_welkom_v1` = startpaneel verborgen).
  Overzetten tussen apparaten gaat via back-up/contractbestanden (.json) in de app.
- Kostenmodel: saldering per contract (`auto` = per contractjaar t/m 31-12-2026, daarna geen saldering (`geen`);
  `jaar`; `dag`; `geen` = dynamisch, afname en teruglevering elk tegen eigen maandtarief).
  Maandtarieven per contract (`maandTarieven["YYYY-MM"]`) overschrijven de vaste tarieven.
- Contractnamen worden automatisch gemaakt: leverancier + maand/jaar van de start.
- Contractveld `soort`: `vast` (maandTarieven worden genegeerd en verborgen), `variabel`, `dynamisch`.
  Bij een vast contract neemt "E-mail plakken" geen tarieven over, alleen termijnbedragen.
- Bij twijfel over cijfers: vergelijk met de echte nota's; verschil van ~2% op gas komt door de
  calorische correctie (nota's) versus ruwe m³ (Excel/meter).

## Demo / nieuwe gebruikers

- Startpaneel (`#welcomeCard`, knop ❓ "Hoe begin ik?") met stappen: meterdata, contract, termijn,
  optioneel maandtarieven/Excel-historie/Inzichten. Verschijnt vanzelf zolang er geen eigen contract is.
- Nieuwe gebruiker krijgt een contract met `placeholder: true` (voorbeeldtarieven, melding `#exampleNote`);
  `commit()` verwijdert het zodra er een eigen contract is.
- 📊 Inzichten → "Besparingen": teruglevering = −credit − terugleverkosten per jaar; warmtepomp =
  WP-warmte ÷ (9,77 × 90% ketelrendement) × gasprijs − WP-stroom × gem. normaal/dal (alleen dagen met WP/ketel-splitsing).

- Demomodus (`energie_demo_v1` = {months, stop, wp}): knop "🎬 Bekijk eerst de demo" in het startpaneel of de link
  `?demo` (alleen als er nog geen eigen contract/historie is). Laadt 5 contracten "Voorbeeld Energie" (`demo: true`)
  en verzonnen maandhistorie vanaf 2022 tot de eerste meterdag, afgeleid van de echte Remeha-data; zet WP-start 2023-11.
  Blauwe demobalk met "Demo stoppen"; het eerste eigen contract ruimt de demo ook op (`commit()`).

## Werkwijze

- Test wijzigingen met Playwright (Chromium is voorgeïnstalleerd). CDN's zijn in de sandbox
  geblokkeerd: route `chart.umd.min.js`, `xlsx.full.min.js`, `pdf.min.js`/`pdf.worker.min.js`
  naar lokale npm-pakketten (chart.js@4.4.3, xlsx@0.18.5, pdfjs-dist@3.11.174).
- De gebruiker wil wijzigingen direct live op `main` (fast-forward). Shallow clone: als git een
  push ten onrechte als non-fast-forward weigert, controleer `.git/shallow`.
- Commits als `regobert <regobert@users.noreply.github.com>`.
