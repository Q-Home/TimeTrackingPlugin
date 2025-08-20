<?php
require_once "loxberry_web.php";
require_once "loxberry_system.php";

// Titel en navigatie
$L = LBSystem::readlanguage("language.ini");
$template_title = "TimeTracking Plugin";
$helplink = "http://www.loxwiki.eu:80/x/2wzL";
$helptemplate = "help.html";

// Navigation
$navbar[1]['Name'] = 'Home';
$navbar[1]['URL'] = 'index.php';
$navbar[2]['Name'] = 'Settings';
$navbar[2]['URL'] = 'settings.php';
$navbar[1]['active'] = true;
$navbar[3]['Name'] = 'Logs';
$navbar[3]['URL'] = 'logs.php';

// Toon header
LBWeb::lbheader($template_title, $helplink, $helptemplate);

// Settings file path
$settings_file = '/opt/loxberry/data/plugins/timetrackingplugin/settings.json';
$log_file = '/opt/loxberry/log/plugins/timetrackingplugin/api_debug.log';

// Function to write debug logs
function writeDebugLog($message) {
    global $log_file;
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[$timestamp] $message" . PHP_EOL;
    
    // Ensure log directory exists
    $log_dir = dirname($log_file);
    if (!is_dir($log_dir)) {
        mkdir($log_dir, 0755, true);
    }
    
    file_put_contents($log_file, $logEntry, FILE_APPEND | LOCK_EX);
}

// Function to load settings
function loadSettings($settings_file) {
    $default_settings = [
        'backend_url' => 'http://localhost:5000/api/v1'
    ];
    
    if (file_exists($settings_file)) {
        $settings_content = file_get_contents($settings_file);
        $settings = json_decode($settings_content, true);
        
        if (json_last_error() === JSON_ERROR_NONE && is_array($settings)) {
            // Merge with defaults to ensure all required keys exist
            return array_merge($default_settings, $settings);
        }
    }
    
    return $default_settings;
}

// Function to save settings
function saveSettings($settings_file, $settings) {
    // Ensure directory exists
    $dir = dirname($settings_file);
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
    }
    
    return file_put_contents($settings_file, json_encode($settings, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
}

// Load current settings
$settings = loadSettings($settings_file);

// Backend API configuration from settings
$backend_url = $settings['backend_url'];

// Function to make API requests with improved error handling
function makeAPIRequest($url, $method = 'GET', $data = null) {
    writeDebugLog("Making API request: $method $url");
    
    // Check if URL is valid
    if (!filter_var($url, FILTER_VALIDATE_URL)) {
        writeDebugLog("Invalid URL: $url");
        return ['success' => false, 'message' => 'Ongeldige URL configuratie'];
    }
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
    
    if ($method === 'POST') {
        curl_setopt($ch, CURLOPT_POST, true);
        if ($data) {
            $json_data = json_encode($data);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $json_data);
            writeDebugLog("POST data: $json_data");
        }
    } elseif ($method === 'PUT') {
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PUT');
        if ($data) {
            $json_data = json_encode($data);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $json_data);
            writeDebugLog("PUT data: $json_data");
        }
    }
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    $info = curl_getinfo($ch);
    curl_close($ch);
    
    writeDebugLog("Response HTTP Code: $httpCode");
    writeDebugLog("Response body: " . substr($response, 0, 500)); // First 500 chars
    
    if ($error) {
        writeDebugLog("cURL Error: $error");
        return ['success' => false, 'message' => 'Verbindingsfout: ' . $error];
    }
    
    // Check if response looks like HTML (error page)
    if (strpos(trim($response), '<!DOCTYPE') === 0 || strpos(trim($response), '<HTML') === 0) {
        writeDebugLog("Received HTML response instead of JSON");
        return ['success' => false, 'message' => 'Backend server retourneerde een foutpagina in plaats van JSON. Controleer of de backend service actief is.'];
    }
    
    // Try to decode JSON
    $decodedResponse = json_decode($response, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        writeDebugLog("JSON decode error: " . json_last_error_msg());
        return ['success' => false, 'message' => 'Ongeldige JSON response van backend'];
    }
    
    $success = $httpCode >= 200 && $httpCode < 300;
    writeDebugLog("Request success: " . ($success ? 'true' : 'false'));
    
    return [
        'success' => $success,
        'message' => $decodedResponse['message'] ?? $decodedResponse['error'] ?? 'Onbekende fout',
        'data' => $decodedResponse,
        'http_code' => $httpCode
    ];
}

// Handle form submissions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['add_user'])) {
        writeDebugLog("Add user request started");
        
        // Validate input data
        $required_fields = ['first_name', 'last_name', 'email', 'username', 'password', 'company_name', 'role'];
        $missing_fields = [];
        
        foreach ($required_fields as $field) {
            if (empty(trim($_POST[$field] ?? ''))) {
                $missing_fields[] = $field;
            }
        }
        
        if (!empty($missing_fields)) {
            echo '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> Ontbrekende velden: ' . implode(', ', $missing_fields) . '</div>';
        } else {
            // Add new user
            $userData = [
                'first_name' => trim($_POST['first_name']),
                'last_name' => trim($_POST['last_name']),
                'email' => trim($_POST['email']),
                'username' => trim($_POST['username']),
                'password' => trim($_POST['password']),
                'company_name' => trim($_POST['company_name']),
                'role' => $_POST['role']
            ];
            
            writeDebugLog("Attempting to add user: " . $userData['username']);
            $response = makeAPIRequest($backend_url . '/users/', 'POST', $userData);
            
            if ($response['success']) {
                echo '<div class="alert alert-success"><i class="fas fa-check-circle"></i> Gebruiker succesvol toegevoegd!</div>';
                writeDebugLog("User added successfully");
            } else {
                echo '<div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle"></i> Fout bij toevoegen: <br>
                        <strong>' . htmlspecialchars($response['message']) . '</strong>
                        <br><small>HTTP Code: ' . ($response['http_code'] ?? 'N/A') . '</small>
                      </div>';
                writeDebugLog("Failed to add user: " . $response['message']);
            }
        }
    }
    
    if (isset($_POST['toggle_user_status'])) {
        writeDebugLog("Toggle user status request started");
        
        // Toggle user active/inactive status
        $username = $_POST['username'];
        $blocked = $_POST['current_blocked'] === 'true' ? 'false' : 'true';
        
        $updateData = ['blocked' => $blocked === 'true'];
        $response = makeAPIRequest($backend_url . '/users/' . urlencode($username), 'PUT', $updateData);
        
        if ($response['success']) {
            $status = $blocked === 'true' ? 'gedeactiveerd' : 'geactiveerd';
            echo '<div class="alert alert-success"><i class="fas fa-check-circle"></i> Gebruiker succesvol ' . $status . '!</div>';
            writeDebugLog("User status changed successfully");
        } else {
            echo '<div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> Fout bij wijzigen status: <br>
                    <strong>' . htmlspecialchars($response['message']) . '</strong>
                  </div>';
            writeDebugLog("Failed to change user status: " . $response['message']);
        }
    }
    
    // Update settings if provided
    if (isset($_POST['update_settings'])) {
        $new_settings = [
            'backend_url' => trim($_POST['backend_url'])
        ];
        
        if (saveSettings($settings_file, $new_settings)) {
            $settings = $new_settings; // Update current settings
            $backend_url = $settings['backend_url']; // Update backend URL
            echo '<div class="alert alert-success"><i class="fas fa-check-circle"></i> Instellingen succesvol opgeslagen!</div>';
            writeDebugLog("Settings updated successfully");
        } else {
            echo '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> Fout bij opslaan instellingen!</div>';
            writeDebugLog("Failed to save settings");
        }
    }
    
    // Test backend connection
    if (isset($_POST['test_connection'])) {
        writeDebugLog("Testing backend connection");
        
        $response = makeAPIRequest($backend_url . '/health', 'GET');
        if (!$response['success']) {
            // Try alternative health check endpoint
            $response = makeAPIRequest($backend_url . '/users/', 'GET');
        }
        
        if ($response['success']) {
            echo '<div class="alert alert-success"><i class="fas fa-check-circle"></i> Verbinding met backend succesvol!</div>';
        } else {
            echo '<div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> Kan geen verbinding maken met backend: <br>
                    <strong>' . htmlspecialchars($response['message']) . '</strong>
                  </div>';
        }
    }
}

// Fetch users from backend - CORRECTE URL
writeDebugLog("Fetching users from backend");
$usersResponse = makeAPIRequest($backend_url . '/users/', 'GET');  // LET OP: één slash
$users = $usersResponse['success'] ? ($usersResponse['data']['users'] ?? []) : [];

if (!$usersResponse['success']) {
    writeDebugLog("Failed to fetch users: " . $usersResponse['message']);
}

?>

<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">

<div class="container-fluid mt-4">
    <div class="row">
        <!-- Settings Panel -->
        <div class="col-lg-12 mb-4">
            <div class="card">
                <div class="card-header bg-warning text-dark">
                    <h5 class="mb-0">
                        <i class="fas fa-cog"></i> Instellingen & Verbinding
                        <button class="btn btn-sm btn-outline-dark float-right" type="button" data-toggle="collapse" data-target="#settingsCollapse">
                            <i class="fas fa-chevron-down"></i> Toon/Verberg
                        </button>
                    </h5>
                </div>
                <div class="collapse" id="settingsCollapse">
                    <div class="card-body">
                        <form method="POST">
                            <div class="row">
                                <div class="col-md-8">
                                    <div class="form-group">
                                        <label for="backend_url"><i class="fas fa-server"></i> Backend URL:</label>
                                        <input type="url" class="form-control" id="backend_url" name="backend_url" 
                                               value="<?= htmlspecialchars($settings['backend_url']) ?>" required>
                                        <small class="form-text text-muted">Bijvoorbeeld: http://localhost:5000/api/v1 of http://172.28.0.15:5000/api/v1</small>
                                    </div>
                                </div>
                                <div class="col-md-4 d-flex align-items-end">
                                    <div class="btn-group w-100" role="group">
                                        <button type="submit" name="update_settings" class="btn btn-warning">
                                            <i class="fas fa-save"></i> Opslaan
                                        </button>
                                        <button type="submit" name="test_connection" class="btn btn-info">
                                            <i class="fas fa-wifi"></i> Test
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                        
                        <div class="mt-2">
                            <small class="text-muted">
                                <i class="fas fa-info-circle"></i> Debug logs: /opt/loxberry/log/plugins/timetrackingplugin/api_debug.log
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Gebruikers beheer -->
        <div class="col-lg-12">
            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0"><i class="fas fa-users"></i> Gebruikers Beheer</h4>
                </div>
                <div class="card-body">
                    <!-- Add User Form -->
                    <div class="card mb-3">
                        <div class="card-header bg-success text-white">
                            <h5 class="mb-0"><i class="fas fa-user-plus"></i> Nieuwe Gebruiker Toevoegen</h5>
                        </div>
                        <div class="card-body">
                            <form method="POST">
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label for="first_name"><i class="fas fa-user"></i> Voornaam:</label>
                                            <input type="text" class="form-control" id="first_name" name="first_name" required>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label for="last_name"><i class="fas fa-user"></i> Achternaam:</label>
                                            <input type="text" class="form-control" id="last_name" name="last_name" required>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label for="username"><i class="fas fa-at"></i> Gebruikersnaam:</label>
                                            <input type="text" class="form-control" id="username" name="username" required>
                                        </div>
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label for="email"><i class="fas fa-envelope"></i> Email:</label>
                                            <input type="email" class="form-control" id="email" name="email" required>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label for="password"><i class="fas fa-lock"></i> Wachtwoord:</label>
                                            <input type="password" class="form-control" id="password" name="password" required>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label for="role"><i class="fas fa-user-tag"></i> Rol:</label>
                                            <select class="form-control" id="role" name="role" required>
                                                <option value="user">Gebruiker</option>
                                                <option value="admin">Administrator</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-md-8">
                                        <div class="form-group">
                                            <label for="company_name"><i class="fas fa-building"></i> Bedrijf:</label>
                                            <input type="text" class="form-control" id="company_name" name="company_name" required>
                                        </div>
                                    </div>
                                    <div class="col-md-4 d-flex align-items-end">
                                        <button type="submit" name="add_user" class="btn btn-success btn-block">
                                            <i class="fas fa-plus"></i> Gebruiker Toevoegen
                                        </button>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>

                    <!-- Users List -->
                    <div class="card">
                        <div class="card-header bg-info text-white">
                            <h5 class="mb-0">
                                <i class="fas fa-list"></i> Bestaande Gebruikers (<?= count($users) ?>)
                                <small class="float-right">Backend: <?= htmlspecialchars($backend_url) ?></small>
                            </h5>
                        </div>
                        <div class="card-body">
                            <?php if (empty($users)): ?>
                                <div class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle"></i> Geen gebruikers gevonden.
                                    <?php if (!$usersResponse['success']): ?>
                                        <br><small><strong>Fout:</strong> <?= htmlspecialchars($usersResponse['message']) ?></small>
                                        <br><small>Controleer de backend URL en zorg dat de service actief is.</small>
                                    <?php endif; ?>
                                </div>
                            <?php else: ?>
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead class="thead-dark">
                                            <tr>
                                                <th><i class="fas fa-user"></i> Naam</th>
                                                <th><i class="fas fa-envelope"></i> Email</th>
                                                <th><i class="fas fa-building"></i> Bedrijf</th>
                                                <th><i class="fas fa-user-tag"></i> Rol</th>
                                                <th><i class="fas fa-info-circle"></i> Status</th>
                                                <th><i class="fas fa-cogs"></i> Actie</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <?php foreach ($users as $user): ?>
                                                <tr>
                                                    <td>
                                                        <strong><?= htmlspecialchars($user['first_name'] . ' ' . $user['last_name']) ?></strong>
                                                        <br><small class="text-muted">@<?= htmlspecialchars($user['username']) ?></small>
                                                    </td>
                                                    <td><?= htmlspecialchars($user['email']) ?></td>
                                                    <td><?= htmlspecialchars($user['company_name'] ?? 'N/A') ?></td>
                                                    <td>
                                                        <span class="badge <?= $user['user_role'] === 'admin' ? 'badge-danger' : 'badge-secondary' ?>">
                                                            <i class="fas <?= $user['user_role'] === 'admin' ? 'fa-crown' : 'fa-user' ?>"></i>
                                                            <?= ucfirst(htmlspecialchars($user['user_role'])) ?>
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <?php if ($user['blocked']): ?>
                                                            <span class="badge badge-danger">
                                                                <i class="fas fa-ban"></i> Geblokkeerd
                                                            </span>
                                                        <?php else: ?>
                                                            <span class="badge badge-success">
                                                                <i class="fas fa-check"></i> Actief
                                                            </span>
                                                        <?php endif; ?>
                                                    </td>
                                                    <td>
                                                        <form method="POST" style="display: inline;">
                                                            <input type="hidden" name="username" value="<?= htmlspecialchars($user['username']) ?>">
                                                            <input type="hidden" name="current_blocked" value="<?= $user['blocked'] ? 'true' : 'false' ?>">
                                                            <button type="submit" name="toggle_user_status" 
                                                                    class="btn btn-sm <?= $user['blocked'] ? 'btn-success' : 'btn-warning' ?>"
                                                                    onclick="return confirm('Weet je zeker dat je de status wilt wijzigen?')">
                                                                <?php if ($user['blocked']): ?>
                                                                    <i class="fas fa-check"></i> Activeren
                                                                <?php else: ?>
                                                                    <i class="fas fa-ban"></i> Blokkeren
                                                                <?php endif; ?>
                                                            </button>
                                                        </form>
                                                    </td>
                                                </tr>
                                            <?php endforeach; ?>
                                        </tbody>
                                    </table>
                                </div>
                            <?php endif; ?>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Bootstrap JS for collapse functionality -->
<script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.2/dist/js/bootstrap.bundle.min.js"></script>

<style>
.card {
    border: none;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.table-responsive {
    border-radius: 0.25rem;
}

.badge {
    font-size: 0.8em;
}

.btn {
    border-radius: 0.25rem;
}

.form-control {
    border-radius: 0.25rem;
}
</style>

<?php  
LBWeb::lbfooter();
?>
