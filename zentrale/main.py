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
import syslog
from libby import tempsensors
from libby import remote
from libby import mbus
import threading
from threading import Thread
import urllib
import urllib.request
import logging

# TODO
# - Integration Ist-Temperatur
# - Absenktemperatur
# - Sauberes Beenden

udp_port = 5005
server = "dose"
datacenterport = 6663
udpBcPort =  6664
logging.basicConfig(level=logging.INFO)
#logging.basicConfig(level=logging.DEBUG)

class steuerung(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logging.info("Starting Steuerungthread as " + threading.currentThread().getName())
        self.t_stop = threading.Event()
        self.read_config()
        self.sensor_values = {} 
        self.system = {"ModeReset":"2:00"}
        
        self.set_hw()
        
        self.w1 = tempsensors.onewires()
        self.w1_slaves = self.w1.enumerate()
        self.Timer = timer(self.timerfile)
        
        #Starting Threads
        self.set_pumpe()
        self.short_timer()
        self.timer_operation()


        self.udpServer()
        self.broadcast_value()

    def udpServer(self):
        logging.info("Starting UDP-Server at " + self.basehost + ":" + str(udp_port))
        self.udpSock = socket.socket( socket.AF_INET,  socket.SOCK_DGRAM )
        self.udpSock.bind( (self.basehost,udp_port) )

        udpT = threading.Thread(target=self._udpServer)
        udpT.setDaemon(True)
        udpT.start()

    def _udpServer(self):
        logging.info("Server laaft")
        while(not self.t_stop.is_set()):
            try:
                data, addr = self.udpSock.recvfrom( 1024 )# Puffer-Groesse ist 1024 Bytes.
                #logging.debug("Kimm ja scho")
                ret = self.parseCmd(data) # Abfrage der Fernbedienung (UDP-Server), der Rest passiert per Interrupt/Event
                self.udpSock.sendto(str(ret).encode('utf-8'), addr)
            except Exception as e:
                try:
                    self.udpSock.sendto(str('{"answer":"error"}').encode('utf-8'), addr)
                    logging.warning("Uiui, beim UDP senden/empfangen hat's kracht!" + str(e))
                except Exception as o:
                    logging.warning("Uiui, beim UDP senden/empfangen hat's richtig kracht!" + str(o))

    def get_oekofen_pumpe(self):
        """ Get status from Oekofen heating pump
        Retries, if no response

        """
        if(self.oekofen == 0):
            # Do not get state of heating system, just return true to simulate a running heating pump
            logging.debug("Not taking Oekofen state into account")
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
        except:
            logging.warning("Das ist mal kein JSON, pff!")
            ret = json.dumps({"answer": "Kaa JSON Dings!"})
            return(ret)
        if(jcmd['command'] == "getStatus"):
            ret = self.get_status()
        elif(jcmd['command'] == "getAlive"):
            ret = self.get_alive()
        elif(jcmd['command'] == "getRooms"):
            ret = self.get_rooms()
        elif(jcmd['command'] == "getTimer"):
            ret = self.get_timer(jcmd['Room'])
        elif(jcmd['command'] == "setTimer"):
            ret = self.set_timer(jcmd['Room'])
        elif(jcmd['command'] == "reloadTimer"):
            ret = self.reload_timer()
        elif(jcmd['command'] == "getRoomStatus"):
            ret = self.get_room_status(jcmd['Room'])
        elif(jcmd['command'] == "setRoomStatus"):
            ret = self.set_room_status(jcmd['Room'])
        elif(jcmd['command'] == "getRoomMode"):
            ret = self.get_room_mode(jcmd['Room'])
        elif(jcmd['command'] == "setRoomMode"):
            ret = self.set_room_mode(jcmd['Room'],jcmd['Mode'])
        elif(jcmd['command'] == "getRoomShortTimer"):
            ret = self.get_room_shorttimer(jcmd['Room'])
        elif(jcmd['command'] == "setRoomShortTimer"):
            ret = self.set_room_shorttimer(jcmd['Room'],jcmd['Time'],jcmd['Mode'])
        elif(jcmd['command'] == "getRoomNormTemp"):
            ret = self.get_room_norm_temp(jcmd['Room'])
        elif(jcmd['command'] == "setRoomNormTemp"):
            ret = self.set_room_norm_temp(jcmd['Room'],jcmd['normTemp'])
        elif(jcmd['command'] == "getCounterValues"):
            ret = self.get_counter_values()
        else:
             ret = json.dumps({"answer":"Fehler","Wert":"Kein gültiges Kommando"})
        return(ret)

    def get_rooms(self):
        """ function to return available rooms

        """
        ret = json.dumps({"answer":"getRooms","available_rooms":self.clients})
        return(ret)

    def get_room_status(self, room):
        """ function to get status status of a single room

        """
        try:
            logging.info(self.clients[room])
            ret = json.dumps({"answer":"getRoomStatus","room":room,"status":self.clients[room]})
        except:
            ret = json.dumps({"answer":"room does not exist"})
        return(ret)

    def set_room_status(self, room):
        """ function to set status status of a single room

        """
        #TODO
        return()

    def get_timer(self, room):
        """ function to read the timer settings per room

        """
        ret = json.dumps(self.Timer.get_timer_list(room))
        return(ret)

    def set_timer(self, room):
        #TODO
        return()

    def reload_timer(self):
        """ This function reloads the timer file

        """
        self.Timer = timer(self.timerfile)
        return(json.dumps({"answer":"Timer file reloaded"}))

    def get_alive(self):
        """ function to see, if we are alive

        """
        return(json.dumps({"name":self.hostname,"answer":"Freilich"}))


    def get_status(self):
        """ function to determine status of system

        """
        return(json.dumps(self.clients))

    def get_room_mode(self, room):
        """ Returning mode of room

        """
        return(json.dumps({"answer":"getRoomMode","room":room,"mode":self.clients[room]["Mode"]}))

    def set_room_mode(self, room, mode):
        """ Setting mode of room

        """
        self.clients[room]["Mode"] = mode
        return(json.dumps({"answer":"setRoomMode","room":room,"mode":self.clients[room]["Mode"]}))

    def get_room_shorttimer(self, room):
        """ Returns value of room's shorttimer to overrider Mode settings for a defined time in seconds

        """
        return(json.dumps(self.clients[room]["Shorttimer"]))

    def set_room_shorttimer(self, room, time, mode):
        """ Sets value of room's shorttimer, sets mode accordingly
        After setting, set_status is called to apply change immediately

        """
        try:
            self.clients[room]["Shorttimer"] = int(time)
            self.clients[room]["ShorttimerMode"] = "run"
            self.clients[room]["Mode"] = mode
            logging.info("Setting shorttimer for room %s to %ds: %s", room, int(time), mode)
            self.set_status()
            return(json.dumps(self.clients[room]["Shorttimer"]))
        except:
            return('{"answer":"error","command":"Shorttimer"}')

    def get_room_norm_temp(self, room):
        """ Returns normal set temperature of room 
        Normal temperature is the value when in on-mode

        """
        return(json.dumps({"room" : room, "normTemp" : self.clients[room]["normTemp"]}))

    def set_room_norm_temp(self, room, temp):
        """ Sets normal set temperature of room 
        Normal temperature is the value when in on-mode

        """
        try:
            self.clients[room]["normTemp"] = float(temp)
            logging.info("Setting normTemp for room %s to %s°C", room, temp)
            return(json.dumps({"room" : room, "normTemp" : self.clients[room]["normTemp"]}))
        except:
            return('{"answer":"error","command":"setRoomNormTemp"}')

    def get_counter_values(self):
        '''
        This functions reads some values from the energy counter and retruns them as json string.
        '''
        logging.info("Getting values from MBus counter")
        mb = mbus.mbus()
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
        logging.info(data)
        return(json.dumps({"Floor" : self.name, "Data" : data}))

    def check_reset(self):
        if(self.system["ModeReset"]!="off"):
            now = datetime.datetime.now()
            now_h = int(now.hour) 
            now_m = int(now.minute)
            res_h = int(self.system["ModeReset"].split(":")[0])
            res_m = int(self.system["ModeReset"].split(":")[1])
            if(now_h == res_h):
                if(now_m == res_m or now_m == res_m+1):
                    logging.info("Resetting mode to auto")
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
        if True:
        #try:
            timeout = 1
            while(not self.t_stop.is_set()):
                for client in self.clients:
                    if(self.clients[client]["Shorttimer"] > 0 and self.clients[client]["ShorttimerMode"] == "run"):
                        #logging.debug("%s: -%ds", client, self.clients[client]["Shorttimer"])
                        self.clients[client]["Shorttimer"] -= timeout
                    else:
                        self.clients[client]["Shorttimer"] = 0
                        self.clients[client]["ShorttimerMode"] = "off"
                        old = self.clients[client]["Mode"]
                        self.clients[client]["Mode"] = "auto"
                        if(old != self.clients[client]["Mode"]):
                            logging.info("End of shorttimer %s, resetting mode to auto", client)
                            self.hw_state()
                #logging.info("Running short_timer")
                self.t_stop.wait(timeout)
        #except Exception as e:
        #    logging.error(e)

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
        logging.info("Starting Timeroperationthread as " + threading.currentThread().getName())
        while(not self.t_stop.is_set()):
            self.set_status()
            self.t_stop.wait(60)
        if self.t_stop.is_set():
            logging.info("Ausgetimed!")

    def read_config(self):
        self.hostname = socket.gethostname()
        self.basehost = self.hostname + ".home"
        realpath = os.path.realpath(__file__)
        basepath = os.path.split(realpath)[0]
        setpath = os.path.join(basepath, 'settings')
        inifile = os.path.join(setpath, self.hostname + '.ini')

        self.config = configparser.ConfigParser()
        logging.info("Loading " + inifile)
        self.config.read(inifile)

        self.baseport = int(self.config['BASE']['Port'])
        self.hysterese = float(self.config['BASE']['Hysterese'])
        clients = self.config['BASE']['Clients'].split(";")
        names = self.config['BASE']['Names'].split(";")
        self.sensors = self.config['BASE']['Sensors'].split(";")
        self.name = self.config['BASE']['Name']
        self.sensor_ids = self.config['BASE']['Sensor_IDs'].split(";")
        self.pumpe = int(self.config['BASE']['Pumpe'])
        self.oekofen = int(self.config['BASE']['Oekofen'])
        relais_tmp = self.config['BASE']['Relais'].split(";")
        relais = []
        for i in range(len(relais_tmp)):
                tmp = (relais_tmp[i].split(","))
                tmp1 = []
                for j in range(len(tmp)):
                    tmp1.append(int(tmp[j]))
                relais.append(tmp1)
        i = 0
        self.clients = {}
        for client in clients:
            self.clients[client] = {}
            self.clients[client]["Relais"] = relais[i]
            self.clients[client]["Status"] = "off"
            self.clients[client]["Mode"] = "auto"
            self.clients[client]["normTemp"] = 21
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
        self.timerfile = os.path.join(setpath, self.config['BASE']['Timerfile'])
        logging.info(self.timerfile)

    def set_hw(self): 
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for i in self.unusedRel:
            if not i == '':
                i = int(i)
                GPIO.setup(i, GPIO.OUT)
                GPIO.output(i, self.off)
                logging.info("Setting BMC " + str(i) + " as unused -> off")
        for client in self.clients:
            for j in self.clients[client]["Relais"]:
                GPIO.setup(j, GPIO.OUT)
                GPIO.output(j, self.off)
                logging.info("Setting BMC " + str(j) + " as output")
        if(self.pumpe > 0):
            GPIO.setup(self.pumpe, GPIO.OUT)
            GPIO.output(self.pumpe, self.off)
            logging.info("Setting BMC " + str(self.pumpe) + " as output")
        else:
            logging.info("Not using pump")

    def get_sensor_values(self):
        for sensor in self.sensor_ids:
            if(sensor in self.w1_slaves):
                val = self.w1.getValue(sensor)
                idx = self.sensor_ids.index(sensor)
                sensor = self.sensors[idx]
                now = time.strftime('%Y-%m-%d %H:%M:%S')
                self.sensor_values[sensor] = {}
                self.sensor_values[sensor]["Value"] = round(val,1)
                self.sensor_values[sensor]["Timestamp"] = now
                # Check, if the received sensor value belongs to a client and if yes, store the value to the client dict.
                client = sensor[0:sensor.find("Temp")]
                if(client in self.clients):
                    self.clients[client]["isTemp"] = self.sensor_values[sensor]["Value"]


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
        logging.info("Starting UDP Sensor Broadcasting Thread" + threading.currentThread().getName())
        udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udpSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT,1)
        udpSock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST, 1)
        udpSock.settimeout(0.1)
        while(not self.bcastTstop.is_set()):
            try:
                self.get_sensor_values()
                for sensor in self.sensor_values: 
                    message = {"measurement":{sensor:{"Value":0,"Floor":"","Type":"Temperature","Unit":"°C","Timestamp":"","Store":1}}}
                    message["measurement"][sensor]["Floor"] = self.name
                    message["measurement"][sensor]["Value"] = self.sensor_values[sensor]["Value"]
                    message["measurement"][sensor]["Timestamp"] = self.sensor_values[sensor]["Timestamp"]
                    udpSock.sendto(json.dumps(message).encode(),("<broadcast>",udpBcPort))
            except Exception as e:
                logging.error(str(e))
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
        The thread checks frequently (every 60 seconds by defualt),
        if at least one heating circuit is active. If yes, the pump is
        switched on. Puprose is to operate the pump only when needed.
        '''
        if(self.pumpe < 1):
            logging.info("Not starting Pumpenthread, no pump present")
            return
        try:
            logging.info("Starting Pumpenthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):
                # Checking, if one of the room outputs is switches on -> if yes, switch pump on
                # First, Outputs are checked and their values are collected in state[]
                state = []
                for client in self.clients:
                    state.append(self.clients[client]["Status"])
                logging.debug("State for pump: %s", state)
                # Check, if any of the outputs is switched to on, if yes, activate pump
                if(any(st == "on" for st in state)):
                    logging.debug("Irgendeiner ist on")
                    if GPIO.input(self.pumpe) == self.off:
                        logging.info("Switching pump on")
                    GPIO.output(self.pumpe, self.on)
                    logging.debug("Pump: %s", self.on)
                else:
                    if GPIO.input(self.pumpe) == self.on:
                        logging.info("Switching pump off")
                    GPIO.output(self.pumpe, self.off)
                    logging.debug("Pump: %s", self.off)
                    self.t_stop.wait(60)
                if self.t_stop.is_set():
                    logging.info("Ausgepumpt")
        except Exception as e:
            logging.error(e)
                
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
        logging.debug("Running set_status")
        self.check_reset() # Schaut, ob manuelle Modi auf auto zurückgesetzte werden müssen
        # Schauen, ob die Umwaelzpumpe läuft
        if(self.get_oekofen_pumpe()):
            logging.debug("Umwaelzpumpe an")
            for client in self.clients:
                # Hole Wert (on/off) aus Timerfile 
                self.clients[client]["Timer"] = self.Timer.get_recent_set(client)
                # Wenn im auto-Modus und Zusand lt. Timerfile on:
                old = self.clients[client]["Status"]
                if(self.clients[client]["Mode"] == "auto" and self.clients[client]["Timer"] == "on"):
                    # isTemp < normTemp mit Hysterese -> on
                    if float(self.clients[client]["normTemp"])  - self.hysterese/2 >= float(self.clients[client]["isTemp"]):
                        self.clients[client]["Status"] = "on"
                    # isTemp > normTemp mit Hysteres -> off
                    elif float(self.clients[client]["normTemp"]) + self.hysterese/2 <= float(self.clients[client]["isTemp"]):
                        self.clients[client]["Status"] = "off"
                        logging.debug(client + " running in auto mode, setting state to " + self.clients[client]["Status"])
                # Im manuellen Modus, Zustand on:
                elif(self.clients[client]["Mode"] == "on"):
                    self.clients[client]["Status"] = "on"
                    logging.debug(client + " running in manual mode, setting state to " + self.clients[client]["Status"])
                # Im manuellen Modus, Zustand off:
                elif(self.clients[client]["Mode"] == "off"):
                    self.clients[client]["Status"] = "off"
                    logging.debug(client + " running in manual mode, setting state to " + self.clients[client]["Status"])
                else:
                    self.clients[client]["Status"] = "off"
                    logging.debug(client + " running in auto mode, setting state to " + self.clients[client]["Status"])
                if(old != self.clients[client]["Status"]):
                    logging.info("State has changed: turning %s %s", client, self.clients[client]["Status"])
        # Wenn die Umwälzpumpe nicht läuft, alles ausschalten:
        else:
            logging.debug("Umwaelzpumpe aus")
            for client in self.clients:
                self.clients[client]["Status"] = "off"
                logging.debug("heating pump off, setting "+ client +" state to " + self.clients[client]["Status"])
        self.hw_state()

    def hw_state(self): #OK
        logging.debug("Running hw_state")
        for client in self.clients:
            if self.clients[client]["Status"] == "on":
                val = self.on
            else:
                val = self.off
            for relais in self.clients[client]["Relais"]:
                logging.debug("Client: %s, Relais: %d: %s", client, relais, val)
                GPIO.output(relais,val)
                logging.debug("Ventilausgang %s: %s", relais, val)
 
    def stop(self):
        self.t_stop.set()
        logging.info("Steuerung: So long sucker!")
        for client in self.clients:
            for j in self.clients[client]["Relais"]:
                GPIO.output(j, self.off)
                logging.info("Switching BMC " + str(j) + " off")
        if(self.pumpe > 0):
            GPIO.output(self.pumpe, self.off)
            logging.info("Switching BMC " + str(self.pumpe) + " off")
        GPIO.cleanup()
        return

    def run(self):
        while True:
            try:
                time.sleep(.5)
            except KeyboardInterrupt: # CTRL+C exit
                self.stop()
                break

if __name__ == "__main__":
    steuerung = steuerung()
    steuerung.start()
    steuerung.run()
    

