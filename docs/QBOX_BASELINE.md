# Qbox baseline and update procedure

## Source of truth

Use this repository's `main` branch for reviewed changes. Do not treat files edited
only on a Qbox as a release. Record the deployed commit and Docker image IDs for
each deployment; application source equality alone does not identify an image.

This integration reconciles the application archive supplied on 9 November 2026
with GitHub base `ac4daa52f34bde856be72da9fb710bda86d2ca4e`.
The comparison covered 321 archive files: 276 exact matches, 18 line-ending-only
differences, 19 content differences and 8 Qbox-only files. The 19 changed files and
8 additional files are integrated; line-ending-only differences are not imported.
Ten key archive files had also been matched to running containers using SHA-256.
This does not claim that every container file or host plugin file was inspected.

## Integrated behavior

- Branding name, logo and accent color, including API, storage and web UI.
- Optional badge codes and the existing username/external-user-ID fallback.
- Device, location and raw-data fields in timesheet events.
- Frontend branding integration and guards for optional UI libraries.
- `bin/backend/scripts/auto_stop_missing_badges.py` and the observed daily cron.
- MQTT test helper, with its real password and personal defaults removed.

The backend, frontend and service changes form one set. Do not copy individual
files onto an older backend: constructor signatures and route registration differ.

## Automatic STOP: existing policy, not a new approval

`cron/crontab` preserves the Qbox schedule: daily at 11:59 in the host timezone,
running as `loxberry`. It executes the backend container's automatic STOP script.
The user needs working Docker access; the destination log directory must exist.
The policy remains 8 elapsed hours after a detected START, looking back 2 days.
It does not guarantee 8 net working hours after breaks. At 11:59 a START at 08:00
has a future STOP at 16:00 and is skipped until a later eligible run.

Before changing this policy, obtain agreement from the business owner and review
historical effects. Use `--dry-run` first in an isolated test environment.
The supplied production snapshot contained 1,277 auto-generated STOP events;
those are calculated corrections, not proof of physical clock-out observations.

## Local configuration

Keep GitHub's parameterized `bin/docker-compose.yml`. The server's literal-valued
Compose file and private environment files were not included in the source archive
and must not be replaced blindly. Start new local configuration from
`bin/.env.example`, set values privately and preserve existing port mappings,
broker credentials, database volume and plugin settings during an upgrade.

An old tracked `bin/backend/.env` is removed from the repository. Do not copy local
credentials into source control. The root Compose environment in `bin/.env` is the
configuration used for container creation. Removing a tracked file does not erase
old Git history or replace the need to rotate any previously exposed secrets.

The frontend reads and saves branding via the webapp's `/api/v1/settings/branding`
path. Nginx forwards those requests to the backend, so branding also works when
the Qbox serves the webapp over HTTPS or the direct API uses another host port.

## Deployment procedure

1. Back up the database, current source, real configuration and running Docker
   images. Test restore separately; a running standalone database dump is not
   automatically a consistent snapshot across concurrent writes.
2. Choose a reviewed commit, prepare an isolated test installation and configure
   it with separate credentials, database volume and MQTT topics. Do not use the
   production broker for a functional test.
3. Run the regression suite and exercise login/roles, badge input with and without
   a code, branding, timesheet event details and automatic STOP dry-run on copied
   or synthetic data. Also test upgrade using representative existing data.
4. Preserve local configuration and data. Build all affected application services
   from the same chosen commit. Install the plugin's cron file through the normal
   LoxBerry packaging/install path; copying only `bin/` does not install cron or
   the PHP/plugin wrapper.
5. In the agreed maintenance window, deploy, record the commit/image IDs, check
   health through backend and Nginx, verify a controlled real scan, and inspect
   MQTT diagnostics. Confirm cron installation without running corrective writes
   against historical production data merely as a test.
6. Keep the previous images/configuration available for rollback. Do not use
   `docker compose down -v`, demo seeding or a blind database restore.

The PHP Start/Restart action calls a script that can rebuild services; it is not a
read-only status action. Current `plugin.cfg` and release configuration still have
legacy version/placeholder update URLs. Their installed copies have not been
reconciled, so automatic plugin updates are not yet a verified deployment route.
Do not publish a new version until packaging and upgrade behavior have been tested.

## Known issues intentionally left for separate fixes

This baseline preserves observed behavior, including known issues: broad badge
JWT permissions, trusted-subnet authentication, no JWT revocation on account block,
day-split calculations for overnight work, inconsistent time presentation,
positive MQTT feedback after a failed API write, timestamp-only MQTT input handling,
missing durable retry/deduplication, the legacy stats API mismatch, unredacted
payload prints, and the `badge_codes` versus `badge_code` stored-data mismatch.
Treat these as a follow-up backlog; this integration is not a production safety
certification and does not change existing registrations.

The automatic STOP tests use synthetic records in memory. They neither validate
the correctness of historical corrections nor decide company timekeeping policy.


## ZIP updates: preserve settings and activate images (plugin 1.0.1)

LoxBerry replaces plugin files during a ZIP upgrade. Replacing source files alone
does not change the files copied into an already-running Docker image. Earlier
versions left the activation call commented out, so a GUI update could install
successfully while the old webapp was still served.

`preroot.sh` now saves the local Compose file, overrides, environment files, plugin
config/data and the bind-mounted application logs into a private directory inside
the temporary installation archive before replacement. `postroot.sh` restores that
state and builds/recreates backend, MQTT listener and webapp. MongoDB is never
included in the recreate command and no volumes are removed. This is configuration
preservation, not a database backup or transactional rollback.

When the old `.env` is missing but the installed Compose needs variables, the
helper can reconstruct the required settings from the existing Docker containers.
It writes a private `.env`, quotes password dollar signs literally, and does not
display credentials. An incomplete recovery stops activation with a visible
installer warning; it does not silently substitute example settings.

Builds happen before running application containers are replaced. A failed build
leaves those containers running. A later start failure is reported and may require
manual recovery; the helper does not claim atomic rollback of three services.
The database must already be running for automatic activation. On a fresh install,
configure the database and local settings before starting the application.

After activation the helper verifies `/usr/share/nginx/html/version.json` inside
the running webapp. The webapp serves this as `/version.json`, with the plugin
version, a frontend source fingerprint and a build time. Static responses require
browser revalidation; use Ctrl+F5 once when coming from an old cached version.
The plugin installer log contains a success marker only after version verification.

Download a new ZIP of `main` after this fix; reinstalling an older downloaded ZIP
cannot include it. Each subsequent packaged release should bump plugin.cfg's
version and be tested through the same ZIP upgrade path with representative local
settings. The legacy release.cfg URLs remain a separate automatic-update task.
