#!/usr/bin/env python3
import socket
import os
import RPi.GPIO as GPIO
import sys
import time
import configparser
import json
from timer import timer
import syslog
from libby import tempsensors
import mysql.connector
import threading
from threading import Thread
#from libby.logger import logger
import logging
logging.basicConfig(level=logging.DEBUG)


# TODO
# - Heizungsbetrieb abhängig von Umwälzpumpe im Keller
# - Integrtion Ist-Temperatur
# - Manueller Betrieb
# - Monit-Umbau auf JSON
# - jsonfile korrekt laden
# - Sauberes Beenden

#logging = True
udp_port = 5005


class steuerung(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logging.info("Starting Steuerungthread as " + threading.currentThread().getName())
        self.t_stop = threading.Event()
        self.delay = .1

        self.read_config()

        self.sensor_values = [18.5]
        for i in range(len(self.sensors)-1):
                self.sensor_values.append(18.5)
        
        self.mysql_success = False
        self.mysql_start()


        logging.info("Starting UDP-Server at " + self.basehost + ":" + str(self.baseport))
        self.e_udp_sock = socket.socket( socket.AF_INET,  socket.SOCK_DGRAM )
        self.e_udp_sock.bind( (self.basehost,self.baseport) ) 
        
        self.set_hw()
        
        self.w1 = tempsensors.onewires()
        self.w1_slaves = self.w1.enumerate()
        self.Timer = timer(self.timerfile)
        threading.Thread(target=self.set_pumpe).start()
        #threading.Thread(target=self.log_state).start()
        threading.Thread(target=self.timer_operation).start()
        self.udpServer()

    def udpServer(self):
        logging.info("Starting UDP-Server at " + self.basehost + ":" + str(udp_port))
        self.udpSock = socket.socket( socket.AF_INET,  socket.SOCK_DGRAM )
        self.udpSock.bind( (self.basehost,udp_port) )
        #self.udpSock.bind( ('fbhdg.local',udp_port) )

        self.t_stop = threading.Event()
        udpT = threading.Thread(target=self._udpServer)
        udpT.setDaemon(True)
        udpT.start()

    def _udpServer(self):
        logging.info("Server laaft")
        while(not self.t_stop.is_set()):
            try:
                data, addr = self.udpSock.recvfrom( 1024 )# Puffer-Groesse ist 1024 Bytes.
                logging.info("Kimm ja scho")
                ret = self.parseCmd(data) # Abfrage der Fernbedienung (UDP-Server), der Rest passiert per Interrupt/Event
                self.udpSock.sendto(str(ret).encode('utf-8'), addr)
            except Exception as e:
                logging.info("Uiui, beim UDP senden/empfangen hat's kracht!" + str(e))

    def get_oekofen_pumpe(self, pelle):
        """ Get status from Oekofen heating pump
        Retries, if no response

        """
        ret = -1
        while(ret == -1):
            try:
                 with urllib.request.urlopen(pelle) as response:
                     mydata = response.read()
                     d = json.loads(mydata.decode())
                     ret = d["hk1"]["L_pump"]
            except:
                ret = -1
                time.sleep(1)
        return(ret)

    def parseCmd(self, data):
        data = data.decode()
        try:
            jcmd = json.loads(data)
            #logging.info(jcmd['command'])
        except:
            logging.info("Das ist mal kein JSON, pff!")
            ret = json.dumps({"answer": "Kaa JSON Dings!"})
            return(ret)
        if(jcmd['command'] == "getStatus"):
            ret = self.get_status()
        elif(jcmd['command'] == "getAlive"):
            ret = self.get_alive()
        elif(jcmd['command'] == "getRooms"):
            ret = self.get_rooms()
        elif(jcmd['command'] == "getTimer"):
            ret = self.get_timer(jcmd['room'])
        elif(jcmd['command'] == "setTimer"):
            ret = self.set_timer(jcmd['room'])
        elif(jcmd['command'] == "getRoomStatus"):
            ret = self.get_room_status(jcmd['room'])
        elif(jcmd['command'] == "setRoomStatus"):
            ret = self.set_room_status(jcmd['room'])
        else:
             ret = json.dumps({"answer":"Fehler","Wert":"Kein gültiges Kommando"})
        logging.info(ret)
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
        return()

    def get_timer(self, room):
        """ function to read the timer settings per room

        """
        ret = json.dumps(self.Timer.get_timer_list(room))
        return(ret)

    def set_timer(self, room):
        return()

    def get_alive(self):
        """ function to see, if we are alive

        """
        return(json.dumps({"answer":"Freilich"}))


    def get_status(self):
        """ function to determine status of system

        """
        logging.info("Zustand?")
        return(json.dumps(self.clients))

    def mysql_start(self):
        self.mysql_success = False
        try:
            self.cnx = mysql.connector.connect(user=self.mysqluser, password=self.mysqlpass,host=self.mysqlserv,database=self.mysqldb)
            self.cursor = self.cnx.cursor()
            self.mysql_success = True
            logging("Database connection established")
        except Exception as e:
            try:
                self.mysql_success = False
                logging.info("Database connection error")
                self.cnx.disconnect()
            except Exception as e:
                pass

    def mysql_close(self):
        if self.mysql_success == True:
            self.cursor.close()

    def mysql_write(self, now, parameter, value):
        if self.mysql_success == True:
            add = ("INSERT INTO messwert " 
                    "(datetime, parameter, value) "
                    "VALUES (%s, %s, %s)")
            data = (now, parameter, value)
            try:
                self.cursor.execute(add, data)
                mess_id = self.cursor.lastrowid
                self.cnx.commit()
                return mess_id
            except Exception as e:
                logging.info("Fehler beim Schreiben in die Datenbank")
                self.mysql_start()
        else:
            self.mysql_start()

    def timer_operation(self):
        #try:
            logging.info("Starting Timeroperationthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):
                for client in self.clients:
                    self.clients[client]["setTemp"] = self.Timer.get_recent_temp(client)
                    if float(self.clients[client]["setTemp"])  - self.hysterese/2 >= float(self.clients[client]["isTemp"]):  # mit Hysterese
                        self.clients[client]["Status"] = "on"
                    elif float(self.clients[client]["setTemp"]) + self.hysterese/2 <= float(self.clients[client]["isTemp"]):  # mit Hysterese
                        self.clients[client]["Status"] = "off"
                #logging.info("Timerloop: "+ str(self.state))
                self.hw_state()
                self.t_stop.wait(60)
            if self.t_stop.is_set():
                logging.info("Ausgetimed!")
        #except Exception as e:
        #    logging.info(e)

    def read_config(self):
        if True:
        #try:
            hostname = socket.gethostname()
            self.basehost = hostname + '.local'
            realpath = os.path.realpath(__file__)
            basepath = os.path.split(realpath)[0]
            setpath = os.path.join(basepath, 'settings')
            inifile = os.path.join(setpath, hostname + '.ini')

            self.config = configparser.ConfigParser()
            logging.info("Loading " + inifile)
            self.config.read(inifile)

            self.baseport = int(self.config['BASE']['Port'])
            self.hysterese = float(self.config['BASE']['Hysterese'])
            clients = self.config['BASE']['Clients'].split(";")
            self.sensors = self.config['BASE']['Sensors'].split(";")
            self.sensor_ids = self.config['BASE']['Sensor_IDs'].split(";")
            self.pumpe = int(self.config['BASE']['Pumpe'])
            relais_tmp = self.config['BASE']['Relais'].split(";")
            relais = []
            for i in range(len(relais_tmp)):
                    tmp = (relais_tmp[i].split(","))
                    tmp1 = []
                    for j in range(len(tmp)):
                        tmp1.append(int(tmp[j]))
                    relais.append(tmp1)
            self.clients = {}
            i = 0
            for client in clients:
                self.clients[client] = {}
                self.clients[client]["Relais"] = relais[i]
                self.clients[client]["Status"] = "off"
                self.clients[client]["Timer"] = True
                self.clients[client]["setTemp"] = 0
                self.clients[client]["isTemp"] = 18
                i += 1
            #print(json.dumps(self.clients,indent=4))
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
            self.mysqluser = self.config['BASE']['Mysqluser']
            self.mysqlpass = self.config['BASE']['Mysqlpass']
            self.mysqlserv = self.config['BASE']['Mysqlserv']
            self.mysqldb = self.config['BASE']['Mysqldb']
            self.pelle = self.config['BASE']['Pelle']
            self.timerfile = os.path.join(setpath, self.config['BASE']['Timerfile'])
            logging.info(self.timerfile)


        #except:
        #    logging.error("Configuration error")

    def set_hw(self):  # OK
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
 
    def log_state(self):
        try:
            logging.info("Starting Logthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):

                logging.info("Sensor Values: " + str(self.sensor_values))
                logging.info("isTemp: " + str(self.isTemp))
                self.t_stop.wait(58)
                now = time.strftime('%Y-%m-%d %H:%M:%S')
                for idx in range(len(self.sensor_ids)):
                    if self.sensor_ids[idx].find("28-") == 0:
                        try:
                            self.sensor_values[idx] = self.w1.getValue(self.sensor_ids[idx])
                        except:
                            logging.info("Reading w1 sensor failed")
                for i in range(len(self.sensors)):
                    self.mysql_write(now, self.sensors[i], float(self.sensor_values[i]))
                for i in range(len(self.clients)):
                    #self.mysql_write(now, self.clients[i]+"Temp", self.isTemp[i])
                    if self.state[i] == "on":
                        self.mysql_write(now, self.clients[i], float(1))
                    else:
                        self.mysql_write(now, self.clients[i], float(0))
                #with open(self.logpath+"/Tempsensors.txt", "a") as templogfile:
                    #templogfile.write(now+",%6.2f" % self.w1.getValue(self.w1_slaves[0])+",%6.2f" %self.w1.getValue(self.w1_slaves[1]) + "\r\n" )
                if(self.pumpe > 0):
                    self.mysql_write(now, "ntPumpeDG", float(GPIO.input(self.pumpe)))
                    #self.mysql_write(now, "ntVorlaufDG", self.w1.getValue(self.w1_slaves[1]))
                            #self.mysql_write(now, self.sensors[idx], self.w1.getValue(self.sensor_ids[idx]))
            if self.t_stop.is_set():
                logging.info("Ausgeloggt!")
        except Exception as e:
            logging.error(e)

    def set_pumpe(self): #OK
        if(self.pumpe < 1):
            logging.info("Not starting Pumpenthread, no pump present")
            return
        try:
            logging.info("Starting Pumpenthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):
                # Checking, wether on of the room outputs is switches on -> if yes, switch pump on
                # First, Outputs are checked and their values are collected in state[]
                state = []
                for i in range(len(self.relais)):
                        for j in range(len(self.relais[i])):
                            state.append(GPIO.input(self.relais[i][j]))
                # Check, if any of the outputs is switched to on, if yes, activate pump
                if any(state) == self.on: 
                    if GPIO.input(self.pumpe) == self.off:
                        logging.info("Switching pump on")
                        GPIO.output(self.pumpe, self.on)
                else:
                    if GPIO.input(self.pumpe) == self.on:
                        logging.info("Switching pump off")
                    GPIO.output(self.pumpe, self.off)
                self.t_stop.wait(60)
                logging.info("Pumpenloop: Pumpe= "+ str(GPIO.input(self.pumpe)) + " State= " + str(state))
                pass
            if self.t_stop.is_set():
                logging.info("Ausgepumpt")
        except Exception as e:
            logging.error(e)

    def hw_state(self): #OK
        #logging.info("hw_state setting values " + str(self.state), logging)
        for client in self.clients:
            if self.clients[client]["Status"] == "on":
                val = self.on
            else:
                val = self.off
            for relais in self.clients[client]["Relais"]:
                GPIO.output(relais,val)
 
    def stop(self):
        self.t_stop.set()
        logging.info("Steuerung: So long sucker!")
        #print(threading.enumerate())
        exit()



    def run(self):
        while True:
            try:
                data, addr = self.e_udp_sock.recvfrom( 1024 )# Puffer-Groesse ist 1024 Bytes. 
                #print(addr)
                #print(data.decode('utf-8')) 
                msg = data.decode('utf-8')
                msg_spl = msg.split(",")
                if (msg_spl[0] in self.sensors) or (msg_spl[0] in self.clients):
                    logging.info(msg_spl[0]+": Soll-Temp: "+msg_spl[1]+" °C, Ist-Temp: "+msg_spl[2]+ "°C")
                    try:
                        idx = self.clients.index(msg_spl[0])
                        self.isTemp[idx] = msg_spl[2]
                        self.setTemp[idx] = msg_spl[1]
                        answer = 'Client OK'
                        #print(self.sensors)
                        #print(msg_spl[0])
                        for i in range(len(self.sensors)):
                            ind = self.sensors[i].find(msg_spl[0])
                            if ind == 0:
                                self.sensor_values[i] = msg_spl[2]
                        #if any(msg_spl[0] in s for s in self.sensors):
                        #print(s)
                        self.sensor_values[idx] = msg_spl[2]
                    except:
                        pass
                    try:
                        idx = self.sensors.index(msg_spl[0])
                        self.sensor_values[idx] = msg_spl[2]
                        #print(msg_spl[0])
                        #print(msg_spl[2])
                        answer = 'Sensor OK'
                    except:
                        pass


                else:
                    answer = 'Wrong Message'
                self.e_udp_sock.sendto(answer.encode('utf-8'), addr)
                #print(self.clientsi)
                #print("Aktuelle Temperaturen: ")
                #for i in self.isTemp:
                #    print(i)
                #print(self.setTemp)
                #for i in range(len(self.clients)):
                    #print(i)
                #    for j in range(len(self.relais[i])):
                #        if self.setTemp[i]<=self.isTemp[i]:
                #            #print(relais[i][j])
                #            GPIO.output(self.relais[i][j], 0)
                #        else:
                #            GPIO.output(self.relais[i][j], 1)
            except KeyboardInterrupt: # CTRL+C exiti
                logging.info("So long sucker!")
                for client in self.clients:
                    for j in self.clients[client]["Relais"]:
                        GPIO.output(j, self.off)
                        logging.info("Switching BMC " + str(j) + " off")
                if(self.pumpe > 0):
                    GPIO.output(self.pumpe, self.off)
                    logging.info("Switching BMC " + str(self.pumpe) + " off")
                #for i in range(len(self.rel)):
                #    GPIO.output(self.rel[i], 0)
                #    time.sleep(self.delay)
 
                GPIO.cleanup()
                self.t_stop.set()
                self.mysql_close()
                break

if __name__ == "__main__":
    steuerung = steuerung()
    steuerung.start()
    steuerung.run()
    steuerung.stop()
    

