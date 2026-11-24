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
- Omslagpunt WP → ketel (analyse 24 nov 2026, Open-Meteo-uurtemperatuur Hengelo + Remeha-dagdata mrt 2024–nov 2026):
  ketel neemt het over onder ca. +1,5 à +2 °C buiten (beste fit 2024/25 +1,5, 2025/26 +2,0; nachturen: <2 °C gas in 56–75% van de uren,
  2–3 °C 6%, >3 °C 0%). Daarnaast ketel bij grote vraag (ochtend-opwarmen) ook bij 2–6 °C. WP levert max ca. 80–97 kWh warmte/dag.
  Open-Meteo-hosts staan in de cloud-omgeving "Slimmemeter".
- In het dashboard: Inzichten → "Omslagpunt" (`renderSwitch`, `#swBox`): zelfde methode per stookseizoen in de browser;
  uurtemperaturen Open-Meteo gecachet in `energie_uurtemp_v1`; omslagpunt alleen bij ≥10 dagen < 8 °C en ≥5 dagen < 3 °C.
  Grafiekkeuze (`#swSel`, `energie_swsel_v1`): lopend seizoen, beste/slechtste (per temperatuurklasse min/max over volledige
  seizoenen met omslagpunt, tooltip noemt het seizoen) en losse seizoenen; standaard lopend + beste + slechtste.

## Experiment nachtverlaging (lopend)

- Thermostaat (Remeha, Zone1): week 1 = zo 22 nov t/m za 28 nov 2026 met verlaging: 18,5 °C van 21:00 tot 07:30, 19,5 °C overdag.
  Week 2 = zo 29 nov t/m za 5 dec: dag en nacht 19,5 °C. Daarna vergelijken (ketelgas 05–09 u, ketel_in, WP-stroom, per graaddag, in euro's).
- Uitgangspunt uit de analyse van 20 okt–21 nov: warmte/dag ≈ 104 − 6,6 × T_buiten kWh (≈ 274 W/K), COP nov 4,2;
  op koude dagen ~1 m³ extra ketelgas tussen 05 en 09 u.

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

- **Eerst vragen bij extra kosten**: bouw niets dat de gebruiker (doorlopend) geld kost (betaalde API's zoals de Anthropic API,
  abonnementen, hosting) zonder dat vooraf voor te leggen. Een "Vraag het Claude"-knop met eigen API-sleutel is daarom weer verwijderd.
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

- Startpaneel (`#welcomeCard`, knop ❓ "Hoe begin ik?") is een stap-voor-stap-hulp (één vraag per keer, `energie_wizard_v1` = stap 0–3):
  welkom → contract-PDF (wordt direct uitgelezen en opgeslagen, zonder het contractvenster; PDF zonder stroomprijs wordt geweigerd)
  → maandbedrag → klaar (extra's ingeklapt). Bedoeld voor gebruikers die snel denken dat iets te technisch is: gewone taal, alles overslaanbaar.
  Verschijnt vanzelf zolang er geen eigen contract is, en blijft staan tot "Naar mijn overzicht" of ✕.
- Verbruiksbron (`energie_bron_v1`): standaard `site` (alle_data.js/remeha_data.js van de eigenaar). Stap 1 van de hulp vraagt
  "Wil je je eigen verbruik zien?" → `eigen`: ENERGIE_DATA en REMEHA_DATA worden genegeerd, alleen geüploade Excel-maanden (`hist`)
  tellen, start in jaaroverzicht. Te wijzigen in Historie & back-up (`#bronSelect`) en meegenomen in de back-up (`bron`).
  Slimmemeterportal-API kan niet vanuit de browser (geen CORS) → voor een App Store-versie is een eigen server of native app nodig.
- Nieuwe gebruiker krijgt een contract met `placeholder: true` (voorbeeldtarieven, melding `#exampleNote`);
  `commit()` verwijdert het zodra er een eigen contract is.
- Inzichten: tabellen standaard ingeklapt (`details.ins-tbl`). Besparingsgrafiek zoomt in met een tik: jaren → maanden → dagen
  (`saveView`, navigatie `#saveNav`); de kaartjes erboven volgen de gekozen periode.
  Bladeren met ‹ › (`saveStep`), vegen op de grafiek of pijltjestoetsen: per jaar (maandweergave) of per maand (dagweergave).
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
