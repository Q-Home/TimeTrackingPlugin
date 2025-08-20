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
$mqtt_log = '/opt/loxberry/data/plugins/timetracking-plugin/timetracking_mqtt.log';
$app_log = '/opt/loxberry/log/plugins/timetrackingplugin/app.log';

// Handle log actions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['clear_docker_log'])) {
        if (file_exists($docker_log)) {
            file_put_contents($docker_log, '');
            echo '<div class="alert alert-success">Docker log cleared successfully!</div>';
        }
    }
    
    if (isset($_POST['clear_mqtt_log'])) {
        if (file_exists($mqtt_log)) {
            file_put_contents($mqtt_log, '');
            echo '<div class="alert alert-success">MQTT log cleared successfully!</div>';
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
?>

<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">

<div class="container mt-5">
    <div class="col-lg-12">
        
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

        <!-- Application Logs -->
        <div class="card mb-4">
            <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                <h4 class="mb-0"><i class="fas fa-cog"></i> Application Logs</h4>
                <div>
                    <button class="btn btn-outline-light btn-sm" onclick="refreshLogs()">
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
    const logContainers = ['docker-log', 'mqtt-log', 'app-log'];
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
