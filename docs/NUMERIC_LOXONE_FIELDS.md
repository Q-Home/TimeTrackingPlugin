# Versie 1.3.7: uitsluitend numerieke waarden naar Loxone

Gewerkte uren en het urensaldo worden voortaan als decimale uren naar de geselecteerde custom fields geschreven. De punt is het decimaalteken, onafhankelijk van de ingestelde taal. Er worden geen eenheden, spaties, komma’s of voorlopig-labels meegestuurd.

| Qtime-waarde | Loxone-waarde |
|---|---|
| 7 uur 30 minuten | `7.5` |
| 7 uur 25 minuten | `7.416667` |
| 8 uur | `8` |
| Min 30 minuten saldo | `-0.5` |
| Geen uren, onbekend saldo of onbetrouwbare berekening | `0` |

De uitvoer wordt afgerond op maximaal zes decimalen. Het zijn numerieke teksten omdat de Loxone-customfield-API tekstvelden gebruikt; de inhoud is direct als getal te lezen. Het bestaande Qtime-overzicht blijft uren en minuten tonen. De synchronisatie-preview toont daarnaast de numerieke waarde voor Loxone. Eventuele bronproblemen blijven in Qtime zichtbaar, ook wanneer Loxone daarvoor 0 ontvangt.

Als Registratiestatus geselecteerd is, worden vaste codes geschreven: 0 geen registratie, 1 ingeklokt, 2 pauze, 3 afgesloten, 4 automatisch afgesloten, 5 aandachtspunt. Als Laatst bijgewerkt geselecteerd is, wordt Unix-tijd in seconden geschreven. Dit tijdstip verandert alleen bij een inhoudelijke update; zonder bekende inhoudelijke update is het 0. Oude datumteksten worden bij een volgende ronde omgezet zonder een nieuw inhoudelijk wijzigingstijdstip te verzinnen.

Installeer versie 1.3.7. De veldtoewijzing en het interval van tien minuten blijven behouden. Bij de volgende ronde worden eerder geschreven teksten zoals urenlabels en Niet beschikbaar vervangen door numerieke waarden, uitsluitend in de velden die aan deze plugin zijn toegewezen. Met Nu synchroniseren kan die ronde bewust eerder worden gestart. Controleren / dry-run toont de voorgenomen numerieke waarden zonder te schrijven.

De automatische afsluiting en MQTT-startbeveiliging uit 1.3.6 zijn inbegrepen. Deze wijziging is getest met synthetische registraties en een nagebootste Miniserver; er is tijdens ontwikkeling niet op een productie-Qbox geschreven.
