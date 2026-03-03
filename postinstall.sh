#!/bin/bash
# To use important variables from command line use the following code:
COMMAND=$0    # Zero argument is shell command
PTEMPDIR=$1   # First argument is temp folder during install
PSHNAME=$2    # Second argument is Plugin-Name for scipts etc.
PDIR=$3       # Third argument is Plugin installation folder
PVERSION=$4   # Forth argument is Plugin version
#LBHOMEDIR=$5 # Comes from /etc/environment now. Fifth argument is
# Base folder of LoxBerry
PTEMPPATH=$6  # Sixth argument is full temp path during install (see also $1)

# Combine them with /etc/environment
PHTMLAUTH=$LBHOMEDIR/webfrontend/htmlauth/plugins/$PDIR
PHTML=$LBPHTML/$PDIR
PTEMPL=$LBPTEMPL/$PDIR
PDATA=$LBPDATA/$PDIR
PLOGS=$LBPLOG/$PDIR # Note! This is stored on a Ramdisk now!
PCONFIG=$LBPCONFIG/$PDIR
PSBIN=$LBPSBIN/$PDIR

sudo apt-get update
# sudo apt-get install -y php-mongodb
# sudo systemctl restart apache2

# Docker permission setup
echo "Checking Docker permissions..."

# Check if docker group exists
if ! getent group docker > /dev/null; then
    echo "Docker group not found. Creating docker group..."
    sudo groupadd docker
fi

# Check if current user is in docker group
if id -nG "$USER" | grep -qw docker; then
    echo "User $USER is already in docker group. Skipping."
else
    echo "Adding user $USER to docker group..."
    sudo usermod -aG docker "$USER"
    echo "User added to docker group. Please log out and log back in for changes to take effect."
    echo "Or run: newgrp docker"
fi

# Ensure docker daemon is running
echo "Checking Docker daemon status..."
if ! sudo systemctl is-active --quiet docker; then
    echo "Starting Docker daemon..."
    sudo systemctl start docker
else
    echo "Docker daemon is already running."
fi

# Test Docker socket permissions
if [ -S /var/run/docker.sock ]; then
    if [ -w /var/run/docker.sock ]; then
        echo "Docker socket is accessible."
    else
        echo "Warning: Docker socket exists but is not writable. You may need elevated permissions."
    fi
else
    echo "Warning: Docker socket not found at /var/run/docker.sock"
fi

echo "Docker setup check complete."

# Log files setup
echo "Setting up log files..."
LOGDIR="/opt/loxberry/log/plugins/timetrackingplugin"
MQTT_LOG="$LOGDIR/timetracking_mqtt.log"
APP_LOG="$LOGDIR/app.log"

# Create log directory if it doesn't exist
if [ ! -d "$LOGDIR" ]; then
    echo "Creating log directory: $LOGDIR"
    sudo mkdir -p "$LOGDIR"
else
    echo "Log directory already exists: $LOGDIR"
fi

# Create and initialize MQTT log file
if [ ! -f "$MQTT_LOG" ]; then
    echo "Creating MQTT log file: $MQTT_LOG"
    sudo touch "$MQTT_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log file not found: $MQTT_LOG - Creating new log file" | sudo tee "$MQTT_LOG" > /dev/null
else
    echo "MQTT log file already exists: $MQTT_LOG"
fi

# Create and initialize app log file
if [ ! -f "$APP_LOG" ]; then
    echo "Creating app log file: $APP_LOG"
    sudo touch "$APP_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log file not found: $APP_LOG - Creating new log file" | sudo tee "$APP_LOG" > /dev/null
else
    echo "App log file already exists: $APP_LOG"
fi

# Set proper permissions for log files
sudo chmod 666 "$MQTT_LOG" 2>/dev/null || true
sudo chmod 666 "$APP_LOG" 2>/dev/null || true

echo "Log files setup complete."

# sudo /opt/loxberry/bin/plugins/timetrackingplugin/run_docker_compose.sh

exit 0;