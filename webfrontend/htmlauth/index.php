<?php
require_once "loxberry_web.php";
require_once "loxberry_system.php";

// Titel en navigatie
$L = LBSystem::readlanguage("language.ini");
$template_title = "TimeTracking Plugin";
$helplink = "http://www.loxwiki.eu:80/x/2wzL";
$helptemplate = "help.html";

$navbar[1]['Name'] = 'Status';
$navbar[1]['URL'] = 'index.php';
$navbar[1]['active'] = True;
$navbar[2]['Name'] = 'MQTT Settings';
$navbar[2]['URL'] = 'mqtt.php';
$navbar[3]['Name'] = 'Logs';
$navbar[3]['URL'] = 'logs.php';

// Toon header
LBWeb::lbheader($template_title, $helplink, $helptemplate);

echo "<h2>Personeel Badges & Werktijden</h2>";

// ---- MongoDB connectie ----
// PAS AAN indien je IP verschilt
$mongo_host = "mongodb://192.168.0.100:27017";
$mongo_db = "timetracking";
$mongo_collection = "devices";

$filter_user = isset($_GET['user']) ? trim($_GET['user']) : "";

try {
    // 1) Connectie
    $manager = new MongoDB\Driver\Manager($mongo_host);

    // 2) Filter: als ?user= is opgegeven
    $filter = [];
    if ($filter_user !== "") {
        $filter = ['user' => $filter_user];
    }

    $query = new MongoDB\Driver\Query($filter);
    $rows = $manager->executeQuery("$mongo_db.$mongo_collection", $query);

    // 3) Data array opbouwen
    $badges = [];
    foreach ($rows as $doc) {
        $badges[] = [
            'badgecode' => $doc->badgecode ?? '',
            'user' => $doc->user ?? '',
            'scan_time' => $doc->scan_time ?? '',
            'status' => $doc->status ?? '',
            'action' => $doc->action ?? ''
        ];
    }

} catch (MongoDB\Driver\Exception\Exception $e) {
    echo "<p style='color:red;'>MongoDB fout: " . $e->getMessage() . "</p>";
}

?>

<!-- Filter formulier -->
<form method="get" style="margin-bottom: 20px;">
    <label for="user">Filter op gebruiker:</label>
    <input type="text" name="user" id="user" value="<?=htmlspecialchars($filter_user)?>">
    <button type="submit">Filter</button>
    <a href="index.php">Toon alles</a>
</form>

<!-- Tabel -->
<table style="width: 100%; table-layout: fixed;" cellpadding="5" cellspacing="0" border="1">
    <tr>
        <th style="width: 20%;">Badge ID</th>
        <th style="width: 20%;">Naam</th>
        <th style="width: 20%;">Scan tijd</th>
        <th style="width: 20%;">Status</th>
        <th style="width: 20%;">Actie</th>
    </tr>
    <?php if (count($badges) === 0): ?>
        <tr><td colspan="5">Geen resultaten gevonden.</td></tr>
    <?php else: ?>
        <?php foreach ($badges as $badge): ?>
            <tr>
                <td><?=htmlspecialchars($badge['badgecode'])?></td>
                <td><?=htmlspecialchars($badge['user'])?></td>
                <td><?=htmlspecialchars($badge['scan_time'])?></td>
                <td><?=htmlspecialchars($badge['status'])?></td>
                <td><?=htmlspecialchars($badge['action'])?></td>
            </tr>
        <?php endforeach; ?>
    <?php endif; ?>
</table>

<?php  
// Footer tonen
LBWeb::lbfooter();
?>
