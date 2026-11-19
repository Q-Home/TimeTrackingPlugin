# Versie 1.3.1 — ontbrekende synchronisatietaak herstellen

Een geslaagde verbindingstest controleert de Miniserver, maar voert geen periodieke schrijftaak uit. De diagnose op de Qbox toonde een ingeschakelde synchronisatie, opgeslagen veldmapping en gebruikerskoppelingen, maar geen taakresultaat, geen cronvermelding en geen synchronisatielog.

De root-installatie plaatst of controleert vanaf deze versie zelf de taak in `/etc/cron.d`. Daarmee is activering niet meer alleen afhankelijk van het kopiëren van de meegeleverde plugin-crontab. De nieuwe taak start iedere minuut als `loxberry`, maakt zo nodig de logmap opnieuw aan en gebruikt een proceslock in de private runtime-directory van de bestaande hostadapter. De databaselease blijft ook gelijktijdige uitvoering verhinderen.

Bestaat er al een actieve synchronisatietaak in een geldig cronbestand, dan wordt die hergebruikt en wordt geen tweede taak toegevoegd. Andere cronregels worden niet veranderd. Een zelf aangepast bestand op de gereserveerde taaknaam wordt niet overschreven. De installatie meldt expliciet of taakactivering is gelukt. De eigen taak wordt bij verwijderen van de plugin opgeruimd.

## Herstel op de Qbox

1. Installeer versie **1.3.1** via de pluginbeheerder. Bestaande database, koppelingen, inschakelstatus en veldmapping blijven behouden.
2. Controleer in het installatielog de bevestiging **Loxone synchronization task installed or verified**.
3. Open **Loxone-synchronisatie → Koppelingen & diagnose**, klik op **Nu synchroniseren**, wacht ongeveer één minuut en klik op **Vernieuwen**.
4. Controleer **Laatste start achtergrondtaak**, de aantallen **gecontroleerd / bijgewerkt / fouten**, en per medewerker **Laatste geslaagde controle** en **Inhoudelijk bijgewerkt**.
5. **Controleren / dry-run** leest de actuele waarden terug uit de Miniserver onder **Bestaande waarden in Loxone**. Dit onderscheidt opgeslagen Qtime-totalen van de bevestigde Miniserverwaarden.

Er staat een duidelijke melding wanneer nog geen achtergrondtaak is gestart of wanneer die niet kon afronden. Het logbestand bevat voortaan ook een veilig taakresultaat met aantallen of de status uitgeschakeld/wachtend. Wachtwoorden en ruwe netwerkfouten worden niet gelogd.

Handige leescontroles:

```sh
grep -R 'loxone_sync.py' /etc/cron.d
tail -n 10 /opt/loxberry/log/plugins/timetrackingplugin/loxone_sync.log
```

De cronservice, Docker en de bestaande hostadapter moeten op de host actief zijn. Deze update wijzigt geen Loxone-gebruikersrechten of veldmapping en is tijdens ontwikkeling niet op een productie-Qbox uitgevoerd.
