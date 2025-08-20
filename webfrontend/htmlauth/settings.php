<?php
require_once "loxberry_web.php";
require_once "loxberry_system.php";

$L = LBSystem::readlanguage("language.ini");
$template_title = "TimeTracking Plugin Settings";
$helplink = "http://www.loxwiki.eu:80/x/2wzL";
$helptemplate = "help.html";

// Navigation
$navbar[1]['Name'] = 'Home';
$navbar[1]['URL'] = 'index.php';
$navbar[2]['Name'] = 'Settings';
$navbar[2]['URL'] = 'settings.php';
$navbar[2]['active'] = true;
$navbar[3]['Name'] = 'Logs';
$navbar[3]['URL'] = 'logs.php';

LBWeb::lbheader($template_title, $helplink, $helptemplate);

// File locations
$settings_file = '/opt/loxberry/data/plugins/timetrackingplugin/settings.json';
$docker_compose_file = '/opt/loxberry/bin/plugins/timetrackingplugin/docker-compose.yml';
$run_script = '/opt/loxberry/bin/plugins/timetrackingplugin/run_docker_compose.sh';
$log_file = '/opt/loxberry/log/plugins/timetrackingplugin/docker.log';

// Logging function
function writeToLog($message, $type = 'INFO') {
    global $log_file;
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[$timestamp] [$type] $message" . PHP_EOL;
    
    // Ensure log directory exists
    $log_dir = dirname($log_file);
    if (!is_dir($log_dir)) {
        mkdir($log_dir, 0755, true);
    }
    
    file_put_contents($log_file, $logEntry, FILE_APPEND | LOCK_EX);
}

// Load files
$settings_contents = file_exists($settings_file) ? file_get_contents($settings_file) : '';
$docker_compose_contents = file_exists($docker_compose_file) ? file_get_contents($docker_compose_file) : '';

// Handle form submissions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Save settings and docker-compose files
    if (isset($_POST['save_settings'])) {
        writeToLog("Settings save requested by user", "INFO");
        
        if (isset($_POST['settings_json'])) {
            file_put_contents($settings_file, $_POST['settings_json']);
            writeToLog("Settings JSON file updated", "INFO");
        }
        if (isset($_POST['docker_compose'])) {
            file_put_contents($docker_compose_file, $_POST['docker_compose']);
            writeToLog("Docker Compose YAML file updated", "INFO");
        }

        echo '<div class="alert alert-success text-center">
                <i class="fas fa-check-circle"></i> Settings saved successfully!
              </div>';
        writeToLog("Settings saved successfully", "SUCCESS");

        // Reload updated content for display after save
        $settings_contents = file_get_contents($settings_file);
        $docker_compose_contents = file_get_contents($docker_compose_file);
    }
    
    // Start Docker Compose
    if (isset($_POST['start_docker'])) {
        writeToLog("Docker Compose start requested by user", "INFO");
        $docker_compose_path = '/opt/loxberry/bin/plugins/timetrackingplugin';
        
        if (file_exists($run_script)) {
            chmod($run_script, 0755);
            $cmd = "cd " . escapeshellarg($docker_compose_path) . " && bash run_docker_compose.sh 2>&1";
            writeToLog("Executing custom run script: $cmd", "INFO");
        } else {
            $cmd = "cd " . escapeshellarg($docker_compose_path) . " && docker compose up -d 2>&1";
            writeToLog("Executing docker compose up: $cmd", "INFO");
        }
        
        $output = shell_exec($cmd);
        writeToLog("Docker start command output: " . trim($output), "DOCKER");
        
        if (strpos($output, 'error') !== false || strpos($output, 'Error') !== false) {
            writeToLog("Docker start encountered errors", "ERROR");
        } else {
            writeToLog("Docker containers started successfully", "SUCCESS");
        }
        
        echo '<div class="alert alert-success">
                <h5><i class="fas fa-play-circle"></i> Docker Compose Started</h5>
                <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto;">' . 
                htmlspecialchars($output) . '</pre>
              </div>';
    }
    
    // Stop Docker Compose
    if (isset($_POST['stop_docker'])) {
        writeToLog("Docker Compose stop requested by user", "INFO");
        $docker_compose_path = '/opt/loxberry/bin/plugins/timetrackingplugin';
        $cmd = "cd " . escapeshellarg($docker_compose_path) . " && docker compose down 2>&1";
        writeToLog("Executing docker compose down: $cmd", "INFO");
        
        $output = shell_exec($cmd);
        writeToLog("Docker stop command output: " . trim($output), "DOCKER");
        
        if (strpos($output, 'error') !== false || strpos($output, 'Error') !== false) {
            writeToLog("Docker stop encountered errors", "ERROR");
        } else {
            writeToLog("Docker containers stopped successfully", "SUCCESS");
        }
        
        echo '<div class="alert alert-warning">
                <h5><i class="fas fa-stop-circle"></i> Docker Compose Stopped</h5>
                <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto;">' . 
                htmlspecialchars($output) . '</pre>
              </div>';
    }
    
    // Restart Docker Compose (stop + start)
    if (isset($_POST['restart_docker'])) {
        writeToLog("Docker Compose restart requested by user", "INFO");
        $docker_compose_path = '/opt/loxberry/bin/plugins/timetrackingplugin';
        
        // First stop
        $stop_cmd = "cd " . escapeshellarg($docker_compose_path) . " && docker compose down 2>&1";
        writeToLog("Executing restart - stopping containers: $stop_cmd", "INFO");
        $stop_output = shell_exec($stop_cmd);
        writeToLog("Docker restart stop output: " . trim($stop_output), "DOCKER");
        
        // Then start
        if (file_exists($run_script)) {
            chmod($run_script, 0755);
            $start_cmd = "cd " . escapeshellarg($docker_compose_path) . " && bash run_docker_compose.sh 2>&1";
            writeToLog("Executing restart - starting with custom script: $start_cmd", "INFO");
        } else {
            $start_cmd = "cd " . escapeshellarg($docker_compose_path) . " && docker compose up -d 2>&1";
            writeToLog("Executing restart - starting containers: $start_cmd", "INFO");
        }
        $start_output = shell_exec($start_cmd);
        writeToLog("Docker restart start output: " . trim($start_output), "DOCKER");
        
        if (strpos($start_output, 'error') !== false || strpos($start_output, 'Error') !== false) {
            writeToLog("Docker restart encountered errors", "ERROR");
        } else {
            writeToLog("Docker containers restarted successfully", "SUCCESS");
        }
        
        echo '<div class="alert alert-info">
                <h5><i class="fas fa-redo-alt"></i> Docker Compose Restarted</h5>
                <h6>Stop Output:</h6>
                <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 150px; overflow-y: auto;">' . 
                htmlspecialchars($stop_output) . '</pre>
                <h6>Start Output:</h6>
                <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 150px; overflow-y: auto;">' . 
                htmlspecialchars($start_output) . '</pre>
              </div>';
    }
    
    // Check Docker status
    if (isset($_POST['check_status'])) {
        writeToLog("Docker status check requested by user", "INFO");
        $docker_compose_path = '/opt/loxberry/bin/plugins/timetrackingplugin';
        $cmd = "cd " . escapeshellarg($docker_compose_path) . " && docker ps -a 2>&1";
        writeToLog("Executing status check: $cmd", "INFO");
        
        $output = shell_exec($cmd);
        writeToLog("Docker status output: " . trim($output), "DOCKER");
        
        echo '<div class="alert alert-info">
                <h5><i class="fas fa-info-circle"></i> Docker Container Status</h5>
                <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto;">' . 
                htmlspecialchars($output) . '</pre>
              </div>';
    }
}
?>

<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">

<div class="container mt-5">
    <div class="col-lg-10 offset-lg-1">
        
        <!-- Docker Control Panel -->
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0"><i class="fas fa-docker"></i> Docker Control Panel</h4>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-12 mb-3">
                        <p class="text-muted">
                            <i class="fas fa-info-circle"></i> 
                            Manage your TimeTracking Docker containers. Use Start to launch all services, Stop to shut them down, or Restart to apply configuration changes.
                        </p>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-3 mb-2">
                        <form method="POST" style="display: inline-block; width: 100%;">
                            <button type="submit" name="start_docker" class="btn btn-success btn-block">
                                <i class="fas fa-play"></i> Start
                            </button>
                        </form>
                    </div>
                    
                    <div class="col-md-3 mb-2">
                        <form method="POST" style="display: inline-block; width: 100%;">
                            <button type="submit" name="stop_docker" class="btn btn-danger btn-block">
                                <i class="fas fa-stop"></i> Stop
                            </button>
                        </form>
                    </div>
                    
                    <div class="col-md-3 mb-2">
                        <form method="POST" style="display: inline-block; width: 100%;">
                            <button type="submit" name="restart_docker" class="btn btn-warning btn-block">
                                <i class="fas fa-redo-alt"></i> Restart
                            </button>
                        </form>
                    </div>
                    
                    <div class="col-md-3 mb-2">
                        <form method="POST" style="display: inline-block; width: 100%;">
                            <button type="submit" name="check_status" class="btn btn-info btn-block">
                                <i class="fas fa-info-circle"></i> Status
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <!-- Configuration Files -->
        <div class="card">
            <div class="card-header bg-secondary text-white">
                <h4 class="mb-0"><i class="fas fa-cog"></i> Configuration Files</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <h5 class="mb-3"><i class="fas fa-file-code"></i> Settings JSON File</h5>
                    <div class="form-group">
                        <textarea name="settings_json" class="form-control" rows="20" 
                                  style="font-family: 'Courier New', monospace; font-size: 12px;"
                                  placeholder="Enter your JSON settings here..."><?= htmlspecialchars($settings_contents) ?></textarea>
                    </div>

                    <h5 class="mb-3 mt-4"><i class="fas fa-file-alt"></i> Docker Compose YAML File</h5>
                    <div class="form-group">
                        <textarea name="docker_compose" class="form-control" rows="30" 
                                  style="font-family: 'Courier New', monospace; font-size: 12px;"
                                  placeholder="Enter your docker-compose.yml content here..."><?= htmlspecialchars($docker_compose_contents) ?></textarea>
                    </div>

                    <div class="text-center mt-4 mb-3">
                        <button type="submit" name="save_settings" class="btn btn-primary btn-lg px-5">
                            <i class="fas fa-save"></i> Save Configuration Files
                        </button>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- Help Section -->
        <div class="card mt-4">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0"><i class="fas fa-question-circle"></i> Help & Commands</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6><i class="fas fa-terminal"></i> Docker Commands:</h6>
                        <ul class="list-unstyled">
                            <li><strong><i class="fas fa-play text-success"></i> Start:</strong> <code>docker-compose up -d</code></li>
                            <li><strong><i class="fas fa-stop text-danger"></i> Stop:</strong> <code>docker-compose down</code></li>
                            <li><strong><i class="fas fa-redo-alt text-warning"></i> Restart:</strong> Stop + Start containers</li>
                            <li><strong><i class="fas fa-info-circle text-info"></i> Status:</strong> <code>docker-compose ps</code></li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="fas fa-exclamation-triangle"></i> Important Notes:</h6>
                        <ul class="list-unstyled">
                            <li><strong>Save First:</strong> Always save configuration before restarting</li>
                            <li><strong>Stop Safely:</strong> Use Stop button to properly shutdown containers</li>
                            <li><strong>Check Status:</strong> Verify containers are running after start</li>
                            <li><strong>Logs:</strong> Check output messages for errors</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>

    </div>
</div>

<style>
.card {
    border: none;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    margin-bottom: 1rem;
}

.card-header {
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
}

.btn {
    border-radius: 0.25rem;
    transition: all 0.2s;
}

.btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 0.25rem 0.5rem rgba(0, 0, 0, 0.1);
}

textarea {
    resize: vertical;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
}

pre {
    font-size: 12px;
    border: 1px solid #e9ecef;
}

.alert {
    border-radius: 0.25rem;
    border: none;
}

.text-muted {
    font-size: 0.9rem;
}
</style>

<?php LBWeb::lbfooter(); ?>