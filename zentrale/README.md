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

Die Dokumentation der Funktionen sowie der JSON-Kommands findet sich unter [Steuerung](steuerung.md).
Die REST-API ist unter [REST-API](restapi.md) beschrieben.

## TODO
- REST-API für Garagentor erstellen
- MQTT für Garagentor entfernen
- Abfrage für Mischertemperaturen
- Heizkurve für Mischer setzen
- BME280 einbinden
- Temperaturen über MQTT erhalten
- Setzen von Timerregeln
- Schreiben in Timerfiles
- MQTT-Publish Pumpenstatus
- MQTT-Publish bei Veränderung der restlichen Werte
- Abfrage Umwälzpumpe über MQTT
- Abfrage Aussentemperatur über MQTT 
- MQTT-Publish der Zählerwerte

