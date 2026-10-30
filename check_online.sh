#!/bin/bash

# --- KONFIGURATION ---
SERVER_IP="dose.plattentoni.de" 
# ---------------------

FEHLSCHLAEGE=0

for i in {1..3}; do
    # Ping sendet 1 Paket mit einem Timeout von 2 Sekunden
    if ping -c 1 -W 2 "$SERVER_IP" > /dev/null 2>&1; then
        # Verbindung erfolgreich -> Skript beenden
        logger -t check_online "All good, we're in the game"
        exit 0
    else
        # Verbindung fehlgeschlagen -> Zähler erhöhen
        FEHLSCHLAEGE=$((FEHLSCHLAEGE + 1))
        
        # Wenn es noch nicht der letzte Versuch war, 5 Sekunden warten
        if [ $FEHLSCHLAEGE -lt 3 ]; then
            sleep 5
        fi
    fi
done

# Wenn 3 Fehlschläge erreicht wurden, Reboot auslösen
if [ $FEHLSCHLAEGE -eq 3 ]; then
    echo "Server $SERVER_IP nicht erreichbar. Starte System neu..."
    logger -t check_online "Oh oh, can't call home. Rebooting."
    /usr/sbin/reboot
fi
