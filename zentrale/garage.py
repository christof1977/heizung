#!/usr/bin/env python3

import RPi.GPIO as GPIO
import logging
import paho.mqtt.client as mqtt
import json
import time

#logger = logging.getLogger(__name__)
logger = logging.getLogger("Garage")
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)

class Garage():
    def __init__(self, kontakt=None, melder=None, mqtthost=None, mqttuser=None, mqttpass=None):
        if(kontakt < 1 or  melder < 1):
           raise RuntimeError("No valid pins are defined")
        self.mqtthost = mqtthost
        self.mqttpass = mqttpass
        self.mqttuser = mqttuser
        self.garagenkontakt = kontakt
        self.garagenmelder = melder
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.garagenkontakt, GPIO.OUT)
        GPIO.output(self.garagenkontakt, 0)
        logger.info("Setting Garagenkontakt: %s", str(self.garagenkontakt))
        GPIO.setup(self.garagenmelder, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logger.info("Setting Garagenmelder: %s", str(self.garagenmelder))
        GPIO.add_event_detect(self.garagenmelder, GPIO.BOTH, callback = self.garagenmeldung, bouncetime = 250)

        self.mqttclient = mqtt.Client("Garage")
        self.mqttclient.username_pw_set(self.mqttuser, self.mqttpass)
        self.mqttclient.on_message = self.on_mqtt_message
        self.mqttclient.on_connect = self.on_mqtt_connect
        #logger.info("Setting Last Will and Testament")
        #self.mqttclient.will_set(self.name + "/" + self.hostname + "/LWT", "Offline", retain=True)
        self.mqttclient.connect(self.mqtthost, 1883, 60)
        #logger.info("Sending LWT Online Message")
        self.mqttclient.loop_start()
        self.garagentor = ""
        self.garagenmeldung(self.garagenmelder)

    def __del__(self):
        try:
            self.mqttclient.loop_stop()
            self.mqttclient.disconnect()
        except:
            pass

    def on_mqtt_connect(self, client, userdata, flags, rc):
        client.subscribe("Garage/Tor/Kommando")

    def on_mqtt_message(self, client, userdata, msg):
        # Move garage door if topic is Garage/Tor/Kommando
        payload = msg.payload.decode('UTF-8')
        if(msg.topic == "Garage/Tor/Kommando"):
            if(payload == "auf"):
                self.set_tor("auf")
                logger.info("Tor auf")
            else:
                self.set_tor("zu")
                logger.info("Tor zu")

    def garagenmeldung(self, channel):
        logger.debug("GARAGENMELDA: %s", str(self.garagenmelder))
        logger.debug("Channel: %s", str(channel))
        if(channel == self.garagenmelder and channel > 0):
            status = GPIO.input(channel)
        else:
            return -1
        try:
            if(status == 0):
                if(self.garagentor == "auf"):
                    logger.debug("Same state, not publishing")
                else:
                    self.garagentor = "auf"
                    self.mqttclient.publish("Garage/Tor/Zustand", self.garagentor, retain=True)
            else:
                if(self.garagentor == "zu"):
                    logger.debug("Same state, not publishing")
                else:
                    self.garagentor = "zu"
                    self.mqttclient.publish("Garage/Tor/Zustand", self.garagentor, retain=True)
        except Exception as e:
            logger.error(e)

    def _get_tor(self):
        if(self.garagenmelder != -1):
            status = GPIO.input(self.garagenmelder)
            if(status == 1):
                return("zu")
            else:
                return("auf")
        else:
            return("Error")

    def get_tor(self):
        """ This function returns the state of the garage door if available. The return format is a JSON-String.  
        The function can be called via JSON-Command-String: ```'{"command" : "getTor"}'```
        
        ```python
        open: '{"Answer":"getTor","Result":"auf"}'
        closed: '{"Answer":"getTor","Result":"zu"}'
        error: '{"Answer":"getTor","Result":"Error","Value":"Tor? Welches Tor?"}'
        ```

        """
        ret = self._get_tor()
        if(ret == "Error"):
            ret = json.dumps({"Answer":"getTor","Result":"Error","Value":"Tor? Welches Tor?"})
        else:
            ret = json.dumps({"Answer":"getTor","Result":ret})
        return(ret)

    def set_tor(self, val):
        """ This function triggers the switch of the Garagentor. When it's open, it closes and vice versa.
        The return of the function is either a success or a error message.
        
        Control commands look as follows:
        ```python
        open: '{"command" : "setTor" , "Request":"auf"}'
        closed: '{"command" : "setTor" , "Request":"zu"}'
        ```
        
        Answer:
        ```python
        Success: '{"Answer":"setTor","Request":"xxx","Result":"Success"}'
        Error: '{"Answer":"setTor","Request":"xxx","Result":"Error"})'
        No door in system: '{"Answer":"setTor","Request":"xxx","Result":"Error","Value":"Tor? Welches Tor?"}'
        Door already in requested state: '{"Answer":"setTor","Request":"xxx","Result":"Tor ist doch schon xxx, Doldi."}'
        ```
        """
        if self.garagenkontakt > 0:
            if(val ==  self._get_tor()):
                logger.info("Gargentor ist doch schon "+ val + ". Fuesse stillhalten")
                ret = json.dumps({"Answer":"setTor","Request":val,"Result":"Tor ist doch schon " + val + ", Doldi."})
            else:
                try:
                    logger.info("Moving Garagentor")
                    GPIO.output(self.garagenkontakt, 1)
                    time.sleep(.2)
                    GPIO.output(self.garagenkontakt, 0)
                    ret = json.dumps({"Answer":"setTor","Request":val,"Result":"Success"})
                except:
                    ret = json.dumps({"Answer":"setTor","Request":val,"Result":"Error"})
        else:
            ret = json.dumps({"Answer":"setTor","Request":val,"Result":"Error","Value":"Tor? Welches Tor?"})
        return(ret)


if __name__ == "__main__":
    garage = Garage(kontakt=10, melder=24, mqtthost="mqtt.plattentoni.de", mqttuser="raspi", mqttpass="parsi")
    while True:
        time.sleep(1)
        garage.garagenmeldung(24)
