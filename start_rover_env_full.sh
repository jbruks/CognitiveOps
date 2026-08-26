#!/bin/bash

echo "================================="
echo "LUNAR ROVER DEVELOPMENT ENV"
echo "FULL STARTUP"
echo "================================="

# Cargar entorno
source ~/.profile

# Ir al repo
cd ~/dev/ardupilot || exit 1

echo "Abriendo SITL + MAVProxy..."

gnome-terminal -- bash -c '
source ~/.profile
cd ~/dev/ardupilot
sim_vehicle.py -v Rover --cmd="module load map; module load console; output add 127.0.0.1:14550; output add 127.0.0.1:14551"
exec bash
'

# Dar tiempo a que SITL arranque
sleep 10

echo "Abriendo QGroundControl..."

gnome-terminal -- bash -c '
cd ~
./QGroundControl.AppImage
exec bash
'

echo "================================="
echo "Entorno arrancado"
echo "================================="
echo "MAVProxy outputs esperados:"
echo "  14550 -> QGroundControl"
echo "  14551 -> Python scripts"
echo "================================="
