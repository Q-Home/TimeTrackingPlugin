# Versie 1.2.6 — lege dagen aanvullen

HR en beheerders kunnen bij elke verstreken dag in **Urenoverzicht → medewerker → Dagdetails** op **Registratie toevoegen** klikken. Dat kan ook wanneer er nog geen START of STOP bestaat. De bestaande algemene knop **Registratie aanvullen** boven de dagdetails blijft beschikbaar.

## Gewerkt zonder te klokken

1. Open de betrokken dag en klik op **Registratie toevoegen**.
2. De datum van die dag is ingevuld. Kies **START**, vul de werkelijk gewerkte begintijd en een reden in en sla op.
3. Klik op dezelfde dag opnieuw op **Registratie toevoegen**. Bij een open sessie staat **STOP** voorgeselecteerd.
4. Vul de werkelijke eindtijd en reden in en sla op. Voeg indien nodig ook **BREAK** en **RETURN** toe.

De tijd blijft bij een nieuwe registratie bewust leeg en is verplicht. Er wordt geen fictieve werkdag van acht uur ingevuld. Een START zonder STOP blijft een onvolledige sessie; beide handelingen worden afzonderlijk opgeslagen en zijn zichtbaar in de wijzigingshistoriek. De gekozen dag blijft na opslaan open. De ingestelde afronding en pauzeregels gelden ook voor handmatige registraties.

## Een bestaande registratie verbeteren

Klik naast een bestaande START, STOP of pauzeregistratie op **Corrigeren / controleren**. Datum en tijd worden uit die registratie overgenomen. Pas ze aan en geef een reden. Je kunt zo ook een automatisch aangemaakte STOP na controle bevestigen of corrigeren. De bronregistratie blijft bewaard; de correctie bepaalt vervolgens de berekening.

## Niet gewerkt: verlof of afwezigheid

Voeg geen werkuren toe wanneer de medewerker niet gewerkt heeft. Gebruik **HR-instellingen → Kalender & afwezigheid → Individuele afwezigheid** en kies medewerker, datum/periode en invloed op de norm. Voor een volledige verlofdag kan de norm nul worden; voor gedeeltelijke afwezigheid stel je de resterende verwachte netto-uren in. Een structureel afwijkend werkregime hoort in een persoonlijk rooster.

## Bevoegdheden en afgesloten uren

Alleen HR en beheerders met HR-rechten kunnen rechtstreeks corrigeren. Technisch beheer krijgt hierdoor geen extra HR-rechten; medewerkers kunnen nog steeds niet aanmelden. Bij een goedgekeurde periode blijft expliciet intrekken van de goedkeuring vereist. Een afgesloten periode moet eerst met reden worden heropend; de knop op de dag is dan uitgeschakeld met uitleg. De server blijft deze regels ook bij rechtstreekse aanvragen controleren.

Na installatie van versie 1.2.6: vernieuw de pagina met **Ctrl+F5**. Screenshots en browsercontroles gebruiken alleen synthetische medewerkers en registraties; er zijn geen productie-uren aangepast.

De installatie-ZIP bevat de lokaal gegenereerde voorbeeldbeelden in `docs/screenshots/empty-day-add-registration.png`, `add-day-registration-form.png` en `corrected-day-registration.png`. De beelden zijn niet naar GitHub gepubliceerd.
