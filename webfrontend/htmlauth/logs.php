<?php
require_once "loxberry_web.php";
require_once "loxberry_system.php";

$L = LBSystem::readlanguage("language.ini");
$template_title = "TimeTracking Plugin Logs";
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

// Log file locations
$docker_log = '/opt/loxberry/log/plugins/timetrackingplugin/docker.log';
$mqtt_log = '/opt/loxberry/log/plugins/timetrackingplugin/timetracking_mqtt.log';
$app_log = '/opt/loxberry/log/plugins/timetrackingplugin/app.log';
$docker_compose_path = '/opt/loxberry/bin/plugins/timetrackingplugin';

// App logging function - for general app and API events
function writeToLog($message, $type = 'INFO') {
    global $app_log;
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[$timestamp] [$type] $message" . PHP_EOL;
    
    // Ensure log directory exists
    $log_dir = dirname($app_log);
    if (!is_dir($log_dir)) {
        @mkdir($log_dir, 0777, true);
        @chmod($log_dir, 0777);
    }
    
    // Create file if it doesn't exist
    if (!file_exists($app_log)) {
        @touch($app_log);
        @chmod($app_log, 0666);
    }
    
    @file_put_contents($app_log, $logEntry, FILE_APPEND | LOCK_EX);
}

// Docker logging function - for docker commands and output
function writeToDockerLog($message, $type = 'INFO') {
    global $docker_log;
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[$timestamp] [$type] $message" . PHP_EOL;
    
    // Ensure log directory exists
    $log_dir = dirname($docker_log);
    if (!is_dir($log_dir)) {
        @mkdir($log_dir, 0777, true);
        @chmod($log_dir, 0777);
    }
    
    // Create file if it doesn't exist
    if (!file_exists($docker_log)) {
        @touch($docker_log);
        @chmod($docker_log, 0666);
    }
    
    @file_put_contents($docker_log, $logEntry, FILE_APPEND | LOCK_EX);
}

// MQTT logging function - for MQTT service events
function writeToMQTTLog($message, $type = 'INFO') {
    global $mqtt_log;
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[$timestamp] [$type] $message" . PHP_EOL;
    
    // Ensure log directory exists
    $log_dir = dirname($mqtt_log);
    if (!is_dir($log_dir)) {
        @mkdir($log_dir, 0777, true);
        @chmod($log_dir, 0777);
    }
    
    // Create file if it doesn't exist
    if (!file_exists($mqtt_log)) {
        @touch($mqtt_log);
        @chmod($mqtt_log, 0666);
    }
    
    @file_put_contents($mqtt_log, $logEntry, FILE_APPEND | LOCK_EX);
}

// Handle log actions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['clear_docker_log'])) {
        writeToDockerLog("Docker log cleared by user", "INFO");
        if (file_exists($docker_log)) {
            file_put_contents($docker_log, '');
            writeToLog("Docker log cleared successfully", "SUCCESS");
            echo '<div class="alert alert-success">Docker log cleared successfully!</div>';
        }
    }
    
    if (isset($_POST['clear_mqtt_log'])) {
        writeToMQTTLog("MQTT log cleared by user", "INFO");
        if (file_exists($mqtt_log)) {
            file_put_contents($mqtt_log, '');
            writeToLog("MQTT log cleared successfully", "SUCCESS");
            echo '<div class="alert alert-success">MQTT log cleared successfully!</div>';
        }
    }
    
    if (isset($_POST['clear_app_log'])) {
        writeToLog("App log cleared by user", "INFO");
        if (file_exists($app_log)) {
            file_put_contents($app_log, '');
            echo '<div class="alert alert-success">App log cleared successfully!</div>';
        }
    }
}

// Function to read and format log file
function readLogFile($filepath, $lines = 100) {
    if (!file_exists($filepath)) {
        return "Log file not found: $filepath";
    }
    
    $file = file($filepath);
    if ($file === false) {
        return "Could not read log file: $filepath";
    }
    
    // Get last N lines
    $totalLines = count($file);
    $startLine = max(0, $totalLines - $lines);
    $lastLines = array_slice($file, $startLine);
    
    return implode('', $lastLines);
}

// Function to format log content with colors
function formatLogContent($content) {
    $lines = explode("\n", $content);
    $formatted = '';
    
    foreach ($lines as $line) {
        if (empty(trim($line))) continue;
        
        $class = 'text-dark';
        if (strpos($line, '[ERROR]') !== false) {
            $class = 'text-danger';
        } elseif (strpos($line, '[SUCCESS]') !== false) {
            $class = 'text-success';
        } elseif (strpos($line, '[WARNING]') !== false) {
            $class = 'text-warning';
        } elseif (strpos($line, '[INFO]') !== false) {
            $class = 'text-info';
        } elseif (strpos($line, '[DOCKER]') !== false) {
            $class = 'text-primary';
        }
        
        $formatted .= '<div class="' . $class . '">' . htmlspecialchars($line) . '</div>';
    }
    
    return $formatted;
}

function readCommandOutput($command) {
    $output = shell_exec($command . ' 2>&1');
    if ($output === null || trim($output) === '') {
        return "No output returned for command:\n$command";
    }

    return $output;
}

function readMqttListenerConfig($allowedSettings) {
    // Filter at the Docker command: passwords and unrelated environment values
    // must never be returned to the web page, even if the container is stopped.
    $settingChecks = array_map(function ($key) {
        return '(eq $key ' . json_encode($key) . ')';
    }, $allowedSettings);
    $format = '{{println (json .State.Status)}}'
        . '{{range .Config.Env}}{{$key := index (split . "=") 0}}'
        . '{{if or ' . implode(' ', $settingChecks) . '}}{{println (json .)}}'
        . '{{else if and (eq $key "MQTT_PASSWORD") (ne . "MQTT_PASSWORD=")}}'
        . '{{println (json "MQTT_PASSWORD_CONFIGURED=true")}}{{end}}{{end}}';

    $output = shell_exec('sudo -n docker inspect --type=container --format '
        . escapeshellarg($format) . ' mqtt-listener 2>/dev/null');
    $lines = explode("\n", trim((string) $output));
    $status = json_decode(array_shift($lines), true);
    if (!is_string($status) || $status === '') {
        return null;
    }

    $config = ['status' => $status, 'settings' => [], 'password_configured' => false];
    foreach ($lines as $line) {
        $entry = json_decode($line, true);
        if (!is_string($entry) || strpos($entry, '=') === false) {
            continue;
        }
        [$key, $value] = explode('=', $entry, 2);
        if ($key === 'MQTT_PASSWORD_CONFIGURED') {
            $config['password_configured'] = $value === 'true';
        } elseif (in_array($key, $allowedSettings, true)) {
            $config['settings'][$key] = $value;
        }
    }
    return $config;
}

$mqtt_setting_labels = [
    'MQTT_BROKER' => 'Brokeradres',
    'MQTT_PORT' => 'Poort',
    'MQTT_USERNAME' => 'MQTT-gebruikersnaam',
    'MQTT_TOPIC' => 'Topic voor badge-events',
    'MQTT_STATS_TOPIC' => 'Topic voor statistiekvragen',
    'MQTT_PUB_TOPIC' => 'Topic voor terugkoppeling',
];
$mqtt_config = readMqttListenerConfig(array_keys($mqtt_setting_labels));
$mqtt_status_labels = [
    'running' => 'Actief',
    'restarting' => 'Herstart bezig',
    'exited' => 'Gestopt',
    'created' => 'Aangemaakt, nog niet gestart',
    'paused' => 'Gepauzeerd',
    'dead' => 'Uitgevallen',
];

$mqtt_docker_logs = readCommandOutput(
    "cd " . escapeshellarg($docker_compose_path) . " && sudo -n docker compose logs --tail=1000 mqtt-listener"
);
$mqtt_docker_lines = array_filter(explode("\n", $mqtt_docker_logs), function ($line) {
    return trim($line) !== '' && strpos($line, '[PRINT] Main loop heartbeat - ') === false;
});
$mqtt_docker_logs = implode("\n", array_slice($mqtt_docker_lines, -200));
if ($mqtt_docker_logs === '') {
    $mqtt_docker_logs = 'Geen recente meldingen buiten de periodieke heartbeat.';
}
?>

<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">

<div class="container mt-5">
    <div class="col-lg-12">

        <section class="card mb-4" aria-labelledby="mqtt-diagnostics-title">
            <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                <h4 class="mb-0" id="mqtt-diagnostics-title"><i class="fas fa-satellite-dish" aria-hidden="true"></i> Diagnose Miniserver-koppeling</h4>
                <button type="button" class="btn btn-outline-light btn-sm" onclick="refreshLogs()">Vernieuwen</button>
            </div>
            <div class="card-body">
                <p>De plugin ontvangt badge-events via MQTT. De onderstaande aanmelding geldt voor de broker, niet voor de Miniserver zelf.</p>
                <?php if ($mqtt_config === null): ?>
                    <p class="alert alert-warning">De listenercontainer kon niet worden uitgelezen. Controleer bij <a href="settings.php">Settings</a> of de container bestaat en of Docker bereikbaar is.</p>
                <?php else: ?>
                    <dl class="row mb-2">
                        <dt class="col-sm-5">Status listenercontainer</dt>
                        <dd class="col-sm-7"><?= htmlspecialchars($mqtt_status_labels[$mqtt_config['status']] ?? $mqtt_config['status']) ?></dd>
                        <?php foreach ($mqtt_setting_labels as $key => $label): ?>
                            <?php $value = $mqtt_config['settings'][$key] ?? ''; ?>
                            <dt class="col-sm-5"><?= htmlspecialchars($label) ?></dt>
                            <dd class="col-sm-7 text-break"><?= htmlspecialchars($value === '' ? 'Niet ingesteld' : $value) ?></dd>
                        <?php endforeach; ?>
                        <dt class="col-sm-5">MQTT-wachtwoord</dt>
                        <dd class="col-sm-7"><?= $mqtt_config['password_configured'] ? 'Ingesteld (verborgen)' : 'Niet ingesteld' ?></dd>
                    </dl>
                    <p class="small text-muted">Dit zijn de instellingen van de container. Een actieve container betekent dat het proces draait; de verbinding met de broker controleer je in de log.</p>
                <?php endif; ?>
                <p class="mb-0">Doe een testscan, vernieuw de pagina en kijk in de <a href="#mqtt-listener-output">listenerlog</a> naar <code>Received MQTT message</code> en de daaropvolgende API-melding. Voor oudere meldingen kun je de <a href="#mqtt-log">MQTT-log</a> raadplegen.</p>
            </div>
        </section>

        <!-- Docker Logs -->
        <div class="card mb-4">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h4 class="mb-0"><i class="fas fa-docker"></i> Docker Logs</h4>
                <div>
                    <form method="POST" class="d-inline">
                        <button type="submit" name="clear_docker_log" class="btn btn-outline-light btn-sm" 
                                onclick="return confirm('Are you sure you want to clear the Docker log?')">
                            <i class="fas fa-trash"></i> Clear Log
                        </button>
                    </form>
                    <button class="btn btn-outline-light btn-sm ml-2" onclick="refreshLogs()">
                        <i class="fas fa-refresh"></i> Refresh
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div id="docker-log" style="height: 400px; overflow-y: auto; background: #f8f9fa; padding: 15px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 12px;">
                    <?= formatLogContent(readLogFile($docker_log, 200)) ?>
                </div>
                <small class="text-muted mt-2 d-block">
                    <i class="fas fa-info-circle"></i> Showing last 200 lines from: <?= $docker_log ?>
                </small>
            </div>
        </div>

        <!-- MQTT Logs -->
        <div class="card mb-4">
            <div class="card-header bg-success text-white d-flex justify-content-between align-items-center">
                <h4 class="mb-0"><i class="fas fa-broadcast-tower"></i> MQTT Logs</h4>
                <div>
                    <form method="POST" class="d-inline">
                        <button type="submit" name="clear_mqtt_log" class="btn btn-outline-light btn-sm"
                                onclick="return confirm('Are you sure you want to clear the MQTT log?')">
                            <i class="fas fa-trash"></i> Clear Log
                        </button>
                    </form>
                    <button class="btn btn-outline-light btn-sm ml-2" onclick="refreshLogs()">
                        <i class="fas fa-refresh"></i> Refresh
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div id="mqtt-log" style="height: 400px; overflow-y: auto; background: #f8f9fa; padding: 15px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 12px;">
                    <?= formatLogContent(readLogFile($mqtt_log, 200)) ?>
                </div>
                <small class="text-muted mt-2 d-block">
                    <i class="fas fa-info-circle"></i> Showing last 200 lines from: <?= $mqtt_log ?>
                </small>
            </div>
        </div>

        <div class="card mb-4" id="mqtt-listener-output">
            <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                <h4 class="mb-0"><i class="fas fa-terminal"></i> MQTT Listener Container Output</h4>
                <div>
                    <button class="btn btn-outline-light btn-sm" onclick="refreshLogs()">
                        <i class="fas fa-refresh"></i> Refresh
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div id="mqtt-container-log" style="height: 400px; overflow-y: auto; background: #f8f9fa; padding: 15px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 12px;">
                    <?= formatLogContent($mqtt_docker_logs) ?>
                </div>
                <small class="text-muted mt-2 d-block">
                    <i class="fas fa-info-circle"></i> Maximaal 200 meldingen uit de recente containeruitvoer. Herhaalde heartbeats worden overgeslagen.
                </small>
            </div>
        </div>

        <!-- Application Logs -->
        <div class="card mb-4">
            <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                <h4 class="mb-0"><i class="fas fa-cog"></i> Application Logs</h4>
                <div>
                    <form method="POST" class="d-inline">
                        <button type="submit" name="clear_app_log" class="btn btn-outline-light btn-sm" 
                                onclick="return confirm('Are you sure you want to clear the App log?')">
                            <i class="fas fa-trash"></i> Clear Log
                        </button>
                    </form>
                    <button class="btn btn-outline-light btn-sm ml-2" onclick="refreshLogs()">
                        <i class="fas fa-refresh"></i> Refresh
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div id="app-log" style="height: 400px; overflow-y: auto; background: #f8f9fa; padding: 15px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 12px;">
                    <?= formatLogContent(readLogFile($app_log, 200)) ?>
                </div>
                <small class="text-muted mt-2 d-block">
                    <i class="fas fa-info-circle"></i> Showing last 200 lines from: <?= $app_log ?>
                </small>
            </div>
        </div>

        <!-- Log Legend -->
        <div class="card">
            <div class="card-header bg-secondary text-white">
                <h5 class="mb-0"><i class="fas fa-question-circle"></i> Log Level Legend</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <ul class="list-unstyled">
                            <li><span class="text-danger"><strong>[ERROR]</strong></span> - Critical errors that need attention</li>
                            <li><span class="text-warning"><strong>[WARNING]</strong></span> - Warning messages</li>
                            <li><span class="text-info"><strong>[INFO]</strong></span> - General information</li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <ul class="list-unstyled">
                            <li><span class="text-success"><strong>[SUCCESS]</strong></span> - Successful operations</li>
                            <li><span class="text-primary"><strong>[DOCKER]</strong></span> - Docker command outputs</li>
                            <li><span class="text-dark"><strong>[OTHER]</strong></span> - Other log messages</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>

    </div>
</div>

<script>
function refreshLogs() {
    location.reload();
}

// Auto-refresh every 30 seconds
setInterval(function() {
    refreshLogs();
}, 30000);

// Auto-scroll to bottom of log containers
window.onload = function() {
    const logContainers = ['docker-log', 'mqtt-log', 'mqtt-container-log', 'app-log'];
    logContainers.forEach(function(id) {
        const container = document.getElementById(id);
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    });
};
</script>

<style>
.card {
    border: none;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.card-header {
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
}

#docker-log::-webkit-scrollbar,
#mqtt-log::-webkit-scrollbar,
#app-log::-webkit-scrollbar {
    width: 8px;
}

#docker-log::-webkit-scrollbar-track,
#mqtt-log::-webkit-scrollbar-track,
#app-log::-webkit-scrollbar-track {
    background: #f1f1f1;
}

#docker-log::-webkit-scrollbar-thumb,
#mqtt-log::-webkit-scrollbar-thumb,
#app-log::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 4px;
}

#docker-log::-webkit-scrollbar-thumb:hover,
#mqtt-log::-webkit-scrollbar-thumb:hover,
#app-log::-webkit-scrollbar-thumb:hover {
    background: #555;
}
</style>

<?php LBWeb::lbfooter(); ?>
