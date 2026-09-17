# JO14-6 agenda

Automatisch bijgewerkte agenda-feed (.ics) voor **ST SO Soest/VVZ'49 O14-6**
(de combinatie tussen SO Soest en VVZ'49), voor gebruik als abonnement in
Google Calendar (of Apple/Outlook).

Geen betaalde Voetbal.nl-app nodig: dit gebruikt de publieke widget-API
die SO Soest's eigen website (so-soest.nl) ook gebruikt om standen en
programma te tonen. Zie `scrape.py` voor details.

Per wedstrijd staan er (zodra de KNVB de verzameltijd publiceert, meestal
1-2 weken van tevoren) twee agenda-items:

- **Verzamelen: ...** — van verzameltijd tot aanvangstijd
- **Thuisteam - Uitteam** — de wedstrijd zelf, incl. scheidsrechter en veld

## Hoe toevoegen aan Google Calendar

1. Ga naar https://calendar.google.com/calendar/r/settings/addbyurl
2. Plak de URL naar `matches.ics` in deze repo (raw.githubusercontent.com-link)
3. Klik op **Agenda toevoegen**

De agenda wordt elke ochtend en avond automatisch bijgewerkt via GitHub
Actions (`.github/workflows/update.yml`); Google Calendar ververst de feed
vervolgens op zijn eigen tempo (meestal binnen 12-24 uur).

## Beperkingen

- Werkt alleen zolang SO Soest dezelfde publieke `client_id` gebruikt op
  hun website. Als dat ooit wijzigt, moet `CLIENT_ID` in `scrape.py`
  worden bijgewerkt (opnieuw op te zoeken in de bron van
  `https://www.so-soest.nl/assets/js/global.js`).
- Zoekt elke run automatisch de actuele poulecode op, dus werkt door
  wanneer de KNVB halverwege het seizoen een nieuwe competitiefase indeelt.
