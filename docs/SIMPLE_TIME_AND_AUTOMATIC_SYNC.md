# Versie 1.3.0 — eenvoudige tijdregistratie en automatische Loxone-koppeling

## Standaardwerking

Registraties worden voortaan standaard **automatisch goedgekeurd** voor dagelijks gebruik. Er is geen verplichte goedkeuringsronde. Dit is een verwerkingsstatus, geen vergrendelde goedkeuringsperiode: nieuwe registraties en handmatige correcties blijven mogelijk.

Een automatische STOP of een dag zonder registratie blokkeert de beschikbare uren niet meer. Een dag zonder registratie telt als nul gewerkte uren; het systeem verzint geen werkuren om de achturennorm te vullen. Lopende sessies blijven herkenbaar als voorlopig. Automatische afsluitingen blijven zichtbaar als informatie. Ernstige onleesbare brongegevens blijven een fout; een niet te berekenen saldo blijft herkenbaar wanneer voor een deel van de maand geen norm bestaat.

De bestaande afronding, pauzeaftrek en persoonlijke roosters blijven gelden. Kalender en vakantie zijn optionele hulpmiddelen om de verwachte uren en het saldo te verfijnen; je hoeft ze niet in te richten om de gewerkte uren te zien of te synchroniseren.

Handmatige goedkeuring is optioneel beschikbaar via **HR-instellingen → Eenvoudige tijdregistratie**. Zet daar de eenvoudige werking uit als een handmatige workflow gewenst is. Oude expliciet goedgekeurde en afgesloten perioden blijven bewaard en beschermd; de update wist of heropent die niet. De keuze wordt één keer bij de upgrade geactiveerd en niet bij iedere herstart opnieuw overschreven.

## Automatische gebruikerskoppeling

De gebruikers-ID uit de vertrouwde Loxone-registratie wordt gebruikt voor de koppeling met de bestaande Miniservergebruiker:

- Een Loxone-UUID wordt rechtstreeks gecontroleerd tegen diezelfde gebruiker.
- Een andere Loxone-userid wordt door de Miniserver opgezocht met `checkuserid`; daarna wordt de gevonden UUID gecontroleerd.
- Historische registraties kunnen de ID leveren wanneer een oud handmatig aangemaakt medewerkersprofiel die nog niet bevat.
- De koppeling blijft werken na een naamswijziging. Er wordt niet op naam gegokt.

Een medewerker hoeft niet meer afzonderlijk via **Gebruiker koppelen** geselecteerd te worden. De achtergrondtaak legt de gecontroleerde koppeling vast en schrijft de gekozen urenvelden bij ingeschakelde synchronisatie. Nieuwe bronregistraties plannen automatisch een volgende ronde in. Dit gebeurt normaal binnen één minuut, niet tijdens de badge-aanvraag zelf. De badge-aanvraag blijft daardoor ook bij een tijdelijk onbereikbare Miniserver werken.

Bij een ontbrekende, dubbele of tegenstrijdige ID wordt een concrete melding getoond en wordt niet naar een andere persoon geschreven. Een bestaand handmatig gekoppelde UUID wordt nooit ongemerkt vervangen. Gearchiveerde of geblokkeerde accounts worden niet automatisch bijgewerkt. Een handmatige uitzondering blijft bereikbaar onder **Koppeling bekijken**.

## Eenmalige instellingen blijven behouden

De bestaande Miniserverselectie en veldtoewijzing worden hergebruikt. De update kiest geen andere gebruikersvelden en schakelt een eerder uitgeschakelde schrijver niet stilzwijgend in. Voor schrijven moeten de gewenste velden eenmaal gekozen en de synchronisatie ingeschakeld zijn. Automatisch koppelen kan al plaatsvinden wanneer de schrijver uitgeschakeld is; er worden dan geen Miniservervelden gewijzigd.

Lokale-IP-compatibiliteit en certificaatwaarschuwingen blijven behouden. De adapter wijzigt uitsluitend geselecteerde custom fields van bestaande gebruikers. Er worden geen Loxone-gebruikers, rechten of wachtwoorden aangemaakt of gewijzigd. Medewerkers krijgen geen Qtime-webtoegang.

## Controle na installatie

1. Installeer versie 1.3.0 via de pluginbeheerder en ververs met Ctrl+F5.
2. Het urenoverzicht toont **Automatisch goedgekeurd** en vereist geen goedkeuringsknop voor nieuwe perioden.
3. Controleer dat automatische afsluitingen en beschikbare maandtotalen direct zichtbaar zijn.
4. Op **Loxone-synchronisatie** verschijnt na de achtergrondronde **Automatisch gekoppeld via Loxone-ID**.
5. Controleer het tijdstip van de laatste update en de gekozen custom fields. Bij een onbekende ID staat er een melding bij de betreffende medewerker.

Onderbouwing voor ID-resolutie: [officiële Loxone-gebruikers-API V17](https://www.loxone.com/enen/wp-content/uploads/sites/3/2026/04/1700_Usermanagement.pdf), secties `getuser`, `checkuserid` en `uuid`. Er is tijdens de ontwikkeling geen productie-Qbox of Miniserver benaderd. Tests gebruiken synthetische registraties en serverantwoorden.
