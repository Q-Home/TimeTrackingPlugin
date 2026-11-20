# Versie 1.3.6: vergeten sessies automatisch afsluiten

## Waarom de oude taak onvoldoende betrouwbaar was

De dagelijkse opdracht stond in de meegeleverde plugin-crontab. De LoxBerry-installer kopieert die alleen wanneer er nog geen plugin-crontab bestaat; een update vervangt een oudere taak dus niet vanzelf. De root-installatie controleerde tot nu toe wel de Loxone-synchronisatietaak, maar niet de automatische STOP. Daarnaast werkte de afsluiter standaard slechts twee dagen terug. Zonder inspectie van het installatielog en de actieve hosttaak is niet vast te stellen welke van die omstandigheden op een specifieke Qbox speelde.

## Nieuwe uitvoering

De root-installatie plaatst en activeert nu apart `timetracking-auto-close.service` en `timetracking-auto-close.timer`. De taak draait om 00:05 in de hosttijdzone, na opstarten en iedere tien minuten als vangnet. De uitvoerder bepaalt zelf welke dagen afgesloten kalenderdagen zijn in de bedrijfstijdzone. Dezelfde service kan niet tegelijkertijd door de timer worden gestart; na een fout kan de volgende ronde opnieuw proberen. Na toepassing van de nieuwe containers vraagt de installatie direct een inhaalronde aan.

Een bestaande, herkenbare oude afsluitopdracht wordt alleen in de eigen plugin-crontab uitgeschakeld nadat de nieuwe timer geactiveerd is. Overige cronregels blijven staan en de oorspronkelijke crontab wordt bewaard met een niet-actieve back-upextensie. Eigen aangepaste bestanden op de gereserveerde systemd-namen worden niet overschreven. De taak gebruikt niet langer een lockbestand dat de gebruiker mogelijk niet in `/run/lock` kan aanmaken.

## Welke STOP wordt toegevoegd

De inhaalronde zoekt alle nog onafgesloten startdagen, ook ouder dan twee dagen, en verwerkt die op datumvolgorde. Zij houdt rekening met bestaande echte STOP-records, correcties en vervallen starts. Een latere nieuwe dagstart of de STOP van die nieuwe sessie kan een oudere vergeten sessie niet meer verbergen.

De ingestelde afsluitregel blijft leidend: standaard acht verstreken uren na START; waar ingesteld worden de aangepaste uren of de geplande eindtijd gebruikt. In eenvoudige modus wordt de STOP direct toegepast, ook wanneer een oude policy nog alleen signalering of een voorstel bevat. Geavanceerde modus blijft de expliciete signalerings- en voorstelkeuze respecteren. Een berekende STOP wordt nooit voorbij de volgende echte start geplaatst en nooit in de toekomst gezet.

Vandaag wordt niet automatisch afgesloten alleen doordat de vangnettaak draait. De originele START blijft bewaard en er worden uitsluitend herkenbare automatische STOP-records toegevoegd. Opnieuw draaien maakt geen tweede STOP voor dezelfde verwerkte sessie. Echte nachtdiensten met een geregistreerde STOP blijven behouden. De begrenzing van voorlopige middernachturen uit versie 1.3.5 is eveneens inbegrepen.

Bestaande afgesloten of handmatig goedgekeurde perioden blijven beschermd. Een databasefout of periodeblokkering wordt zichtbaar gelogd; zo'n uitzonderingssituatie wordt niet stilzwijgend als geslaagde afsluiting gemeld.

## Installeren en controleren

Installeer versie 1.3.6 via de pluginbeheerder. Wacht op **Automatic STOP timer enabled** en **Automatic STOP catch-up requested** in het installatielog. De vergeten sessie wordt dan bij die inhaalronde afgesloten zodra de backend en database beschikbaar zijn; anders probeert de timer opnieuw. Vernieuw het urenoverzicht na enkele minuten. De automatische STOP is zichtbaar bij de oorspronkelijke dag en de totalen gaan bij de volgende Loxone-synchronisatie mee.

Leescontroles op de Qbox:

```sh
systemctl list-timers timetracking-auto-close.timer --no-pager
systemctl status timetracking-auto-close.service --no-pager
tail -n 20 /opt/loxberry/log/plugins/timetrackingplugin/auto_stop_missing_badges.log
```

De taak meldt starttijd, bedrijfstijdzone, invoegingen en reden-tellers. Een geslaagde uitvoering zonder vergeten sessies mag nul invoegingen melden. Deze wijzigingen zijn getest met tijdelijke hostbestanden en synthetische registraties; niet rechtstreeks op de productie-Qbox uitgevoerd.

Technische bronnen: [LoxBerry-installer](https://github.com/mschlenstedt/Loxberry/blob/master/sbin/plugininstall.pl) en [systemd timerdocumentatie](https://www.freedesktop.org/software/systemd/man/247/systemd.timer.html).
