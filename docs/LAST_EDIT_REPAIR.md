# Versie 1.3.2: correcte nacontrole bij lastEdit

De Qbox bevestigde dat alle vijf custom fields correct geschreven waren. Bij opnieuw opslaan met dezelfde waarden veranderde alleen `lastEdit`. De adapter sloeg uitsluitend de oudere spelling `lastedit` over, waardoor een geslaagde update als verificatiefout werd opgeslagen.

De nacontrole negeert vanaf deze versie beide exacte schrijfwijzen van het wijzigingstijdstip. UUID, beheerde urenvelden, overige gebruikersvelden en toegangskenmerken blijven gecontroleerd. De update wijzigt geen rechten en verstuurt geen volledig gebruikersobject.

## Herstel na de bestaande fout

Installeer versie 1.3.2 via de pluginbeheerder. Een eerder opgeslagen verificatiefout heeft de betreffende koppeling gepauzeerd. Die blokkering wordt bewust niet voor alle gebruikers gewist: een eerdere verificatiefout kan ook een echte afwijking zijn geweest.

Open bij de gecontroleerde medewerker **Koppeling bekijken → Handmatige uitzondering**. Selecteer opnieuw dezelfde bestaande Loxone-gebruiker, bevestig het vervangen van de koppeling en geef als reden bijvoorbeeld "Herstel foutieve lastEdit-controle". Daardoor wordt de oude foutstatus voor uitsluitend deze koppeling gewist. Klik vervolgens op **Nu synchroniseren**, wacht ongeveer een minuut en vernieuw de diagnose. Controleer de laatste geslaagde controle en lees de bestaande Loxone-waarden terug.

De automatische ID-koppeling blijft actief. Opnieuw koppelen maakt geen nieuwe Loxone-gebruiker aan. De regressiecontrole bootst beide tijdstempelvarianten na en controleert dat afwijkende uren, andere custom fields en gewijzigde rechten nog steeds een fout opleveren.
