#!/bin/bash

# --- Constants ---
REPO_DIR="/opt/loxberry/bin/plugins/consumption_prediction"

# --- Check for root if needed ---
if ! docker info &> /dev/null; then
  echo "Docker permission check failed."

  # Check if running as root
  if [ "$EUID" -ne 0 ]; then
    echo "Re-running script with sudo..."
    exec sudo bash "$0" "$@"
  fi

  # Install Docker if not present
  if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
  else
    echo "Docker is already installed."
  fi


echo "Adding loxberry to docker group..."
usermod -aG docker "loxberry"
echo "User loxberry added to docker group."
echo "A reboot is required for group changes to apply."
fi

# --- Check for Docker Compose plugin ---
if ! docker compose version &> /dev/null; then
  echo "Installing Docker Compose plugin..."
  sudo mkdir -p /usr/lib/docker/cli-plugins
  sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
    -o /usr/lib/docker/cli-plugins/docker-compose
  sudo chmod +x /usr/lib/docker/cli-plugins/docker-compose
else
  echo "Docker Compose is already available."
fi

# --- Start Docker Compose ---
cd "$REPO_DIR" || exit 1
echo "Starting Docker Compose services..."
docker compose up -d --build