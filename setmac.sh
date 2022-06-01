#!/bin/bash

raspberry="B8:27:EB:" # Die ersten drei Bytes der MAC-Adresse sind statisch
# Die letzten drei Bytes werden aus der CPU-ID generiert:
cpuid=$(cat /proc/cpuinfo | grep Serial | cut -c 21-26 | sed 's/\(..\)/\1:/g')

mac=$raspberry$cpuid #Zusammensetzen der beiden Teile
mac=${mac%?} #Letztes Zeichen (:) wieder entfernen

#MAC-Adresse setzen
/sbin/ip link set dev eth0 address $mac
/sbin/ip link set dev eth0 up


