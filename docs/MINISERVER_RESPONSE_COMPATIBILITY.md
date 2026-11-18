# Versie 1.2.5 — antwoorden van de Miniserver verwerken

Een verbinding kan HTTP 200 én Loxone-code 200 geven en toch in Qtime vastlopen op de verwerking van de inhoud. De diagnose op de Qbox bevestigde:

- `apiKey`: `LL.value` is tekst die na gewone JSON-decodering tekst blijft.
- `getcustomuserfields`: `LL.value` is een JSON-tekst met een lege lijst (`[]`).
- `getuserlist2`: `LL.value` is een JSON-tekst die als lijst wordt ingelezen.

De adapter ondersteunt vanaf deze versie ook de Loxone-objecttekst met enkele aanhalingstekens in `apiKey`. Aanhalingstekens en eventuele ongequote sleutels worden als tokens omgezet en vervolgens door de JSON-parser gecontroleerd. Er wordt geen JavaScript of PHP uitgevoerd. Alleen versie en serienummer worden gebruikt; het sleutelveld blijft op de host. Zowel `mac` als `snr` is toegestaan. Als beide aanwezig zijn, moeten ze naar dezelfde server verwijzen. Ongeldige of ontbrekende serveridentiteit blijft een fout.

Bij ontbrekende of lege labels toont Qtime **Custom field 1** tot en met **Custom field 5**. Er worden geen veldnamen op de Miniserver gewijzigd. Bestaande labels blijven staan; alleen expliciet geselecteerde velden mogen later door synchronisatie worden bijgewerkt.

Een lege gebruikerslijst is geldig en wordt als nul gebruikers getoond. Ongeldige gebruikersrecords, ongeldige of dubbele UUID's worden geweigerd. De firmwarecontrole blijft Miniserver 17.x vereisen; dit verruimt de firmwareondersteuning niet.

Een ongeldig antwoord krijgt voortaan een specifieke melding voor servergegevens, veldnamen of gebruikerslijst. Een eerder vastgestelde certificaatwaarschuwing wordt ook bij zo'n fout getoond. De lokale-IP-compatibiliteit van versie 1.2.4 blijft behouden.

Na installatie van **1.2.5**: ververs de pagina **Loxone-synchronisatie** en klik op **Verbinding testen**. Bij een werkende verbinding met een niet-passend certificaat kunnen de geslaagde test en de gele certificaatwaarschuwing tegelijk zichtbaar zijn.

Onderbouwing: de [officiële communicatiehandleiding](https://www.loxone.com/wp-content/uploads/datasheets/CommunicatingWithMiniserver.pdf), [gebruikersbeheer V17](https://www.loxone.com/enen/wp-content/uploads/sites/3/2026/04/1700_Usermanagement.pdf), de gebruikersdiagnose en de [apiKey-verwerking in een bestaande Loxone-client](https://github.com/XciD/loxone-ws/blob/master/loxone.go). Tests gebruiken synthetische serverantwoorden; productiegegevens worden niet opgehaald of gewijzigd tijdens de ontwikkeling.
