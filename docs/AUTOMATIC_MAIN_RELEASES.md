# Versie 1.3.8: automatisch van merge naar Qbox-update

## Dagelijks gebruik

Na het samenvoegen naar main volgt automatisch deze keten:

1. De regressiecontroles draaien op Python 3.11 en 3.12, inclusief PHP en JavaScript.
2. Alleen na succes wordt de geteste main-versie gepubliceerd als stabiele GitHub-release.
3. Dezelfde taak schrijft de LoxBerry-updateverwijzing op de branch updates.
4. Qboxen met Automatic Updates → Releases halen de nieuwe versie op tijdens hun native updatecontrole. Re-Check for Updates kan de controle eerder aanvragen; dit is geen garantie dat installatie onmiddellijk klaar is.

Een nieuw nummer in plugin.cfg wordt gebruikt wanneer het beschikbaar en nieuwer is. Is dat nummer al voor andere broncode gebruikt, dan verhoogt de taak automatisch het patchnummer en schrijft uitsluitend de versieaanpassing terug naar main. Bijvoorbeeld 1.3.8 → 1.3.9. Die versiecommit bevat geen applicatiewijzigingen en verwijst naar de oorspronkelijk geteste commit. Een nieuwere handmatig gekozen versie, bijvoorbeeld 1.4.0, blijft behouden.

De eerste merge van deze wijziging kan versie 1.3.8 publiceren en maakt de nog ontbrekende updates-branch aan. De Q-Home-installatie op 1.3.4 kan die feed vervolgens uitlezen; de eerdere identiteitsomzetting hoeft daarvoor niet opnieuw. Handmatig een release aanmaken is na deze overstap niet meer nodig.

## Herhalen en gelijktijdige merges

Een herstart van dezelfde taak bevestigt de bestaande release en herstelt zo nodig alleen de feed; hij maakt geen extra versie. Na een gedeeltelijke fout kan de taak zijn eigen versiecommit herkennen en de onderbroken publicatie voortzetten. Bestaande tags worden nooit verplaatst. Een conceptrelease wordt niet ongemerkt gepubliceerd.

Wanneer een nieuwere merge een testuitvoering inmiddels heeft ingehaald, publiceert de oude taak niet. De eigen geslaagde controle van de nieuwste merge zorgt voor de release. Een versiecommit kan main uitsluitend met een niet-geforceerde fast-forward bijwerken; een gelijktijdige wijziging wordt niet overschreven. De feed heeft daarnaast bescherming tegen terugzetten naar een oudere versie.

## Beheer en vereiste rechten

De bestaande GitHub Actions-token volstaat: de vrijgavejob krijgt contents: write. Er is geen extra persoonlijke token nodig. De regressiejob en pull-requestuitvoeringen houden alleen leesrechten. Forks en PR's publiceren geen releases. Main en updates moeten de bedoelde versie- en feedcommits van de workflow toestaan; als branchbescherming die schrijftoegang blokkeert, stopt de taak met een zichtbare fout en wordt de bescherming niet omzeild.

Release en feed worden expliciet in dezelfde herbruikbare workflow uitgevoerd. Een door GITHUB_TOKEN aangemaakte release start normaal geen nieuwe release-eventworkflow. Daarom vertrouwt de keten niet op een tweede gebeurtenis. Zie de [officiële GitHub-documentatie](https://docs.github.com/en/actions/concepts/security/github_token). De bestaande ingang voor bewust handmatig gepubliceerde stabiele releases blijft bruikbaar.

De publicatie gebruikt exact de geteste commit, of zijn gecontroleerde versie-only child. Het update-archief verwijst naar de onveranderde releasetag, nooit naar de bewegende main-branch. De release bevat de normale plugin-ZIP uit die tag. Er worden geen productiegegevens, credentials of logbestanden aan de release toegevoegd.

## Controle na de eerste merge

Controleer in Actions dat Regression tests én de release/feed-job groen zijn. Bij Releases hoort de nieuwe stabiele versie te staan en op updates hoort release.cfg hetzelfde nummer met de juiste tag-URL te bevatten. Klik daarna op de Qbox op Re-Check for Updates of wacht de normale updateronde af.

De lokale regressies gebruiken een nagebootste GitHub-API. Ze publiceren niets en testen de eerste release, automatische nummering, herhaalbaarheid, hervatten na fout, tagconflicten, gelijktijdige wijzigingen en de weigering van onveilige hervatting. De echte publicatie wordt pas door de merge naar main gestart; er is tijdens ontwikkeling niets op de Qbox geïnstalleerd.
