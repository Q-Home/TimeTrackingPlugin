<?php
require_once "loxberry_web.php";
require_once "loxberry_system.php";



// Dit zal je taalbestanden lezen naar de array $L
$L = LBSystem::readlanguage("language.ini");
$template_title = "TimeTracking Plugin";
$helplink = "http://www.loxwiki.eu:80/x/2wzL";
$helptemplate = "help.html";

// Navigatiebalk
$navbar[1]['Name'] = 'Status';
$navbar[1]['URL'] = 'index.php';
$navbar[2]['Name'] = 'MQTT Settings';
$navbar[2]['URL'] = 'mqtt.php';
$navbar[1]['active'] = True;

// Header tonen
LBWeb::lbheader($template_title, $helplink, $helptemplate);
?>

<h2>Personeel Badges & Werktijden</h2>
<table style="width: 100%; table-layout: fixed;" cellpadding="5" cellspacing="0">
    <tr>
        <th style="width: 25%;">Badge ID</th>
        <th style="width: 25%;">Naam</th>
        <th style="width: 25%;">In</th>
        <th style="width: 25%;">Uit</th>
    </tr>
    <?php foreach ($badges as $badge): ?>
    <tr>
        <td><?=htmlspecialchars($badge['badge_id'])?></td>
        <td><?=htmlspecialchars($badge['naam'])?></td>
        <td><?=htmlspecialchars($badge['in'])?></td>
        <td><?=htmlspecialchars($badge['uit'])?></td>
    </tr>
    <?php endforeach; ?>
</table>

<?php  
// Footer tonen  
LBWeb::lbfooter();
?>