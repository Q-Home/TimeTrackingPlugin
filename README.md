# LoxBerry TimeTrackingPlugin

`main` in this repository is the source of truth for changes to TimeTrackingPlugin.
The Qbox application additions captured on 9 November 2026 are integrated here:
branding settings, optional badge codes, richer timesheet events and the existing
daily automatic STOP task. This is a source baseline, not a claim that all known
security or time-calculation issues are resolved.

## Documentation

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
