# Versie 1.3.3: Loxone-velden iedere tien minuten

De automatische synchronisatie naar de custom fields gebruikt standaard 600 seconden. Ook bestaande instellingen met een korter interval worden effectief op tien minuten gebracht. Een langer ingesteld interval blijft behouden. De instelling accepteert 600 tot 3600 seconden.

Nieuwe badgegegevens en automatische gebruikerskoppelingen omzeilen dit interval niet meer. Bij de volgende ronde worden de actuele totalen berekend; er wordt geen oude wachtrijwaarde geschreven. Alleen de bewuste actie **Nu synchroniseren** kan eerder een ronde starten. Ook opslaan van instellingen of een handmatige herkoppeling plant expliciet een ronde in.

De croncontrole blijft iedere minuut lopen en wacht tussendoor. Zo blijft de handmatige actie snel beschikbaar. De registratie op Qbox zelf blijft direct werken. Installeer versie 1.3.3 via de pluginbeheerder en controleer bij Loxone-synchronisatie dat het interval 600 seconden is. Er worden geen koppelingen of veldtoewijzingen gewist.
