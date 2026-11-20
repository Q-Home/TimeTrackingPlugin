# Versie 1.3.5: starts van de MQTT-bus en geen fictieve middernachturen

De getoonde situatie bevatte geen bronregistratie op de nieuwe dag. De urenberekening verdeelde een nog open sessie van de vorige dag over beide kalenderdagen. Daardoor leek 00:00 een nieuwe start, terwijl er geen START-record was. De nachtelijke opruimtaak maakt uitsluitend STOP-records; deze wijziging maakt of verwijdert geen productie-registraties.

Een onafgesloten sessie telt voortaan maximaal tot de eerstvolgende lokale middernacht. De vorige dag blijft voorlopig met de melding dat een STOP ontbreekt. De volgende dag heeft nul gewerkte uren zolang geen eigen MQTT-start of bevestigde nachtdienst aanwezig is. De tijdzone van de ingestelde periode wordt gebruikt, inclusief zomer- en wintertijd. Dit is een begrenzing van de berekening, geen opgeslagen automatische STOP.

Een nieuwe badge-start op een volgende dag begint een eigen sessie; de vergeten STOP van gisteren trekt die niet meer mee. Een echte nachtdienst met een bron-START en bron-STOP aan weerszijden van middernacht blijft over beide dagen berekend. Zolang die nachtelijke STOP ontbreekt, worden op de volgende dag geen voorlopige uren toegevoegd; na ontvangst wordt de bevestigde nachtdienst herberekend.

Nieuwe START/SCAN_IN-registraties kunnen niet meer met een HR-correctie worden toegevoegd en een STOP kan niet in START worden veranderd. Een bestaande badge-start kan met reden worden gecorrigeerd; het originele bericht blijft onveranderd. De nieuwe-registratiedialoog biedt alleen STOP en pauzeacties aan. Historisch opgeslagen handmatige correcties worden niet verwijderd. Als een automatisch gemarkeerde START in de brondata wordt aangetroffen, wordt die zichtbaar als fout gemeld en levert hij geen gewerkte uren op.

De bestaande, beveiligde MQTT-ingang blijft de route voor nieuwe badge-starts. De nachtelijke afsluitregels blijven STOP-only. Deze release corrigeert geen bestaande brongegevens en wijzigt geen afsluitbeleid. Controleer na installatie de getroffen dag opnieuw; een ontbrekende echte STOP kan met de werkelijke tijd worden aangevuld. De Loxone-totalen worden bij de volgende synchronisatieronde opnieuw berekend.
