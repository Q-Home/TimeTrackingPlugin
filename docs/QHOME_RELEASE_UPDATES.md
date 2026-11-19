# Q-Home en automatische release-updates — versie 1.3.4

De plugin-uitgever is Q-Home, met info@q-home.be als algemeen contactadres. De API-voorbeelden gebruiken neutrale veldnamen. De uitgeversnaam telt bij LoxBerry mee in de technische plugin-identiteit. Daarom moet een bestaande installatie eerst eenmalig worden omgezet; anders ziet LoxBerry de nieuwe ZIP als een tweede plugin.

## Eenmalige overstap op een bestaande Qbox

1. Laat alle andere plugin- of systeeminstallaties afronden.
2. Kopieer `tools/migrate_qhome.py` naar de Qbox, bijvoorbeeld als `/tmp/qtime-qhome.py`.
3. Voer uit: `sudo python3 /tmp/qtime-qhome.py`.
4. Wacht op de bevestiging **Q-Home identity and Releases updates enabled**. Stop bij een foutmelding; installeer dan nog geen ZIP.
5. Installeer de nieuwe TimeTrackingPlugin-ZIP via de pluginbeheerder. Controleer dat dezelfde pluginmap behouden blijft en dat er **by Q-Home** staat.
6. Laat **Automatic Updates → Releases** geselecteerd.

Het omzettingsscript gebruikt de LoxBerry-installatievergrendeling. Het wijzigt alleen de identiteit en update-instellingen van exact de bestaande `timetrackingplugin`, inclusief de schaduwdatabase die de updater leest. Het bewaart de versie, mapnamen, overige plugins en installatiegegevens. Het raakt MongoDB, badgegegevens, wachtwoorden, Loxone-koppelingen en Docker niet aan. Vooraf komt een private databaseback-up in `data/plugins/timetrackingplugin/identity-backups`. Bij een schrijffout worden de oorspronkelijke databases teruggezet. Dubbele of inconsistente installaties worden geweigerd.

Deze omzetting hoeft maar één keer. Een nieuwe Qbox kan de Q-Home-ZIP direct installeren.

## Volgende releases automatisch installeren

De oude configuratie bevatte lege GitHub-voorbeeldadressen. De nieuwe configuratie gebruikt de native LoxBerry-updater met een stabiele feed op de branch `updates`.

Na het samenvoegen van deze wijziging publiceert de beheerder een normale GitHub-release met een tag die overeenkomt met `PLUGIN.VERSION`, bijvoorbeeld `v1.3.4`. GitHub Actions controleert de tag, pluginversie en Q-Home-identiteit. Daarna schrijft de workflow `release.cfg` op `updates`, met het ZIP-archief van precies die tag. Op de eerste release wordt deze branch automatisch aangemaakt. Een oudere release mag de feed niet terugzetten.

LoxBerry haalt de feed op tijdens zijn eigen periodieke updatecontrole en installeert nieuwere releases wanneer **Releases** geselecteerd is. Dat gebeurt niet onmiddellijk op het publicatiemoment. Een commit op main, een losse ZIP, een conceptrelease of prerelease wordt niet automatisch verspreid. Beide updatekanalen verwijzen bewust naar dezelfde stabiele feed.

De feed bestaat pas nadat de eerste stabiele Q-Home-release met deze workflow is gepubliceerd. Deze codewijziging publiceert zelf geen release en installeert niets op een Qbox. Als de workflow geen schrijfrechten heeft op `updates`, moet de repositorybeheerder die branch beschikbaar maken voor de workflow; het taaklog meldt dit. Bestaande lokale configuratie blijft via de bestaande ZIP-installatieprocedure bewaard.

## Validatie

Automatische controles gebruiken uitsluitend tijdelijke bestanden en verzonnen pluginrecords. Ze controleren identiteitsomzetting, behoud van andere gegevens, herhaalbaarheid, conflictbeveiliging, private back-up, herstel bij een fout en het weigeren van ongeldige of oudere releases. De daadwerkelijke automatische installatie op een Qbox moet na de eerste gepubliceerde Q-Home-release worden gecontroleerd.
