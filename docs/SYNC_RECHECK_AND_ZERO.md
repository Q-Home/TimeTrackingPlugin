# Versie 1.3.9: numerieke kaarten en gecontroleerd hervatten

## Nul op het scherm en in Loxone

De grote waarde op iedere kaart in Loxone-synchronisatie toont nu rechtstreeks de numerieke uitvoer: decimale uren met een punt, of 0 bij een onbekende waarde. Waar beschikbaar staat de leesbare urenweergave eronder. Een ontbrekend saldo toont dus 0 en niet de oude tekst. Bronproblemen blijven als toelichting zichtbaar en worden niet naar de numerieke custom fields geschreven.

Sinds 1.3.7 gebruikt de schrijver deze numerieke uitvoer al. Een nog opgeslagen tekstwaarde in Loxone kan echter blijven staan wanneer de betreffende koppeling door een fout gepauzeerd is. Alleen de weergave wijzigen hervat zo'n koppeling niet.

## Verschillende foutoorzaken

Een historische verificatiefout bleef opgeslagen en blokkeerde volgende updates. Het oude scherm toonde daar toch een datum voor een volgende poging bij. De nieuwe weergave zegt expliciet dat de koppeling gepauzeerd is. Historische generieke fouten worden niet voorgesteld als een nieuwe, actuele mislukte teruglezing.

Nieuwe adapterfouten onderscheiden een afwijking in de beheerde custom fields van een wijziging in andere gebruikerskenmerken. Beide blijven de schrijver pauzeren. De bestaande uitzondering voor alleen lastEdit/lastedit blijft behouden; de overige controles blijven actief.

Een identiteitsconflict kan ontstaan bij dubbele lokale medewerkers, een bron-ID die naar een andere UUID wijst, of meerdere historische bron-ID’s. De meldingen onderscheiden deze gevallen. Verschillende bron-ID’s, bijvoorbeeld een numerieke userid en de UUID, worden alleen als aliassen geaccepteerd wanneer de Miniserver ze afzonderlijk bevestigt als precies dezelfde UUID. De geverifieerde set wordt vastgelegd en opnieuw gecontroleerd; een gewijzigde bron tijdens het lezen blokkeert het schrijven nog steeds. Verschillende lokale medewerkers worden niet automatisch samengevoegd en een bestaande andere UUID wordt niet automatisch vervangen.

## Koppeling controleren en hervatten

Beheerders en technische beheerders krijgen bij een opgeslagen fout de knop Koppeling controleren en hervatten. Die controleert de bestaande Miniserver, dezelfde UUID, bron-ID’s en dubbele verwijzingen. Pas na een geslaagde controle wordt de pauze opgeheven, met auditregistratie en een nieuwe synchronisatieronde. Er worden tijdens de controle geen custom fields geschreven. De daaropvolgende schrijver berekent de huidige waarden opnieuw en behoudt zijn volledige nacontrole.

Als de controle mislukt, blijft de blokkering bestaan en verschijnt de concrete reden. Een echt identiteitsconflict wordt dus niet weggewerkt door foutmeldingen te wissen. Alleen bevoegde rollen kunnen deze actie uitvoeren.

Na het mergen wordt deze versie via de automatische releaseketen gepubliceerd. Werk de plugin bij en vernieuw de synchronisatiepagina. Gebruik bij een gepauzeerde koppeling de nieuwe knop. Controleer daarna via Controleren / dry-run de bestaande waarden in Loxone. De productie-Qbox en de eigenlijke medewerkerkoppelingen zijn tijdens ontwikkeling niet gewijzigd.
