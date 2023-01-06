#!/usr/bin/env python3
import socket
import os
import RPi.GPIO as GPIO
import sys
import time
import datetime
import configparser
import json
from timer import timer
from mixer import mixer
import syslog
from libby import tempsensors
from libby import remote
from libby import mbus
import threading
from threading import Thread
import logging
import select
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import prctl

from flask import Flask
from flask import request
from flask_restful import Api
from flask_restful import Resource, abort

# TODO
# - MQTT Retain
# - MQTT LWT
# - REST-Interface Garage
# - Publish ventil status
# - Publish pump status
# - Publish change of other values

udp_port = 5005
server = "dose"
datacenterport = 6663
udpBcPort =  6664
logger = logging.getLogger('Heizung')
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)


class udpBroadcast():
    def __init__(self):
        self.udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.udpSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT,1)
        self.udpSock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST, 1)
        self.udpSock.settimeout(0.1)
        logger.info("UDP Broadcast socket created")

    def send(self, message):
        try:
            logger.debug(json.dumps(message))
            self.udpSock.sendto(json.dumps(message).encode(),("<broadcast>",udpBcPort))
        except:
            logger.error("Something went wrong while sending UDP broadcast message")

#class steuerung(threading.Thread):
class steuerung(Resource):
    def __init__(self):
        #threading.Thread.__init__(self)
        #logger.info("Starting Steuerungthread as " + threading.currentThread().getName())
        self.t_stop = threading.Event()
        self.read_config()
        self.system = {"ModeReset":"2:00"}
        
        self.set_hw()
        if(self.mixer_addr != -1):
            #self.mix = mixer(addr=self.mixer_addr)
            self.mix = mixer()
            self.mix.run()
        
        self.w1 = tempsensors.onewires()
        self.w1_slaves = self.w1.enumerate()
        self.Timer = timer(self.timerfile)
        
        #Starting Threads
        self.set_pumpe()
        self.short_timer()
        self.timer_operation()

        self.udpServer()
        self.udp = udpBroadcast()

        self.broadcast_value()
        self.udpRx()

        self.mqtttopics = {}
        if(self.garagenkontakt != -1):
                self.mqtttopics["Garage"] = "Garage/Tor/Kommando"
        for sensor in self.sensorik:
            logger.info("Sensor " + sensor + ": " + str(self.sensorik[sensor]))
            try:
                if(self.sensorik[sensor]["System"] == "MQTT"):
                    self.mqtttopics[sensor] = self.sensorik[sensor]["ID"]
            except:
                logger.warning("Config error, key 'System' missing.")
        if self.mqtttopics:
            self.mqttclient = mqtt.Client(self.hostname+str(datetime.datetime.now().timestamp()))
            self.mqttclient.on_connect = self.on_mqtt_connect
            self.mqttclient.on_message = self.on_mqtt_message
            # Then, connect to the broker.
            self.mqttclient.username_pw_set(self.mqttuser, self.mqttpass)
            self.mqttclient.connect(self.mqtthost, 1883, 60)
            # Finally, process messages until a `client.disconnect()` is called.
            self.mqttclient.loop_start()
        if(self.garagenkontakt != -1):
                self.garagenmeldung(self.garagenmelder)
        self.run()

    # The callback for when the client connects to the broker.
    def on_mqtt_connect(self, client, userdata, flags, rc):
        # After establishing a connection, subscribe to the input topic.
        for topic in self.mqtttopics:
            #logger.info("Subscribing to " + self.mqtttopics[topic])
            client.subscribe(self.mqtttopics[topic])

    # The callback for when a message is received from the broker.
    def on_mqtt_message(self, client, userdata, msg):
        # Decode the message payload from Bytes to String.
        payload = msg.payload.decode('UTF-8')
        if(msg.topic == "Garage/Tor/Kommando"):
            if(payload == "auf"):
                self.set_tor("auf")
            else:
                self.set_tor("zu")
        for sensor in self.sensorik:
            if msg.topic in self.sensorik.get(sensor).values():
                try:
                    payload = json.loads(payload)
                    for key in payload.keys():
                        try:
                            self.clients[sensor]["isTemp"] = payload[key]["Temperature"]
                        except:
                            pass
                except:
                    logger.warning("Not a JSON string")

    def udpRx(self):
         self.udpRxTstop = threading.Event()
         rxValT = threading.Thread(target=self._udpRx)
         rxValT.setDaemon(True)
         rxValT.start()

    def _udpRx(self):
         prctl.set_name("udpRx")
         port =  6664
         print("Starting UDP client on port ", port)
         udpclient = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP
         udpclient.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
         udpclient.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
         udpclient.bind(("", port))
         udpclient.setblocking(0)
         while(not self.udpRxTstop.is_set()):
             ready = select.select([udpclient], [], [], .1)
             if ready[0]:
                 data, addr = udpclient.recvfrom(8192)
                 try:
                     message = json.loads(data.decode())
                     if("measurement" in message.keys()):
                         meas = message["measurement"]
                         if("tempOekoAussen" in meas.keys()):
                             try:
                                 self.mix.ff_temp_target = float(meas["tempOekoAussen"]["Value"])
                             except:
                                 logger.debug("tempOekoAussen not valid or so")
                 except Exception as e:
                     logger.warning(str(e))

    def udpServer(self):
        logger.info("Starting UDP-Server at " + self.basehost + ":" + str(udp_port))
        self.udpSock = socket.socket( socket.AF_INET,  socket.SOCK_DGRAM )
        self.udpSock.bind( (self.basehost,udp_port) )

        udpT = threading.Thread(target=self._udpServer)
        udpT.setDaemon(True)
        udpT.start()

    def _udpServer(self):
        prctl.set_name("udpServer")
        logger.info("Server laaft")
        while(not self.t_stop.is_set()):
            try:
                data, addr = self.udpSock.recvfrom( 1024 )# Puffer-Groesse ist 1024 Bytes.
                #logger.debug("Kimm ja scho")
                ret = self.parseCmd(data) # Abfrage der Fernbedienung (UDP-Server), der Rest passiert per Interrupt/Event
                self.udpSock.sendto(str(ret).encode('utf-8'), addr)
            except Exception as e:
                try:
                    self.udpSock.sendto(str('{"answer":"error"}').encode('utf-8'), addr)
                    logger.warning("Uiui, beim UDP senden/empfangen hat's kracht!" + str(e))
                except Exception as o:
                    logger.warning("Uiui, beim UDP senden/empfangen hat's richtig kracht!" + str(o))

    def get_oekofen_pumpe(self):
        """ Get status from Oekofen heating pump
        Retries, if no response

        """
        if(self.oekofen == 0):
            # Do not get state of heating system, just return true to simulate a running heating pump
            logger.debug("Not taking Oekofen state into account")
            ret = True
        else:
            ret = -1
            while(ret == -1):
                try:
                    json_string = '{"command" : "getUmwaelzpumpe"}'
                    ret = remote.udpRemote(json_string, addr=server, port=datacenterport)["answer"]
                except:
                    ret = -1
                    time.sleep(1)
            if(ret in ["true", "True", "TRUE"]):
                ret = True
            else:
                ret = False
        return(ret)

    def parseCmd(self, data):
        data = data.decode()
        try:
            jcmd = json.loads(data)
            logger.debug(data)
        except:
            logger.warning("Das ist mal kein JSON, pff!")
            ret = json.dumps({"answer": "Kaa JSON Dings!"})
            return(ret)
        if(jcmd['command'] == "getStatus"):
            ret = self.get_status()
        elif(jcmd['command'] == "getAlive"):
            ret = self.get_alive()
        elif(jcmd['command'] == "getRooms"):
            ret = self.get_rooms()
        elif(jcmd['command'] == "getRoomTimer"):
            ret = self.get_room_timer(jcmd['Room'])
        elif(jcmd['command'] == "setRoomTimer"):
            ret = self.set_room_timer(jcmd['Room'])
        elif(jcmd['command'] == "reloadTimer"):
            ret = self.reload_timer()
        elif(jcmd['command'] == "getTimer"):
            ret = self.get_timer()
        elif(jcmd['command'] == "getRoomStatus"):
            ret = self.get_room_status(jcmd['Room'])
        elif(jcmd['command'] == "setRoomStatus"):
            ret = self.set_room_status(jcmd['Room'])
        elif(jcmd['command'] == "getRoomMode"):
            ret = self.get_room_mode(jcmd['Room'])
        elif(jcmd['command'] == "setRoomMode"):
            ret = self.set_room_mode(jcmd['Room'],jcmd['Mode'])
        elif(jcmd['command'] == "toggleRoomMode"):
            ret = self.toggle_room_mode(jcmd['Room'])
        elif(jcmd['command'] == "getRoomShortTimer"):
            ret = self.get_room_shorttimer(jcmd['Room'])
        elif(jcmd['command'] == "setRoomShortTimer"):
            ret = self.set_room_shorttimer(jcmd['Room'],jcmd['Time'],jcmd['Mode'])
        elif(jcmd['command'] == "resetRoomShortTimer"):
            ret = self.reset_room_shorttimer(jcmd['Room'])
        elif(jcmd['command'] == "getRoomTemp"):
            ret = self.get_room_temp(jcmd['Room'])
        elif(jcmd['command'] == "getRoomSetTemp"):
            ret = self.get_room_set_temp(jcmd['Room'])
        elif(jcmd['command'] == "setRoomSetTemp"):
            ret = self.set_room_set_temp(jcmd['Room'],jcmd['setTemp'])
        elif(jcmd['command'] == "getCounterValues"):
            ret = self.get_counter_values(jcmd['Counter'])
        elif(jcmd['command'] == "getCounter"):
            ret = self.get_counter()
        elif(jcmd['command'] == "setTor"):
            ret = self.set_tor(jcmd['Request'])
        elif(jcmd['command'] == "getTor"):
            ret = self.get_tor()
        else:
             ret = json.dumps({"answer":"Fehler","Wert":"Kein gültiges Kommando"})
        return(ret)

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

    def get_rooms(self):
        """ Return available rooms
        
        Command:
        ```python
        '{"command" : "getRooms"}'
        ```
        
        Answer:
        ```python
        '{"answer":"getRooms","available_rooms":["Z1", "Z2"]}'
        ```

        """
        keys = self.clients.keys()
        ret = json.dumps({"answer":"getRooms","available_rooms":list(self.clients.keys())})
        return(ret)

    def get_room_status(self, room):
        """ Returns status of a single room
        
        Command:
        ```python
        '{"command" : "getRoomStatus", "Room" : "LivingRoom"}'
        ```
        
        Answer:
        ```python
        {
        "answer": "getRoomStatus",
        "room": "LivingRoom",
        "status": {
            "Relais": [
                18,
                10
            ],
            "Status": "on",
            "Mode": "auto",
            "setMode": "auto",
            "setTemp": 21.5,
            "isTemp": 18,
            "Shorttimer": 0,
            "ShorttimerMode": "off",
            "Timer": "on",
            "Name": "Wohnzimmer"
            }
        }
        ```
        
        Answer in case of error:
        ```python
        '{"answer":"room does not exist"}'
        ```

        """
        try:
            logger.debug(self.clients[room])
            ret = json.dumps({"answer":"getRoomStatus","room":room,"status":self.clients[room]})
        except:
            ret = json.dumps({"answer":"room does not exist"})
        return(ret)

    def set_room_status(self, room):
        """ function to set status status of a single room
        
        not implemented yet, is it needed at all?

        """
        #TODO
        return()

    def get_room_timer(self, room):
        """ Returns a room's timer settings
        
        Command: 
        ```python
        '{"command" : "getRoomTimer", "Room" : "LivingRoom"}'
        ```
        
        Answer: 
        ```python
        {"0": [["5:15", "22:00"], ["on", "off"]], "3": [["5:15", "22:00"], ["on", "off"]], "4": [["5:15", "22:00"], ["on", "off"]], "1": [["6:30", "22:00"], ["on", "off"]], "2": [["6:30", "22:00"], ["on", "off"]], "5": [["8:00", "22:00"], ["on", "off"]], "6": [["8:00", "22:00"], ["on", "off"]]}
        ```

        """
        ret = json.dumps(self.Timer.get_timer_list(room))
        return(ret)

    def set_room_timer(self, room):
        """ Sets a room's timer
        
        Not implemented yet.

        Command:
        ```python
        '{"command" : "setRoomTimer", "Room" : "LivingRoom"}'
        ```

        """
        #TODO
        return(json.dumps({"answer":"setRoomTimer", "error": "Not implemented yet"}))

    def reload_timer(self):
        """ This function reloads the timer file, no arguments required.

        Command:
        ```python
        '{"command" : "reloadTimer"}'
        ```

        Answer:
        ```python
        '{"answer":"Timer file reloaded"}'
        ```

        """
        self.Timer = timer(self.timerfile)
        return(json.dumps({"answer":"Timer file reloaded"}))

    def get_timer(self):
        """ This function returns the timer file as json string

        Command:
        ```python
        '{"command" : "getTimer"}'
        ```

        """
        return(json.dumps({"answer":"getTimer", "timerfile": self.Timer.get_all_timer_list()}))

    def get_alive(self):
        """ function to see, if we are alive

        Command:
        ```python
        '{"command" : "getAlive"}'
        ```

        Answer:
        ```python
        '{"name":"hostname","answer":"Freilich", "time":"01:01:01"}'
        ```

        """
        dt = datetime.datetime.now()
        dts = "{:02d}:{:02d}:{:02d}".format(dt.hour, dt.minute, dt.second)
        return(json.dumps({"name":self.hostname,"answer":"Freilich", "time" : dts}))


    def get_status(self):
        """ function to determine status of system

        Command:
        ```python
        '{"command" : "getStatus"}'
        ```

        Answer:
        ```python
        '{
        "WZ": {
            "Relais": [
                18,
                10
            ],
            "Status": "off",
            "Mode": "auto",
            "setMode": "auto",
            "setWindow": "auto",
            "setTemp": 21,
            "isTemp": 18,
            "Shorttimer": 0,
            "ShorttimerMode": "off",
            "Timer": "off",
            "Name": "Wohnzimmer"
        },
        "SZ": {
            "Relais": [
                27
            ],
            "Status": "off",
            "Mode": "auto",
            "setMode": "auto",
            "setWindow": "auto",
            "setTemp": 21,
            "isTemp": 18,
            "Shorttimer": 0,
            "ShorttimerMode": "off",
            "Timer": "off",
            "Name": "Schlafzimmer"
        }'
        ```
        """
        return(json.dumps(self.clients))

    def get_room_mode(self, room):
        """ Returning mode of room

        Command:
        ```python
        '{"command" : "getRoomMode", "room" : "WZ"}'
        ```

        Answer:
        '{
            "answer": "getRoomMode",
            "room": "WZ",
            "mode": "auto"
        }'

        """
        return(json.dumps({"answer":"getRoomMode","room":room,"mode":self.clients[room]["Mode"]}))

    def set_room_mode(self, room, mode):
        """ Setting mode of room

        Set the room to one of the following modes:
        - on:           on
        - off:          off
        - auto:         timer mode
        - window_open:  off, previous mode is stored
        - window_close: restore to mode before window_open

        Command:
        ```python
        '{"command" : "setRoomMode", "room" : "WZ", "mode" : "on/off/auto/window_open/window_close"}'
        ```

        Answer:
        '{
            "answer": "setRoomMode",
            "room": "WZ",
            "mode": "auto"
        }'

        """
        if mode in ["on", "off", "auto"]:
            self.clients[room]["setMode"] = mode
            ret = {"answer":"setRoomMode","room":room,"mode":self.clients[room]["setMode"]}
        elif mode == "window_open":
            self.clients[room]["windowMode"] = self.clients[room]["setMode"]
            self.clients[room]["setMode"] = "off"
            ret = {"answer":"setRoomMode","room":room,"mode":self.clients[room]["setMode"]}
        elif mode == "window_close":
            self.clients[room]["setMode"] = self.clients[room]["windowMode"]
            ret = {"answer":"setRoomMode","room":room,"mode":self.clients[room]["setMode"]}
        else:
            ret = {"answer":"setRoomMode","error":"setMode"}
        logger.info(ret)
        return(json.dumps(ret))

    def toggle_room_mode(self, room):
        """ Setting mode of room to the next one (off -> on -> auto -> off -> ...)

        Command:
        ```python
        '{"command" : "toggleRoomMode", "room" : "WZ"}'
        ```

        Answer:
        '{"answer": "toggleRoomMode", "room": "AZ", "mode": "auto"}'

        """
        if(self.clients[room]["setMode"] == "off"):
            mode = "on"
        elif(self.clients[room]["setMode"] == "on"):
            mode = "auto"
        elif(self.clients[room]["setMode"] == "auto"):
            mode = "off"
        else:
            mode = "auto"
        ret = json.loads(self.set_room_mode(room, mode))
        ret["answer"] = "toggleRoomMode"
        return(json.dumps(ret))

    def get_room_shorttimer(self, room):
        """ Returns value of room's shorttimer to override mode settings for a defined time in seconds

        Command:
        ```python
        '{"command" : "getRoomShortTime", "room" : "WZ"}'
        ```

        Answer:
        '{  "answer": "getRoomShortTimer",
            "ShortTimer": 0,
            "Status": "off",
            "ShorttimerMode": "off"}'

        """
        return(json.dumps({"answer":"getRoomShortTimer", "ShortTimer": self.clients[room]["Shorttimer"], "Status":self.clients[room]["Status"], "ShorttimerMode":self.clients[room]["ShorttimerMode"]}))

    def set_room_shorttimer(self, room, time, mode):
        """ Sets value of room's shorttimer, sets mode accordingly
        After setting, set_status is called to apply change immediately

        Command:
        ```python
        '{"command" : "setRoomShortTimer",
          "Room" : "WZ",
          "Mode": "on"
          "Time" : "60" }'
        ```

        Answer:
        { "answer": "getRoomShortTimer",
          "ShortTimer": 60,
          "Status": "on",
          "ShorttimerMode": "run"}

        Answer in error case:
        '{"answer":"setRoomShortTimer","error":"Unexpected error"}'

        """
        try:
            time = int(time)
        except:
            return('{"answer":"setRoomShortTimer","error":"time must be an integer"}')
        if mode not in ["on", "off"]:
            return('{"answer":"setRoomShortTimer","error":"mode must be on or off"}')
        else:
            try:
                self.clients[room]["Shorttimer"] = time + self.clients[room]["Shorttimer"]
                self.clients[room]["ShorttimerMode"] = "run"
                self.clients[room]["Mode"] = mode
                logger.info("Setting shorttimer for room %s to %ds: %s", room, time, mode)
                self.set_status()
                ret = json.loads(self.get_room_shorttimer(room))
                ret["answer"] = "setRoomShortTimer"
                return json.dumps(ret)
            except:
                return '{"answer":"setRoomShortTimer","error":"Unexpected error"}'

    def reset_room_shorttimer(self, room):
        """ Reets value of room's shorttimer, sets mode accordingly
        After setting, set_status is called to apply change immediately

        """
        try:
            old_mode = self.clients[room]["ShorttimerMode"]
            self.clients[room]["Shorttimer"] = 0
            self.clients[room]["ShorttimerMode"] = "off"
            self.clients[room]["Mode"] = self.clients[room]["setMode"]
            if(old_mode == "run"):
                logger.info("Resetting shorttimer for room %s, new mode: %s", room, self.clients[room]["Mode"])
            self.set_status()
            return(json.dumps(self.clients[room]["Shorttimer"]))
        except:
            return('{"answer":"resetRoomShortTimer","error":"Unexpected error"}')

    def get_room_temp(self, room):
        """ Returns measured temperature of room 

        """
        return(json.dumps({"room" : room, "isTemp" : self.clients[room]["isTemp"]}))

    def get_room_set_temp(self, room):
        """ Returns normal set temperature of room 
        Normal temperature is the value when in on-mode

        """
        return(json.dumps({"room" : room, "setTemp" : self.clients[room]["setTemp"]}))

    def set_room_set_temp(self, room, temp):
        """ Sets normal set temperature of room 
        Normal temperature is the value when in on-mode

        """
        try:
            self.clients[room]["setTemp"] = float(temp)
        except:
            return('{"answer":"setRoomSetTemp", "error": "temp must be of type float"}')
        try:
            logger.info("Setting setTemp for room %s to %s°C", room, temp)
            return(json.dumps({"room" : room, "setTemp" : self.clients[room]["setTemp"]}))
        except:
            return('{"answer":"setRoomSetTemp", "error": "Unexpected error"}')

    def get_mixer(self):
        """ Returns is a mixer is available.

        Answer:
        "{"request":"get_mixer", "answer":"not available"}"
        "{"request":"get_mixer", "answer":"available"}"
        """
        if(self.mixer_addr == -1):
            return(json.dumps({"request":"get_mixer", "answer":"not available"}))
        else:
            return(json.dumps({"request":"get_mixer", "answer":"available"}))

    def mixer_running(self):
        """ Returns if mixer is running.

        Answer:
        "{"request":"mixer_running", "answer":true}"
        "{"request":"mixer_running", "answer":false}"

        In case no mixer is available:
        "{"request":"mixer_running", "answer":"Error"}"

        """
        try:
            return(json.dumps({"request":"mixer_running", "answer":self.mix.running}))
        except:
            return(json.dumps({"request":"mixer_running", "answer":"Error"}))

    def get_ff_is_temp(self):
        """ Returns measured mixer forward flow temperature

        Answer:
        {"request" : "FfIsTemp", "answer" : 77.0, "Unit" : "°C"})

        In case no mixer is available:
        "{"request":"FFIsTemp", "answer":"Error"}"

        """
        try:
            return(json.dumps({"request" : "FfIsTemp", "answer" : self.mix.ff_temp_is, "Unit" : "°C"}))
        except:
            return(json.dumps({"request" : "FfIsTemp", "answer" : "Error"}))

    def get_ff_set_temp(self):
        """ Returns set mixer forward flow temperature

        Answer:
        {"request" : "FfSetTemp", "answer" : 77.0, "Unit" : "°C"})
 
        In case no mixer is available:
        "{"request":"FFSetTemp", "answer":"Error"}"

        """
        try:
            return(json.dumps({"request" : "FfSetTemp", "answer" : self.mix.ff_temp_target, "Unit" : "°C"}))
        except:
            return(json.dumps({"request" : "FfSetTemp", "answer" : "Error"}))

    def get_counter(self):
        try:
            return(json.dumps({"Floor" : self.name, "Counter" : self.zaehler}))
        except:
            return(json.dumps({"Answer":"Counter","Result":"Error"}))

    def get_counter_values(self, counter):
        '''
        This functions reads some values from the energy counter and retruns them as json string.
        '''
        try:
            idx = self.zaehler.index(counter)
        except Exception as e:
            logger.error(e)
            return(json.dumps({"Answer":"getCounterValues","Result":"Error"}))
            
        logger.info("Getting values from MBus counter")
        mb = mbus.mbus(address=self.zaehleraddr[idx])
        result = mb.do_char_dev()
        job = json.loads(result)
        energy = []
        for i in (job['body']['records']):
            if i['type'] == 'VIFUnit.ENERGY_WH':
                energy.append(float(i['value']))
            if i['type'] == 'VIFUnit.FLOW_TEMPERATURE':
                flow_temp = float(i['value'])
            if i['type'] == 'VIFUnit.RETURN_TEMPERATURE':
                return_temp =float(i['value'])
            if i['type'] == 'VIFUnit.POWER_W' and i['function'] == 'FunctionType.INSTANTANEOUS_VALUE':
                power = float(i['value'])
            if i['type'] == 'VIFUnit.VOLUME_FLOW' and i['function'] == 'FunctionType.INSTANTANEOUS_VALUE':
                flow = float(i['value'])
        data = {}
        data["Energy"] = {"Value":max(energy), "Unit": "Wh"}
        data["ForwardFlow"] = {"Value":flow_temp, "Unit":"°C"}
        data["ReturnFlow"] = {"Value":return_temp, "Unit":"°C"}
        data["Power"] = {"Value":power, "Unit":"W"}
        data["Flow"] = {"Value":round(flow*1000,2), "Unit":"l/h"}
        logger.info(data)
        return(json.dumps({"Floor" : self.name, "Counter" : self.zaehler[idx], "Data" : data}))

    def check_reset(self):
        if(self.system["ModeReset"]!="off"):
            now = datetime.datetime.now()
            now_h = int(now.hour) 
            now_m = int(now.minute)
            res_h = int(self.system["ModeReset"].split(":")[0])
            res_m = int(self.system["ModeReset"].split(":")[1])
            if(now_h == res_h):
                if(now_m == res_m or now_m == res_m+1):
                    logger.info("Resetting mode to auto")
                    for client in self.clients:
                        self.clients[client]["Mode"] = "auto"

    def short_timer(self):
        '''
        Starts the short timer thread
        '''
        shortTimerT = threading.Thread(target=self._short_timer)
        shortTimerT.setDaemon(True)
        shortTimerT.start()

    def _short_timer(self):
        '''
        Frequently look, if a shorttimer is activated for some room.
        If yes, switch from automatic mode to shorttimer moder
        '''
        prctl.set_name("Shorttimer")
        if True:
        #try:
            timeout = 1
            while(not self.t_stop.is_set()):
                for client in self.clients:
                    if(self.clients[client]["Shorttimer"] > 0 and self.clients[client]["ShorttimerMode"] == "run"):
                        #logger.debug("%s: -%ds", client, self.clients[client]["Shorttimer"])
                        self.clients[client]["Shorttimer"] -= timeout
                    else:
                        self.reset_room_shorttimer(client)
                #logger.info("Running short_timer")
                self.t_stop.wait(timeout)
        #except Exception as e:
        #    logger.error(e)

    def timer_operation(self):
        '''
        Starts the timer_operation Thread.
        '''
        timerT = threading.Thread(target=self._timer_operation)
        timerT.setDaemon(True)
        timerT.start()

    def _timer_operation(self):
        ''' This function provides the freqent operation of the controller.
        '''
        prctl.set_name("Timer Operation")
        logger.info("Starting Timeroperationthread as " + threading.currentThread().getName())
        while(not self.t_stop.is_set()):
            self.set_status()
            self.t_stop.wait(60)
        if self.t_stop.is_set():
            logger.info("Ausgetimed!")

    def read_config(self):
        self.hostname = socket.gethostname()
        self.basehost = ""
        realpath = os.path.realpath(__file__)
        basepath = os.path.split(realpath)[0]
        setpath = os.path.join(basepath, 'settings')
        inifile = os.path.join(setpath, self.hostname + '.ini')

        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        logger.info("Loading " + inifile)
        self.config.read(inifile)

        self.baseport = int(self.config['BASE']['Port'])
        self.hysterese = float(self.config['BASE']['Hysterese'])
        clients = self.config['BASE']['Clients'].split(";")
        names = self.config['BASE']['Names'].split(";")
        self.name = self.config['BASE']['Name']
        self.sensorik = {}
        sensorik = dict(self.config.items('SENSORS'))
        for sensor in sensorik:
            tmp = sensorik[sensor].split(", ")
            self.sensorik[sensor] = {}
            self.sensorik[sensor]["Type"] = tmp[0]
            self.sensorik[sensor]["System"] = tmp[1]
            self.sensorik[sensor]["ID"] = tmp[2]
            self.sensorik[sensor]["PreviousVal"] = 0
        self.pumpe = int(self.config['BASE']['Pumpe'])
        self.oekofen = int(self.config['BASE']['Oekofen'])
        try:
            self.zaehler = self.config['BASE']['Zaehler'].split(";")
            self.zaehleraddr = (self.config['BASE']['ZaehlerAddr'].split(";"))
            self.zaehleraddr = [int(i) for i in self.zaehleraddr]
            logger.info(self.zaehler)
            logger.info(self.zaehleraddr)
        except:
            # Kein Zähler konfiguriert
            pass

        relais_tmp = self.config['BASE']['Relais'].split(";")
        relais = []
        for i in range(len(relais_tmp)):
                tmp = (relais_tmp[i].split(","))
                tmp1 = []
                for j in range(len(tmp)):
                    tmp1.append(int(tmp[j]))
                relais.append(tmp1)
        i = 0
        self.clients = {} # Dict with all room information
        for client in clients:
            self.clients[client] = {}
            self.clients[client]["Relais"] = relais[i]
            self.clients[client]["Status"] = "off"
            self.clients[client]["Mode"] = "auto"
            self.clients[client]["setMode"] = "auto"
            self.clients[client]["setWindow"] = "auto"
            self.clients[client]["setTemp"] = 21
            self.clients[client]["isTemp"] = 18
            self.clients[client]["Shorttimer"] = 0
            self.clients[client]["ShorttimerMode"] = "off"
            self.clients[client]["Timer"] = "off"
            self.clients[client]["Name"] = names[i]
            i += 1
        self.polarity = self.config['BASE']['Polarity']
        self.unusedRel = self.config['BASE']['UnusedRel'].split(";")
        if self.polarity == "invers":
            self.on = 0
            self.off = 1
        else:
            self.on = 1
            self.off = 0
        self.logpath = os.path.join(basepath, 'log')
        self.timerpath = setpath
        self.timerfile = self.config['BASE']['Timerfile']
        if(self.timerfile == ""):
            self.timerfile = "timer_" + self.hostname + ".json"
        self.timerfile = os.path.join(setpath, self.timerfile)
        logger.info(self.timerfile)
        try:
            self.garagenkontakt = int(self.config['GARAGE']['Kontakt'])
        except:
            self.garagenkontakt = -1
        try:
            self.garagenmelder = int(self.config['GARAGE']['Melder'])
        except:
            self.garagenmelder = -1
        try:
            self.mixer_addr = hex(int(self.config['BASE']['Mischer'],16))
            logger.info(self.mixer_addr)
            self.mixer_sens = self.config['BASE']['MischerSens']
            self.sensorik["VorlaufSoll"] = {}
            self.sensorik["VorlaufSoll"]["Type"] = "Temperatur"
            self.sensorik["VorlaufSoll"]["System"] = "Intern"
            self.sensorik["VorlaufSoll"]["ID"] = "ff_temp_target"
            self.sensorik["VorlaufSoll"]["PreviousVal"] = 0
        except:
            self.mixer_addr = -1
            self.mixer_sens = -1
        self.mqtthost = self.config['MQTT']['mqtthost']
        self.mqttuser = self.config['MQTT']['mqttuser']
        self.mqttpass = self.config['MQTT']['mqttpass']


    def set_hw(self): 
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for i in self.unusedRel:
            if not i == '':
                i = int(i)
                GPIO.setup(i, GPIO.OUT)
                GPIO.output(i, self.off)
                logger.info("Setting BMC " + str(i) + " as unused -> off")
        for client in self.clients:
            for j in self.clients[client]["Relais"]:
                GPIO.setup(j, GPIO.OUT)
                GPIO.output(j, self.off)
                logger.info("Setting BMC " + str(j) + " as output")
        if(self.pumpe > 0):
            GPIO.setup(self.pumpe, GPIO.OUT)
            GPIO.output(self.pumpe, self.off)
            logger.info("Setting BMC " + str(self.pumpe) + " as output")
        else:
            logger.info("Not using pump")
        if(self.garagenkontakt > 0):
            GPIO.setup(self.garagenkontakt, GPIO.OUT)
            GPIO.output(self.garagenkontakt, 0)
            logger.info("Setting Garagenkontakt: %s", str(self.garagenkontakt))
        if(self.garagenmelder > 0):
            GPIO.setup(self.garagenmelder, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            logger.info("Setting Garagenmelder: %s", str(self.garagenmelder))
            GPIO.add_event_detect(self.garagenmelder, GPIO.BOTH, callback = self.garagenmeldung, bouncetime = 250)

    def garagenmeldung(self, channel):
        logger.debug("GARAGENMELDA: %s", str(self.garagenmelder))
        logger.debug("Channel: %s", str(channel))
        if(channel == self.garagenmelder and channel > 0):
            status = GPIO.input(channel)
        else:
            return -1
        try:
            if(status == 1):
                self.garagentor = "zu"
                self.mqttclient.publish("Garage/Tor/Zustand", self.garagentor)
                logger.debug(self.garagentor)
            elif(status == 0):
                self.garagentor = "auf"
                self.mqttclient.publish("Garage/Tor/Zustand", self.garagentor)
                publish.single("Garage/Tor", self.garagentor, hostname=self.mqtthost, client_id=self.hostname, auth = {"username":self.mqttuser, "password":self.mqttpass})
                logger.debug(self.garagentor)
        except Exception as e:
            logger.error(e)

    def get_sensor_values(self):
        logger.debug(self.sensorik)
        for sensor in self.sensorik: #Iterate all sensors configured in ini-file
            pub = False # do not publish as MQTT telegram
            if(self.sensorik[sensor]["ID"] in self.w1_slaves): # Do this, if iterated sensor is a 1w-sensor
                val = round(self.w1.getValue(self.sensorik[sensor]["ID"]),1)
                pub = True # publish as MQTT telegram
                if(sensor in self.clients): 
                    self.clients[sensor]["isTemp"] = val
            if(self.sensorik[sensor]["ID"] == "ff_temp_target"):
                val = self.mix.ff_temp_target
                pub = True # publish as MQTT telegram
            if pub and self.sensorik[sensor]["PreviousVal"] != val:
                self.sensorik[sensor]["PreviousVal"] = val
                now = datetime.datetime.now().replace(microsecond=0).isoformat()
                topic = self.name + "/" + sensor + "/" + self.hostname 
                msg = {"Time":now,
                       self.sensorik[sensor]["System"]:
                            {"Id":self.sensorik[sensor]["ID"],
                             "Temperature":val},
                             "TempUnit":"C"}
                msg = json.dumps(msg)
                publish.single(topic+"/SENSOR",
                               msg,
                               hostname=self.mqtthost,
                               client_id=self.hostname,
                               auth = {"username":self.mqttuser, "password":self.mqttpass})

    def broadcast_value(self):
        '''
        Starts the UDP sensor broadcasting daemon thread
        '''
        self.bcastTstop = threading.Event()
        bcastT = threading.Thread(target=self._broadcast_value)
        bcastT.setDaemon(True)
        bcastT.start()

    def _broadcast_value(self):
        '''
        This function is running as a thread and performs an UDP
        broadcast of sensor values every 20 seconds on port udpBcPort.
        This datagram could be fetched by multiple clients for purposes
        of display or storage.
        '''
        prctl.set_name("UDP Broadcast Value")
        logger.info("Starting UDP Sensor Broadcasting Thread" + threading.currentThread().getName())
        while(not self.bcastTstop.is_set()):
            try:
                self.get_sensor_values()
            except Exception as e:
                logger.error("Error in broadcast_value: sensor_values")
                logger.error(str(e))
            try:
                self.garagenmeldung(self.garagenmelder)
            except Exception as e:
                logger.error("Error in broadcast_value: Garagenmeldung")
                logger.error(str(e))
            self.bcastTstop.wait(20)

    def set_pumpe(self):
        '''
        This Function starts Pumpenthread.
        '''
        pumpT = threading.Thread(target=self._set_pumpe)
        pumpT.setDaemon(True)
        pumpT.start()


    def _set_pumpe(self):
        '''
        If a pump is configured, the pump thread will be started.
        The thread checks frequently (every 60 seconds by default),
        if at least one heating circuit is active. If yes, the pump is
        switched on. Puprose is to operate the pump only when needed.
        '''
        prctl.set_name("Famous Pumpenthread")
        if(self.pumpe < 1):
            logger.info("Not starting Pumpenthread, no pump present")
            return
        try:
            logger.info("Starting Pumpenthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):
                # Checking, if one of the room outputs is switches on -> if yes, switch pump on
                # First, Outputs are checked and their values are collected in state[]
                state = []
                for client in self.clients:
                    state.append(self.clients[client]["Status"])
                logger.debug("State for pump: %s", state)
                # Check, if any of the outputs is switched to on, if yes, activate pump
                if(any(st == "on" for st in state)):
                    logger.debug("Irgendeiner ist on")
                    if GPIO.input(self.pumpe) == self.off:
                        logger.info("Switching pump on")
                        GPIO.output(self.pumpe, self.on)
                        logger.debug("Pump: %s", self.on)
                    try:
                        # Try is only successful, if there is a mixer object
                        if(not self.mix.is_running()):
                            #Check, if mixer is running, if not, starting mixer if present
                            self.mix.run()
                    except:
                        # Do nothing, because mixer object is not present
                        pass

                else:
                    if GPIO.input(self.pumpe) == self.on:
                        logger.info("Switching pump off")
                        GPIO.output(self.pumpe, self.off)
                        logger.debug("Pump: %s", self.off)
                    try:
                        # Try is only successful, if there is a mixer object
                        if(self.mix.is_running()):
                            #Check, if mixer is running, if yes, stop mixer if present
                            self.mix.stop()
                    except:
                        # Do nothing, because mixer object is not present
                        pass
                self.t_stop.wait(30)
                #if self.t_stop.is_set():
            logger.info("Ausgepumpt")
        except Exception as e:
            logger.error(e)
                
    def set_status(self):
        '''
        This function controls the heating circuits. The circuits are normally
        controlled by the timer.json file and the room temperature.
        A heating circuit is switched on, when we are within the on-time and the room
        temperature is below the set room temperature.
        It will be checked, if a manual mode (on/off) is selectedm this overrides automatic mode,
        this includes the Shorttimer function.
        Last but not least, is is checked, if the main heating pump is running. If not, all
        heating circuitsare turned off.
        '''
        logger.debug("Running set_status")
        self.check_reset() # Schaut, ob manuelle Modi auf auto zurückgesetzte werden müssen
        # Schauen, ob die Umwaelzpumpe läuft
        if(self.get_oekofen_pumpe()):
            logger.debug("Umwaelzpumpe an")
            for client in self.clients:
                # Hole Wert (on/off) aus Timerfile 
                self.clients[client]["Timer"] = self.Timer.get_recent_set(client)
                # Wenn im auto-Modus und Zusand lt. Timerfile on:
                old = self.clients[client]["Status"]
                if(self.clients[client]["Mode"] == "auto" and self.clients[client]["Timer"] == "on"):
                    # isTemp < setTemp mit Hysterese -> on
                    if float(self.clients[client]["setTemp"])  - self.hysterese/2 >= float(self.clients[client]["isTemp"]):
                        self.clients[client]["Status"] = "on"
                    # isTemp > setTemp mit Hysteres -> off
                    elif float(self.clients[client]["setTemp"]) + self.hysterese/2 <= float(self.clients[client]["isTemp"]):
                        self.clients[client]["Status"] = "off"
                        logger.debug(client + " running in auto mode, setting state to " + self.clients[client]["Status"])
                # Im manuellen Modus, Zustand on:
                elif(self.clients[client]["Mode"] == "on"):
                    self.clients[client]["Status"] = "on"
                    logger.debug(client + " running in manual mode, setting state to " + self.clients[client]["Status"])
                # Im manuellen Modus, Zustand off:
                elif(self.clients[client]["Mode"] == "off"):
                    self.clients[client]["Status"] = "off"
                    logger.debug(client + " running in manual mode, setting state to " + self.clients[client]["Status"])
                else:
                    self.clients[client]["Status"] = "off"
                    logger.debug(client + " running in auto mode, setting state to " + self.clients[client]["Status"])
                # Log-Ausgabe und MQTT-Message, wenn sich der Schaltzustand geändert hat
                if(old != self.clients[client]["Status"]):
                    logger.info("State has changed: turning %s %s", client, self.clients[client]["Status"])
                    now = datetime.datetime.now().replace(microsecond=0).isoformat()
                    topic = self.name + "/" + client + "/" + self.hostname
                    if self.clients[client]["Status"] == "on":
                        state = 1
                    else:
                        state = 0
                    msg = {"Time":now,
                           "State":state}
                    msg = json.dumps(msg)
                    publish.single(topic+"/VALVE",
                                   msg,
                                   hostname=self.mqtthost,
                                   client_id=self.hostname,
                                   auth = {"username":self.mqttuser, "password":self.mqttpass})
        # Wenn die Umwälzpumpe nicht läuft, alles ausschalten:
        else:
            logger.debug("Umwaelzpumpe aus")
            for client in self.clients:
                self.clients[client]["Status"] = "off"
                logger.debug("heating pump off, setting "+ client +" state to " + self.clients[client]["Status"])
        self.hw_state()

    def hw_state(self): #OK
        logger.debug("Running hw_state")
        for client in self.clients:
            if self.clients[client]["Status"] == "on":
                val = self.on
            else:
                val = self.off
            for relais in self.clients[client]["Relais"]:
                logger.debug("Client: %s, Relais: %d: %s", client, relais, val)
                GPIO.output(relais,val)
                logger.debug("Ventilausgang %s: %s", relais, val)
 
    def stop(self):
        self.t_stop.set()
        logger.info("Steuerung: So long sucker!")
        for client in self.clients:
            for j in self.clients[client]["Relais"]:
                GPIO.output(j, self.off)
                logger.info("Switching BMC " + str(j) + " off")
        if(self.pumpe > 0):
            GPIO.output(self.pumpe, self.off)
            logger.info("Switching BMC " + str(self.pumpe) + " off")
        GPIO.cleanup()
        return


    def run(self):
         self.runstop = threading.Event()
         runT = threading.Thread(target=self._run, name="run_thread")
         runT.setDaemon(True)
         runT.start()

    def _run(self):
        prctl.set_name("Running runner")
        while True:
            try:
                if self.mixer_sens in self.sensorik:
                    logger.debug(self.w1.getValue(self.sensorik[self.mixer_sens]["ID"]))
                    self.mix.ff_temp_is = self.w1.getValue(self.sensorik[self.mixer_sens]["ID"])
                    logger.debug(self.mix.ff_temp_is)
                time.sleep(5)
            except KeyboardInterrupt: # CTRL+C exit
                self.stop()
                break

#host_name = "0.0.0.0"
#port = 5000 
#app = Flask(__name__)
#api = Api(app)

#api.add_resource(Status, '/status', '/status/<string:id>')

#if __name__ == "__main__":
#    steuerung = steuerung()
#    threading.Thread(target=lambda: app.run(host=host_name, port=port, debug=True, use_reloader=False)).start()
#    steuerung.run()

