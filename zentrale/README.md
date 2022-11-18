# Heizungssteuerung

Software zur Steuerung von Heizungsventilen, mittlerweile erweitert um die Steuerung und Überwachung eines Garagentors. Weiterhin auch nützlich für eine automatische Gartenbewässerung. Die Software ist für Raspberry Pi Zero geschrieben.

## Funktionen
- Ansteuerung von Ventilen über Relais, Anzahl prinzipiell nur die die Anzahl der Ausgänge begrenzt
- Zeitsteuerung über Timerfile
- Jeder Zimmer kann aus einem oder mehreren Heizkreisen bestehen
- Status eine zentralen Umwälzpumpe kann abgefragt werden, um die Regelung zu aktivieren bzw. deaktivieren
- Temperaturregelung über einfachen Zweipunktregler
- Aussentemperaturgeführte Vorlauftemperaturregelung (bei vorhandenem Stellventil, Ansteuerung über DRV8830 I2C Motorsteuerung)
- Kurzzeittimer (on/off), hilfreich zum Lüften
- Auslesung von MBus-Wärmemengenzählern
- JSON-API über UDP-Server
- Temperaturmessungen über MQTT
- Messung von Vorlauf-/Rücklauftemperatur
- REST-API

Zusatz:
- Auslesen eines Garagentormelderkontakts
- Ansteuerung (auf/zu) eines Garagentors


## JSON-API

### getStatus
Returns status of system including set temperature, actual temperature and on/off per room

### getAlive
Check, if system is alive, returns {"answer":"Freilich"}

### getRooms

### getRoomStatus

### setRoomStatus

### getTimer

### setTimer
 
## REST-API
