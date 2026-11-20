# LoxBerry TimeTrackingPlugin

`main` in this repository is the source of truth for changes to TimeTrackingPlugin.
The Qbox application additions captured on 9 November 2026 are integrated here:
branding settings, optional badge codes, richer timesheet events and the existing
daily automatic STOP task. This is a source baseline, not a claim that all known
security or time-calculation issues are resolved.

## Documentation

- [Automatic employees and Qtime access policy (1.2.2)](docs/AUTOMATIC_EMPLOYEES.md)
- [Own password and nightly automatic closing (1.2.1)](docs/ACCOUNT_AND_NIGHT_CLOSE.md)
- [Loxone user totals: setup, versions, diagnosis and limitations (1.2.0)](docs/LOXONE_USER_HOURS_SYNC.md)
- [HR timekeeping, screenshots, migration and limitations (1.1.0)](docs/HR_GUIDE.md)
- [Qbox baseline, configuration and update procedure](docs/QBOX_BASELINE.md)
- [Functional overview and limitations](docs/FUNCTIONEEL_OVERZICHT.md)

## Run the regression checks

Use Python 3.11 or 3.12 in a virtual environment:

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

Tests use an in-memory MongoDB substitute, never a running Qbox database or broker.
Local installation secrets belong in `bin/.env`; start with `bin/.env.example` and
set real values privately. Do not commit `.env`, local settings or production logs.

Zie [versie 1.2.3: afronding en standaard werkregime](docs/ROUNDING_AND_DEFAULT_REGIME.md) voor de nieuwe HR-instellingen.

Zie [versie 1.2.4: lokaal IP-adres en certificaatwaarschuwingen](docs/LOCAL_IP_CERTIFICATE_COMPATIBILITY.md) voor de LoxBerry-compatibiliteit.

Zie [versie 1.2.5: Miniserver-antwoorden verwerken](docs/MINISERVER_RESPONSE_COMPATIBILITY.md) voor de verwerking van apiKey en lege veldlabels.

Zie [versie 1.2.6: lege dagen aanvullen](docs/CORRECT_EMPTY_DAYS.md) voor het toevoegen van START/STOP per dag.

Zie [versie 1.3.0: eenvoudige tijdregistratie en automatische Loxone-koppeling](docs/SIMPLE_TIME_AND_AUTOMATIC_SYNC.md) voor de nieuwe standaardwerking.

Zie [versie 1.3.1: synchronisatietaak herstellen](docs/SYNC_SCHEDULER_REPAIR.md) voor installatie van de achtergrondtaak en de nieuwe uitvoeringsdiagnose.

## Q-Home en automatische releases

Vanaf versie 1.3.4 is de uitgever Q-Home. Bestaande installaties hebben een eenmalige identiteitsomzetting nodig **vóór** installatie van de nieuwe ZIP. Zie [omzetting en automatische updates](docs/QHOME_RELEASE_UPDATES.md).

Vanaf 1.3.8 maakt een geslaagde merge naar main automatisch een stabiele release en werkt de Qbox-updatefeed bij, met automatische patchnummering waar nodig. Zie [automatische releases](docs/AUTOMATIC_MAIN_RELEASES.md).
