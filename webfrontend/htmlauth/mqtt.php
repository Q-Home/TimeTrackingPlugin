<?php
require_once "loxberry_web.php";
require_once "loxberry_system.php";

// This will read your language files to the array $L
$L = LBSystem::readlanguage("language.ini");
$template_title = "TimeTracking Plugin";
$helplink = "http://www.loxwiki.eu:80/x/2wzL";
$helptemplate = "help.html";

// The Navigation Bar
$navbar[1]['Name'] = 'Status';
$navbar[1]['URL'] = 'index.php';

$navbar[2]['Name'] = 'MQTT Settings';
$navbar[2]['URL'] = 'mqtt.php';
$navbar[2]['active'] = True;

$navbar[3]['Name'] = 'Logs';
$navbar[3]['URL'] = 'logs.php';

// Now output the header, it will include your navigation bar
LBWeb::lbheader($template_title, $helplink, $helptemplate);

// Define variables
$config_file = './mqtt_config.ini';
$log_file = './Log_file.log';

// Logging function
function log_message($level, $message) {
    global $log_file;
    $timestamp = date('Y-m-d H:i:s');
    $log_entry = "[$timestamp] [$level] $message\n";
    file_put_contents($log_file, $log_entry, FILE_APPEND);
}

// Check if the config file exists and read the values
if (file_exists($config_file)) {
    $config = parse_ini_file($config_file, true);
    $mqtt_host = $config['MQTT']['host'];
    $mqtt_port = $config['MQTT']['port'];
    $mqtt_user = $config['MQTT']['user'];
    $mqtt_password = $config['MQTT']['password'];
    $mqtt_topic_prefix = $config['MQTT']['topic_prefix'];
} else {
    // Set default values if the config file does not exist
    $mqtt_host = '127.0.0.1';
    $mqtt_port = '1883';
    $mqtt_user = 'loxberry';
    $mqtt_password = 'loxberry';
    $mqtt_topic_prefix = 'cityscoop/synco/';
}

// Process form submission
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mqtt_host = $_POST['mqtt_host'];
    $mqtt_port = $_POST['mqtt_port'];
    $mqtt_user = $_POST['mqtt_user'];
    $mqtt_password = $_POST['mqtt_password'];
    $mqtt_topic_prefix = $_POST['mqtt_topic_prefix'];

    // Log the received data
    log_message('info', "Received data: MQTT Host: $mqtt_host, Port: $mqtt_port, User: $mqtt_user, Topic Prefix: $mqtt_topic_prefix");

    // Save the settings or process them as needed
    if (!file_exists($config_dir)) {
        mkdir($config_dir, 0755, true);
    }
    $config_data = "[MQTT]\nhost=$mqtt_host\nport=$mqtt_port\nuser=$mqtt_user\npassword=$mqtt_password\ntopic_prefix=$mqtt_topic_prefix\n";
    file_put_contents($config_file, $config_data);

    // Reload the configuration to update the form with the saved values
    $config = parse_ini_file($config_file, true);
    $mqtt_host = $config['MQTT']['host'];
    $mqtt_port = $config['MQTT']['port'];
    $mqtt_user = $config['MQTT']['user'];
    $mqtt_password = $config['MQTT']['password'];
    $mqtt_topic_prefix = $config['MQTT']['topic_prefix'];
}

?>

<form method="post">
    <div class="form-group">
        <label for="mqtt_host">MQTT Broker Address:</label>
        <input type="text" id="mqtt_host" name="mqtt_host" value="<?= htmlspecialchars($mqtt_host) ?>" class="form-control" disabeld>
    </div>

    <div class="form-group">
        <label for="mqtt_port">Port:</label>
        <input type="number" id="mqtt_port" name="mqtt_port" value="<?= htmlspecialchars($mqtt_port) ?>" class="form-control" disabeld>
    </div>

    <div class="form-group">
        <label for="mqtt_user">Username:</label>
        <input type="text" id="mqtt_user" name="mqtt_user" value="<?= htmlspecialchars($mqtt_user) ?>" class="form-control">
    </div>

    <div class="form-group">
        <label for="mqtt_password">Password:</label>
        <input type="password" id="mqtt_password" name="mqtt_password" value="<?= htmlspecialchars($mqtt_password) ?>" class="form-control">
    </div>

    <div class="form-group">
        <label for="mqtt_topic_prefix">MQTT Topic Prefix:</label>
        <input type="text" id="mqtt_topic_prefix" name="mqtt_topic_prefix" value="<?= htmlspecialchars($mqtt_topic_prefix) ?>" class="form-control" required>
    </div>

    <button type="submit" class="btn btn-primary">Save Settings</button>
</form>



<?php  
// Finally print the footer  
LBWeb::lbfooter();
?>