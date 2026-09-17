# Speelagenda VVZ'49 JO14-6

Automatisch bijgewerkte agenda-feed (.ics) voor **ST SO Soest/VVZ'49 O14-6**
(de combinatie tussen SO Soest en VVZ'49), voor gebruik als abonnement in
Google Calendar (of Apple/Outlook).

## Wat staat er in de agenda

- **Verzamelen: …** — van verzameltijd tot aanvangstijd
- **Speeltijden**
- **Thuisteam - Uitteam** — de wedstrijd zelf, incl. scheidsrechter en veld

## Hoe te gebruiken in Google Calendar

1. Ga naar https://calendar.google.com/calendar/r/settings/addbyurl
2. Plak de URL: `https://thewally.github.io/vvz49-jo14-6-agenda/matches.ics`
3. Klik op **Agenda toevoegen**

De agenda wordt elke ochtend en avond automatisch bijgewerkt. Google
Calendar ververst de feed vervolgens op zijn eigen tempo (meestal binnen
12-24 uur).

## Achtergrond

Geen betaalde Voetbal.nl-app nodig: dit gebruikt de publieke widget-API
die SO Soest's eigen website (so-soest.nl) ook gebruikt om standen en
programma te tonen. Zie `scrape.py` voor details.

De Sportlink-widget `client_id` staat in de repository secret
`SPORTLINK_CLIENT_ID` (lokaal: zet 'm in de gelijknamige omgevingsvariabele)
-- niet in de code.

## Beperkingen

- Werkt alleen zolang SO Soest dezelfde publieke `client_id` gebruikt op
  hun website. Als dat ooit wijzigt, moet de secret `SPORTLINK_CLIENT_ID`
  worden bijgewerkt (opnieuw op te zoeken in de bron van
  `https://www.so-soest.nl/assets/js/global.js`).
- Zoekt elke run automatisch de actuele teamcode/poule op, dus werkt door
  wanneer de KNVB halverwege het seizoen een nieuwe competitiefase indeelt.
