# Versie 1.3.10: oude dubbele medewerker archiveren

Ga naar Accounts & rechten en kies bij de oude gebruikersnaam het prullenbak-icoon Archiveren. Controleer de gebruikersnaam vóór bevestiging; de automatisch aangemaakte huidige medewerker moet actief blijven. De bestaande verwijderactie is een archivering: de gebruikersrecord wordt geblokkeerd en gearchiveerd, de bronregistraties worden niet verwijderd.

Een oude UUID-koppeling blijft voor de historie bestaan. Tot deze versie kon die koppeling de actieve medewerker toch blijven blokkeren. Vanaf 1.3.10 telt een expliciet gearchiveerde medewerker niet meer mee als actieve UUID-reservering. Dit geldt voor automatisch koppelen, handmatig koppelen en het gecontroleerd hervatten. De schrijver slaat gearchiveerde medewerkers al over en de synchronisatiepagina verbergt die.

Een account dat alleen geblokkeerd is, blijft zijn UUID wel reserveren. Ook een onbekende binding zonder gebruikersrecord wordt niet stilzwijgend vrijgegeven. De bescherming tegen twee actieve medewerkers met dezelfde identiteit blijft dus bestaan. Terugzetten uit het archief herstelt die conflictcontrole.

Na archiveren kan de volgende automatische ronde de huidige medewerker koppelen. Als de huidige medewerker nog een opgeslagen verificatiepauze heeft, gebruik Koppeling controleren en hervatten. Oude uren blijven bij de gearchiveerde interne medewerker-ID; deze actie voegt de twee urenhistories niet samen en kopieert geen registraties. Voor één gecombineerd historisch overzicht is een afzonderlijke, gecontroleerde samenvoeging nodig.

De productiegebruikers zijn tijdens ontwikkeling niet gearchiveerd. Tests gebruiken tijdelijke synthetische records en controleren behoud van historie, het vrijgeven van alleen gearchiveerde reserveringen en het blijven blokkeren bij actieve of alleen geblokkeerde accounts.
