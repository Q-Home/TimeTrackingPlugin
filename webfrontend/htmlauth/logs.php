<?php
require_once "loxberry_web.php";
<<<<<<< HEAD
=======

// This will read your language files to the array $L
$L = LBSystem::readlanguage("language.ini");

$template_title = "TimeTracking plugin";
$helplink = "http://www.loxwiki.eu:80/x/2wzL";
$helptemplate = "help.html";

// The Navigation Bar
$navbar[1]['Name'] = 'Status';
$navbar[1]['URL'] = 'index.php';

$navbar[2]['Name'] = 'MQTT Settings';
$navbar[2]['URL'] = 'mqtt.php';
$navbar[3]['active'] = True;

$navbar[3]['Name'] = 'Logs';
$navbar[3]['URL'] = 'logs.php';

// Now output the header, it will include your navigation bar
LBWeb::lbheader($template_title, $helplink, $helptemplate);

// This is the main area for your plugin
?>

<?php
$logFile = '/opt/loxberry/data/plugins/timetrackingplugin/timetracking_mqtt.log';

// Check if the log file exists
if (!file_exists($logFile)) {
    die("Log file not found.");
}

// Read the contents of the log file
$logContents = file($logFile, <?php
require_once "loxberry_web.php";
>>>>>>> f77fddfd6f50428b11db86d11d5bac5a61d792a3
require_once "loxberry_system.php";

$L = LBSystem::readlanguage("language.ini");
$template_title = "Plugin Logs";
$helplink = "http://www.loxwiki.eu:80/x/2wzL";
$helptemplate = "help.html";

// Navigation
$navbar[1]['Name'] = 'Home';
$navbar[1]['URL'] = 'index.php';
$navbar[2]['Name'] = 'Settings';
$navbar[2]['URL'] = 'settings.php';
$navbar[3]['Name'] = 'Logs';
$navbar[3]['URL'] = 'logs.php';
$navbar[3]['active'] = true;

LBWeb::lbheader($template_title, $helplink, $helptemplate);

// Define log paths
$log_dir = "/opt/loxberry/data/plugins/timetrackingplugin/";
$log_files = [
    "timetracking_mqtt.log" => "MQTT Listener"
];

$selected_log = $_GET['log'] ?? 'timetracking_mqtt.log';
$log_path = realpath($log_dir . basename($selected_log));

$valid = ($log_path && strpos($log_path, realpath($log_dir)) === 0 && file_exists($log_path));
$log_lines = [];

if ($valid) {
    $log_lines = file($log_path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    $log_lines = array_reverse($log_lines);
    $log_lines = array_slice($log_lines, 0, 500);
}

// Handle AJAX request early and exit
if (isset($_GET['ajax']) && $_GET['ajax'] == 1) {
    if ($valid) {
        foreach ($log_lines as $line) {
            $logClass = 'log-info';
            if (stripos($line, '[error]') !== false) {
                $logClass = 'log-error';
            } elseif (stripos($line, '[warning]') !== false) {
                $logClass = 'log-warning';
            }
            echo '<div class="' . $logClass . '">' . htmlspecialchars(trim($line)) . '</div>';
        }
    } else {
        echo '<div class="text-danger">Log file not found or invalid.</div>';
    }
    exit;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Log Viewer</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" />
    <style>
        #log-viewer {
            width: 100%;
            height: 600px;
            overflow-y: scroll;
            border: 1px solid #ccc;
            padding: 10px;
            margin-top: 20px;
            font-family: monospace;
            font-size: 13px;
            background-color: #f9f9f9;
        }
        .log-info { color: #000000; }
        .log-warning { color: #FF9800; }
        .log-error { color: #F44336; }
        .log-info, .log-warning, .log-error {
            padding: 5px 0;
            border-bottom: 1px solid #ddd;
            white-space: pre-wrap;
        }
        .nav-tabs .nav-link.active {
            font-weight: bold;
        }
        #refresh-log { cursor: pointer; }
    </style>
</head>
<body>
<div class="container mt-5">
    <div class="col-lg-10 offset-lg-1">
        <h3 class="mb-4">Log Viewer</h3>

        <ul class="nav nav-tabs mb-3">
            <?php foreach ($log_files as $filename => $label): ?>
                <li class="nav-item">
                    <a class="nav-link <?= ($selected_log === $filename) ? 'active' : '' ?>" href="?log=<?= urlencode($filename) ?>">
                        <?= htmlspecialchars($label) ?>
                    </a>
                </li>
            <?php endforeach; ?>
            <li class="nav-item ml-auto">
                <a href="#" id="refresh-log" class="nav-link" title="Refresh Log">Refresh</a>
            </li>
        </ul>

        <div id="log-viewer">
            <?php if ($valid): ?>
                <?php foreach ($log_lines as $line): ?>
                    <?php
                    $logClass = 'log-info';
                    if (stripos($line, '[error]') !== false) {
                        $logClass = 'log-error';
                    } elseif (stripos($line, '[warning]') !== false) {
                        $logClass = 'log-warning';
                    }
                    ?>
                    <div class="<?= $logClass ?>"><?= htmlspecialchars(trim($line)) ?></div>
                <?php endforeach; ?>
            <?php else: ?>
                <div class="text-danger">Log file not found or invalid.</div>
            <?php endif; ?>
        </div>
    </div>
</div>

<script>
    document.getElementById('refresh-log').addEventListener('click', function(event) {
        event.preventDefault();
        const params = new URLSearchParams(window.location.search);
        const selectedLog = params.get('log') || 'timetracking_mqtt.log';

        fetch('logs.php?log=' + encodeURIComponent(selectedLog) + '&ajax=1')
            .then(response => response.text())
            .then(html => {
                document.getElementById('log-viewer').innerHTML = html;
            })
            .catch(error => {
                alert('Error refreshing log: ' + error);
            });
    });
</script>

<?php LBWeb::lbfooter(); ?>
</body>
</html>
