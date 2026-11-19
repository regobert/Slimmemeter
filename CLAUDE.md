# Mijn Energie Dashboard — instructies voor Claude

## ▶️ Eerst doen bij de start van een nieuwe sessie

**Openstaande taak: Remeha Elga Ace-koppeling opzetten.** De gebruiker heeft gevraagd dit bij de
volgende start op te pakken. Meld aan het begin van de sessie dat je hiermee begint, tenzij de
gebruiker iets anders vraagt. Haal deze sectie weg zodra de taak is afgerond.

Plan (afgesproken met de gebruiker):
1. Vraag de gebruiker om twee GitHub-repository-secrets aan te maken (niet in de chat plakken!):
   `REMEHA_EMAIL` en `REMEHA_PASSWORD` (Settings → Secrets and variables → Actions → Repository secrets).
   Let op: bij `SLIMME_METER_RJE` werd eerder per ongeluk de hele `.env`-regel als waarde geplakt;
   vraag om alleen de waarde, en maak het script daar tolerant voor.
2. Er is geen officiële Remeha-API. Gebruik de (reverse-engineered) Remeha Home cloud-API zoals
   gedocumenteerd in https://github.com/msvisser/remeha_home (inlogflow en endpoints daar nalezen,
   niet uit het hoofd). Ook bruikbaar als referentie: de Homey-app "Remeha Home".
3. Schrijf `scripts/remeha.py` en voeg een stap toe aan `.github/workflows/energiedata.yml`
   (zelfde nachtelijke run). Doel: per dag het energieverbruik/de opgewekte warmte van de
   warmtepomp (verwarming en warm water) en, indien beschikbaar, COP. Sla op in een apart bestand
   (bijv. `remeha_data.js`), niet in `alle_data.js`.
4. Test eerst één handmatige run en bekijk wat de API teruggeeft vóór je het dashboard aanpast.
   Bekend risico: bij een hybride (Elga Ace) kan het energiecijfer gas en stroom combineren.
5. **Privacy:** de repository is openbaar. Bespreek met de gebruiker of warmtepompdata publiek
   mag staan voordat je data commit.
6. Daarna: verwerken in **📊 Inzichten** (warmtepompverbruik naast totale afname, COP per maand).
   Warmtepomp in gebruik sinds november 2023.

Alternatieven als de cloud-API niet werkt: slimme stekker (Shelly) op de buitenunit, of
Modbus-gateway GTW-08 (houthacker/remeha-modbus).

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
