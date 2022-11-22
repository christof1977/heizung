# Heizungssteuerung

Software zur Steuerung von Heizungsventilen, mittlerweile erweitert um die Steuerung und Überwachung eines Garagentors. Weiterhin auch nützlich für eine automatische Gartenbewässerung. Die Software ist für Raspberry Pi Zero geschrieben.

## Funktionen
- Ansteuerung von Ventilen über Relais, Anzahl prinzipiell nur die die Anzahl der Ausgänge begrenzt
- Zeitsteuerung über Timerfile
- Jedes Zimmer kann aus einem oder mehreren Heizkreisen bestehen
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

### get_status()
Returns status of system including set temperature, actual temperature and on/off per room

### get_alive()
Check, if system is alive, returns {"answer":"Freilich"}

### get_rooms()

### get_room_timer()

### set_room_timer()

### reload_timer()

### get_timer()

### get_room_status()

### set_room_status()

### get_room_mode()

### set_room_mode()

### toggle_room_mode()

### get_room_shorttimer()

### set_room_shorttimer()

### reset_room_shorttimer()

### get_room_temp()

### get_room_norm_temp()

### set_room_norm_temp()

### get_counter_values()

### get_counter()

### set_tor()

### get_tor()
 
## REST-API
