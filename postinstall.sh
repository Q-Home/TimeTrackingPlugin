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

sudo /opt/loxberry/bin/plugins/timetrackingplugin/run_docker_compose.sh

# Wait until InfluxDB is ready (max 60 seconds)
echo "Waiting for InfluxDB to become available..."
for i in {1..60}; do
  if docker exec influxdb curl -s http://localhost:8086/health | grep -q '"status":"pass"'; then
    echo "InfluxDB is ready."
    break
  fi
  sleep 1
done

# Clean up install scripts
rm /opt/loxberry/bin/plugins/timetrackingplugin/run_docker_compose.sh

pip install pymongo paho-mqtt