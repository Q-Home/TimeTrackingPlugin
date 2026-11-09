# TimeTrackingPlugin — functies en uitbreidingsmogelijkheden

**Stand van zaken: 5 november 2026**  
**Doel:** een overzicht van de huidige mogelijkheden, de beperkingen en zinvolle volgende stappen.

## 1. Samenvatting

De plugin vormt een basis voor badgegestuurde tijdregistratie en aanwezigheidsopvolging binnen een LoxBerry/Loxone-omgeving. Badge-events komen via MQTT binnen, worden via een API in MongoDB opgeslagen en verschijnen in een webapplicatie. Beheerders kunnen gebruikers beheren en aanwezigheid opvolgen. Medewerkers kunnen hun eigen uren en profiel raadplegen.

Er is al ondersteuning voor werk- en pauzetijden, week- en maandoverzichten, grafieken en CSV-export. Verdere ontwikkeling kan zich vooral richten op betrouwbare registratie, correctie en goedkeuring van uren, instelbare werkroosters en rapportering.

**Leeswijzer:** “aanwezig” betekent dat de functie terug te vinden is in de actieve applicatiecode. Dit is geen bevestiging van een geslaagde praktijktest. De lokale Docker-engine was niet beschikbaar en de lokale omgevingsconfiguratie ontbrak; de applicatie is voor dit overzicht niet draaiend getest. De analyse volgt de webapp, de modulaire backend die via `run:app` wordt gestart, de MQTT-service en de LoxBerry-beheerpagina’s. Losse oudere backendbestanden zijn niet als actieve functionaliteit meegeteld.

## 2. Wat kan de plugin al?

### 2.1 Aanmelden en rollen

| Mogelijkheid | Huidige werking |
| --- | --- |
| Aanmelden | Met gebruikersnaam of e-mailadres en wachtwoord. |
| Rollen | Twee rollen: beheerder (`admin`) en medewerker (`user`). |
| Persoonlijke omgeving | Medewerkers worden naar hun eigen timesheet geleid; beheerders naar het dashboard. |
| Eigen gegevens | Een medewerker kan het eigen profiel en wachtwoord wijzigen. Rol, badgecode en blokkeerstatus zijn voor beheerders voorbehouden. |
| Geblokkeerde accounts | Een geblokkeerde gebruiker kan niet opnieuw aanmelden. Zie §4 voor de beperking rond bestaande sessies en badge-events. |
| Sessie | De API gebruikt JWT-tokens; de standaard tokenlooptijd in de code is twaalf uur. Afmelden wist de lokale sessiegegevens. |
| Wachtwoorden | Wachtwoorden worden met bcrypt gehasht opgeslagen. |

### 2.2 Gebruikersbeheer

Beheerders beschikken over een gebruikerslijst met zoeken, sorteren en paginering. Van daaruit kunnen ze een account bewerken of de timesheet van een gebruiker openen.

| Mogelijkheid | Huidige werking |
| --- | --- |
| Gebruikers toevoegen | Account aanmaken met onder meer naam, gebruikersnaam, e-mail, bedrijf, wachtwoord, rol en badgecode. |
| Gebruikers bewerken | Profielgegevens, badgecode, rol en blokkeerstatus aanpassen. |
| Blokkeren en deblokkeren | Via de webapp en aparte API-routes. |
| Verwijderen | Een gebruikersaccount verwijderen. Historische badge-events worden daarbij niet automatisch verwijderd. |
| Wachtwoord instellen | Eigen wachtwoord wijzigen of als beheerder dat van een gebruiker aanpassen. |
| Extra velden | Een beheerder kan aanvullende profielvelden als JSON beheren. Er is nog geen formulierbouwer voor deze velden. |
| Activiteitsinformatie | Aantal scans, eerste en laatste activiteit en gebruikte badgecodes tonen. |
| Gebruikers exporteren | CSV-export vanuit de gebruikerslijst. |

De lijst combineert geregistreerde accounts met gebruikersnamen uit historische badge-events. Daardoor kunnen ook personen zonder huidig account in de lijst voorkomen.

### 2.3 Badge-registratie en MQTT

| Mogelijkheid | Huidige werking |
| --- | --- |
| MQTT ontvangen | Badge-events ontvangen op een configureerbaar topic, met configureerbare broker en aanmeldgegevens. |
| Berichtformaten | JSON-objecten en het oudere formaat `badgecode;username;scan_time;action`. |
| Tijdstippen verwerken | ISO-tijdstippen verwerken en omzetten met ondersteuning voor `Europe/Brussels`. |
| Registraties opslaan | Badgecode, gebruiker, actie, tijdstip, locatie, toestel en eventueel ruwe data opslaan via de backend. |
| Terugkoppeling | Een vereenvoudigd bericht publiceren op een configureerbaar MQTT-topic voor Loxone. Dit is geen bevestiging dat de registratie succesvol is opgeslagen; zie §4. |
| Badge-overzicht | Registraties tonen met actie, gebruiker, tijdstip en toestel. |
| Filters | Filteren op gebruiker, badgecode, dag, maand en datumgrenzen. |
| Paginering | Registraties in pagina’s ophalen; de API laat maximaal honderd records per pagina toe. |
| Export | De geladen badgegegevens als CSV downloaden, eventueel met filterinformatie. |

De volgende acties zijn voorzien:

| Actie | Betekenis voor de urenberekening |
| --- | --- |
| `START` / `SCAN_IN` | Werkperiode starten. |
| `BREAK` | Werkperiode onderbreken en pauze starten. |
| `RETURN` | Pauze beëindigen en werk hervatten. |
| `STOP` / `SCAN_OUT` | Werkperiode beëindigen. |
| `SCAN` | Algemene registratie; telt op zichzelf geen werkuren. |

De API bevat daarnaast mogelijkheden om een registratie aan te maken, te wijzigen of te verwijderen en om meerdere registraties als verwerkt te markeren. Voor deze bewerkingen is in het onderzochte badge-overzicht geen volledige beheerinterface aangesloten. “Verwerkt” is momenteel een technisch kenmerk, zonder uitgewerkte goedkeuringsprocedure.

### 2.4 Aanwezigheidsdashboard

Het beheerdersdashboard toont op basis van badge-events:

- Aantal aanwezigen, personen in pauze en personen met activiteit vandaag.
- Bezettingspercentage tegenover het aantal geregistreerde accounts.
- Aantal scans, starts en stops vandaag en scans in het laatste uur.
- Een lijst met aanwezige personen, hun laatste actie en locatie.
- Aanwezigheid per locatie en recente badge-activiteit.

Het dashboard laadt bij openen en kan handmatig worden vernieuwd. De API beperkt de getoonde personen tot acht, de locaties tot zes en de recente activiteiten tot acht. De totaaltellers worden vóór deze beperking berekend.

Dit is een afgeleide aanwezigheid op basis van registraties. Een gemiste scan of een open dienst van de vorige dag kan het beeld onvolledig maken.

### 2.5 Urenberekening en timesheets

| Mogelijkheid | Huidige werking |
| --- | --- |
| Werk- en pauzetijd | Berekenen uit opeenvolgende start-, pauze-, hervat- en stopacties. Meerdere werk- en pauzeperiodes op dezelfde dag zijn mogelijk. |
| Dagberekening | De API kan de uren van één gebruiker op één dag berekenen. |
| Periodeberekening | De API kan een vrij datumbereik berekenen, inclusief dagen zonder events. |
| Week- en maandweergave | De webapp biedt de laatste twaalf weken en twaalf maanden als keuzelijst. |
| Samenvatting | Totale werktijd, pauzetijd, gewerkte dagen en gemiddelde werktijd per gewerkte dag. |
| Dagdetails | Eerste start, laatste stop, pauzetijd, werktijd en status van de dag. |
| Grafieken | Dagelijkse uren en een verdeling van normale, ontbrekende en overuren. De normen zijn nog vast geprogrammeerd; zie §4. |
| Open registraties | De berekening geeft aan of iemand nog werkt of in pauze is. |
| Onlogische acties | De backend verzamelt fouten, zoals twee starts na elkaar of een stop zonder start. Deze foutmeldingen worden niet volledig in de timesheettabel getoond. |
| Eigen inzage | Een medewerker mag via de timesheet-API alleen de eigen uren opvragen; een beheerder kan die van andere gebruikers bekijken. |
| Export | CSV van de dagtotalen en een afzonderlijke CSV met de onderliggende tijdregistratie-events. |

**Voorbeeld:** `START 08:00 → BREAK 12:00 → RETURN 12:30 → STOP 16:30` geeft acht uur werktijd en dertig minuten pauze.

### 2.6 Logs en technisch beheer

| Onderdeel | Aanwezige mogelijkheden |
| --- | --- |
| Systeemlogs in de webapp | Zoeken, filteren op logtype, pagineren, CSV-export en afdrukken via de browser. Bovenaan **Logs** kunnen beheerders ook de actieve MQTT-instellingen en de laatste 30 gebeurtenissen sinds de start van de listener bekijken, zoals verbinding, ontvangst van een badge-event en resultaat van de API-opslag. Het MQTT-wachtwoord wordt alleen als ingesteld of niet ingesteld getoond. |
| LoxBerry-startpagina | Gebruikers opvragen en toevoegen, API-verbinding testen en backend-URL en interne API-sleutel instellen. De statuswissel op deze pagina heeft een aansluitingsprobleem; zie §4. |
| LoxBerry-instellingen | Docker-containers starten, stoppen, herstarten en hun status opvragen. |
| Configuratie bewerken | Instellingen-JSON en Docker Compose als ruwe tekst aanpassen. |
| Technische logs | Docker-, MQTT- en applicatielogs bekijken en leegmaken. Bij **Logs → Diagnose Miniserver-koppeling** staan de listenerstatus, broker, topics en MQTT-gebruikersnaam. De pagina toont alleen of een wachtwoord is ingesteld. De containeruitvoer verbergt herhaalde heartbeats; de pagina vernieuwt om de dertig seconden. |
| Healthcheck | API-route die de databaseverbinding test. |
| API-documentatie | Swagger-interface onder `/docs/` en een specificatie onder `/apispec.json`. Niet alle routes hebben even uitgebreide beschrijvingen. |
| Installatie | LoxBerry-installatiescripts en Docker Compose voor MongoDB, MQTT-listener, Flask-backend en Nginx-webapp. MongoDB gebruikt een persistent volume. |
| Demodata | Een script kan via de API voorbeeldgebruikers en registraties genereren. `test.py` start dit script en is geen automatische testsuite. |

## 3. Overzicht per gebruiker

| Taak | Medewerker | Beheerder |
| --- | --- | --- |
| Eigen uren bekijken en exporteren | Ja | Ja |
| Uren van anderen bekijken en exporteren | Nee | Ja |
| Eigen profiel en wachtwoord wijzigen | Ja, beperkte velden | Ja |
| Gebruikerslijst en gebruikersbeheer | Nee | Ja |
| Aanwezigheidsdashboard bekijken | Nee | Ja |
| Badge-overzicht en systeemlogs via het menu | Verborgen / afgeschermd als beheerpagina | Ja |
| Correcties goedkeuren of een maand afsluiten | Nog niet aanwezig | Nog niet aanwezig |

Deze tabel beschrijft de schermen en de bedoelde gebruikersstromen. De API-rechten voor badgegegevens zijn momenteel ruimer: een geldig medewerkerstoken kan badge-events lezen, toevoegen en wijzigen zonder beperking tot de eigen gebruiker. Het verbergen van een menu-item biedt daarvoor geen API-afscherming.

## 4. Wat is nog beperkt of gedeeltelijk aangesloten?

| Onderwerp | Vaststelling uit de code | Gevolg / gewenste verbetering |
| --- | --- | --- |
| Rechten op badge-events | Lezen, aanmaken en wijzigen vereisen een geldig token of, waar voorzien, intern vertrouwen; er is geen controle op eigenaarschap bij deze badgebewerkingen. Verwijderen en bulkverwerking vereisen wel een beheerder. | De rechten per actie en per gebruiker expliciet vastleggen en afdwingen. |
| Blokkeren | De login controleert de blokkeerstatus. Bestaande tokens en inkomende badge-events controleren die status niet opnieuw. | Onderscheid maken tussen een account blokkeren, een sessie intrekken en een badge deactiveren. |
| MQTT-statistieken | De listener roept `/api/v1/badges/search` aan; die route ontbreekt in de actieve backend. Er wordt ook geen statistiekantwoord gepubliceerd. | Deze functie is nog niet bruikbaar als volledige aanvraag/antwoordkoppeling. |
| Geweigerde toegang | De listener herkent `Access Denied`, maar bouwt daarvoor een event zonder badgecode en met actie `none`; de backend accepteert dit niet. | Een apart, geldig eventtype voor geweigerde toegang uitwerken. |
| Bevestiging en uitval | De MQTT-terugkoppeling wordt ook na een mislukte API-opslag gepubliceerd. Een duurzame wachtrij en bescherming tegen dubbele events ontbreken. | Opslagresultaat terugmelden, mislukte events bewaren en veilig opnieuw aanbieden. |
| Bron van het tijdstip | Bij een JSON-event zonder `scan_time` vult de listener dat veld met de huidige tijd, ook als `timestamp` is meegegeven. Daarna krijgt `scan_time` voorrang. | Eén eenduidige afspraak voor tijdstippen gebruiken, zodat het originele scantijdstip behouden blijft. |
| Nachtdiensten en open uren | De urenberekening begint iedere kalenderdag opnieuw. Een open werk- of pauzeperiode wordt niet tot het huidige tijdstip opgeteld. | Sessies over middernacht ondersteunen en duidelijk tonen welke uren voorlopig zijn. |
| Volledigheidsstatus | `is_complete` betekent dat de eindstatus `idle` is. Dat kan ook gelden voor een lege dag of een dag met onlogische events. | Onderscheid maken tussen geen registratie, correct afgesloten en fouten aanwezig. |
| Overuren en tekorten | De daggrafiek gebruikt acht uur als grens. De verdelingsgrafiek rekent met acht uur per kalenderdag, inclusief weekends. | Geen betrouwbare contractuele overurenbalans; roosters en werkdagkalender toevoegen. |
| Tijdzone dashboard | Het dashboard gebruikt de serverdatum voor daggrenzen; timesheets gebruiken Belgische daggrenzen omgerekend naar UTC. | Eén tijdzonebeleid toepassen, vooral rond middernacht en zomer-/wintertijd. |
| Maandfilter badges | Het maandfilter gebruikt het maandnummer zonder jaar; de UI-keuze van een jaar-maand wordt teruggebracht tot een maandnummer. | Bij meerdere jaren data kunnen maanden worden gecombineerd. Filteren op een volledig datumbereik. |
| Badge-export | De CSV gebruikt alleen de records van de geladen pagina. | Een export over alle resultaten van de gekozen filters aanbieden. |
| Historische identiteit | Uren worden op gebruikersnaam opgezocht. Een naamswijziging werkt historische events niet bij; verwijderen van een account laat events staan. | Een vaste gebruikers-ID gebruiken en afspraken maken voor historiek en archivering. |
| LoxBerry-statuswissel | De PHP-startpagina gebruikt een gebruikersnaam in een PUT-route die een gebruikers-ID verwacht. | De statusknop op deze pagina aansluiten op de juiste route. |
| Configuratie en toegang | De webapp gebruikt vaste HTTP-aanroepen naar poort 5000; de meegeleverde Compose publiceert MongoDB op poort 27017 zonder ingestelde authenticatie. De code bevat standaardwaarden voor admin en sleutels. Intern vertrouwen kan ook alleen op subnet gebaseerd zijn. | Installatieconfiguratie, toegangsgrenzen en verbindingen vóór ingebruikname expliciet instellen en controleren. |

Dit zijn bevindingen uit code-inspectie. De precieze impact op een geïnstalleerde LoxBerry hangt af van de configuratie en moet daar worden getest.

## 5. Welke functies kunnen erbij?

De prioriteiten hieronder zijn voorstellen. **Hoog** ondersteunt betrouwbare dagelijkse registratie; **middel** maakt beheer en rapportering handiger; **later** hangt sterker af van de concrete behoefte. De omvang is relatief en geen tijdsinschatting.

| Uitbreiding | Wat levert dit op? | Prioriteit | Omvang |
| --- | --- | --- | --- |
| Betrouwbare eventverwerking | Events bewaren bij uitval, automatisch opnieuw aanbieden, dubbele berichten herkennen en opslag bevestigen. | Hoog | Groot |
| Correcties met historiek | Een vergeten start, stop of pauze herstellen, met reden, oorspronkelijke waarde en verantwoordelijke. | Hoog | Middel |
| Overzicht van afwijkingen | Eén werklijst met ontbrekende stops, dubbele starts en andere onlogische registraties. | Hoog | Middel |
| Werkroosters en contracturen | Normuren per persoon en weekdag, deeltijds werk, weekends en feestdagen correct verwerken. | Hoog | Groot |
| Nachtdiensten | Eén doorlopende sessie correct over kalenderdagen verdelen. | Hoog | Middel–groot |
| Duidelijk badgebeheer | Meerdere badges per persoon, badge vervangen, verloren badge intrekken en geldigheidsperiodes beheren. | Middel | Middel |
| Goedkeuringsprocedure | Medewerker vraagt een correctie aan; beheerder keurt goed of af. Goedgekeurde maanden kunnen worden afgesloten. | Middel | Groot |
| Herinneringen | Een melding bij een vergeten uitklok, een lange open sessie of een serviceprobleem. | Middel | Middel |
| Rapporten voor alle medewerkers | Volledig periodeoverzicht, totalen per bedrijf/team en volledige CSV-export; eventueel XLSX of PDF. | Middel | Middel |
| Automatisch vernieuwd dashboard | Actuele aanwezigheid zonder handmatige verversing, met volledige personenlijst en filters. | Middel | Middel |
| Back-up en herstel | Geplande databaseback-ups en een geteste herstelprocedure. Een Docker-volume alleen is geen back-up. | Hoog | Middel |
| Instellingenformulier | MQTT, locaties, tijdzone en verbindingen via gevalideerde velden instellen, met verbindingstest. | Middel | Middel |
| Sessiebeheer en accountherstel | Actieve sessies intrekken, wachtwoord vergeten, verplichte eerste wachtwoordwijziging en eventueel tweestapsverificatie. | Middel | Middel–groot |
| Teams en leidinggevenden | Een leidinggevende ziet en beoordeelt alleen de eigen medewerkers. | Later | Groot |
| Verlof en afwezigheden | Verlof, ziekte en andere afwezigheid apart registreren en meenemen in de verwachte uren. | Later | Groot |
| Projecten en taken | Werktijd toewijzen aan een project, klant of activiteit. | Later | Groot |
| Externe koppelingen | Gecontroleerde export of API-koppeling met loonverwerking, HR of boekhouding. | Later | Groot |
| Mobiel inklokken | Een mobiele weergave of kiosk om zonder fysieke badge te starten en stoppen, met passende rechten. | Later | Middel–groot |
| Bewaartermijnen en archivering | Persoonsgegevens, badge-events en logs volgens ingestelde termijnen archiveren of verwijderen. | Middel | Middel |
| Consistente taal | De huidige mix van Nederlands en Engels vervangen door een uniforme taalkeuze. | Later | Klein–middel |

## 6. Aanbevolen volgorde

### Stap 1 — De bestaande basis betrouwbaar maken

Rechten op badge-events aanscherpen, account- en badgeblokkering onderscheiden en de ontbrekende MQTT/PHP-aansluitingen oplossen. Daarna eventopslag, tijdstippen, tijdzones en volledige exports consistent maken. Voeg gerichte automatische controles toe voor urenberekening, toegangsrechten en uitvalscenario’s, samen met een geteste back-up en herstelprocedure.

**Resultaat:** een registratie is aantoonbaar opgeslagen, alleen bevoegde personen kunnen ze wijzigen en de bestaande schermen leveren consistente gegevens.

### Stap 2 — Uren administratief bruikbaar maken

Werkroosters, nachtdiensten, afwijkingen en correcties toevoegen. Vervolgens goedkeuring en periodeafsluiting uitwerken. Overuren en tekorten baseren op de ingestelde afspraken.

**Resultaat:** beheerders kunnen afwijkende registraties herstellen en een gecontroleerd urenoverzicht afsluiten.

### Stap 3 — Rapportering en koppelingen uitbreiden

Rapporten voor meerdere medewerkers, herinneringen, teamrechten en externe koppelingen toevoegen op basis van de dagelijkse behoefte.

**Resultaat:** minder handmatig opvolgwerk en makkelijker gebruik van de uren buiten de plugin.

## 7. Voorstel voor de eerstvolgende versie

Een afgebakende volgende versie kan zich richten op:

1. Correcte API-rechten voor badgegegevens en een duidelijk beleid voor geblokkeerde accounts.
2. Herstel van de MQTT-statistiekfunctie, tijdstempelverwerking en LoxBerry-statusknop.
3. Volledige badge-export en filters met jaar én maand.
4. Een overzicht van foutieve/open registraties, met correctie door een beheerder en wijzigingshistoriek.
5. Eenduidige daggrenzen en gerichte controles op de urenberekening.

Een bruikbare oplevercontrole omvat minimaal: een normale werkdag, meerdere pauzes, een vergeten stop, dubbele MQTT-aanlevering, tijdelijke backenduitval, een nachtdienst, zomer-/wintertijd en toegang met een medewerkeraccount. Nachtdiensten en zomer-/wintertijd kunnen eerst expliciet als bekende beperking worden vastgelegd totdat de berekening daarvoor is uitgebreid.

## 8. Waar is dit op gebaseerd?

| Onderwerp | Belangrijkste bronbestanden in de repository |
| --- | --- |
| Actieve backend | `bin/backend/dockerfile`, `bin/backend/run.py`, `bin/backend/app/__init__.py` |
| Login en rechten | `bin/backend/app/routes/`, `bin/backend/app/decorators/`, `bin/backend/app/services/auth_service.py` |
| Gebruikersbeheer | `bin/backend/app/services/user_service.py`, `bin/Webapp/js/get-users.js`, `bin/Webapp/js/adduser.js`, `bin/Webapp/js/edit_user.js` |
| Badge-events en filters | `bin/backend/app/services/badge_service.py`, `bin/backend/app/validators/badge_validator.py`, `bin/Webapp/js/get-badges.js` |
| Urenberekening en export | `bin/backend/app/services/timesheet_service.py`, `bin/backend/app/utils/date_helper.py`, `bin/Webapp/js/get-timesheetdata.js` |
| Dashboard | `bin/backend/app/services/dashboard_service.py`, `bin/Webapp/js/dashboard.js` |
| MQTT | `bin/MQTTService/mqtt_listener.py` |
| Logs en LoxBerry-beheer | `bin/Webapp/js/logs.js`, `webfrontend/htmlauth/index.php`, `webfrontend/htmlauth/settings.php`, `webfrontend/htmlauth/logs.php` |
| Configuratie en API-documentatie | `bin/docker-compose.yml`, `bin/backend/app/config.py`, `bin/backend/app/swagger.py` |

De uitbreidingen en prioriteiten in §5–7 zijn voorstellen, geen reeds gebouwde of toegezegde functionaliteit.
