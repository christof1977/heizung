#!/usr/bin/env python3
import socket
import os
import RPi.GPIO as GPIO
import sys
import time
import configparser
from timer import timer
import syslog
from libby import tempsensors
import mysql.connector
import threading
from threading import Thread
from flask import Flask, render_template, request, jsonify
#import pins as Pins

settingsfile = 'heizungeg.ini' 


logging = True


def logger(msg):
    if logging == True:
        print(msg)
        syslog.syslog(str(msg))


class steuerung(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger("Starting Steuerungthread as " + threading.currentThread().getName())
        #super(steuerung, self).__init__()
        #print(threading.enumerate())
        #print("Initthread:")
        #print(threading.current_thread())
        self.t_stop = threading.Event()
        self.delay = .1

        self.read_config()

        self.sensor_values = [18.5]
        for i in range(len(self.sensors)-1):
                self.sensor_values.append(18.5)
        
        self.mysql_success = False
        self.mysql_start()

        logger("Starting UDP-Server at " + self.basehost + ":" + str(self.baseport))
        self.e_udp_sock = socket.socket( socket.AF_INET,  socket.SOCK_DGRAM ) 
        self.e_udp_sock.bind( (self.basehost,self.baseport) ) 
        
        #self.rel = [18, 27, 22, 23, 24, 10, 9, 25]
        self.set_hw()
        
        self.setTemp = [0]
        self.isTemp = [18]
        for i in range(len(self.clients)-1):
            self.setTemp.append(0)
            self.isTemp.append(18)
        #print(self.isTemp)
        self.w1 = tempsensors.onewires()
        self.w1_slaves = self.w1.enumerate()
        self.Timer = timer(self.clients, self.timerpath)
        self.timer_read()
        threading.Thread(target=self.set_pumpe).start()
        threading.Thread(target=self.log_state).start()
        threading.Thread(target=self.timer_operation).start()
        #threading.Thread(target=self.threadwatcher).start()
        #print(threading.enumerate())



    def threadwatcher(self):
        try:
            logger("Starting Threadwatcherthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):
                enum = threading.enumerate()
                for i in range(len(enum)):
                    logger("[Threadwatcher]: " + str(enum[i]))
                self.t_stop.wait(10)
            if self.t_stop.is_set():
                logger("Ausgewatcht")
        except Exception as e:
            logger(e)

    def mysql_start(self):
        self.mysql_success = False
        try:
            self.cnx = mysql.connector.connect(user=self.mysqluser, password=self.mysqlpass,host=self.mysqlserv,database=self.mysqldb)
            self.cursor = self.cnx.cursor()
            self.mysql_success = True
            logger("Database connection established")
        except Exception as e:
            try:
                self.mysql_success = False
                logger("Database connection error")
                self.cnx.disconnect()
            except Exception as e:
                pass



    def mysql_close(self):
        if self.mysql_success == True:
            self.cursor.close()

    def mysql_write(self, now, parameter, value):
        if self.mysql_success == True:
            #logger("Writing to DB")
            add = ("INSERT INTO messwert " 
                    "(datetime, parameter, value) "
                    "VALUES (%s, %s, %s)")
            #data = (time.strftime('%Y-%m-%d %H:%M:%S'), parameter, value)
            data = (now, parameter, value)
            try:
                self.cursor.execute(add, data)
                mess_id = self.cursor.lastrowid
                self.cnx.commit()
                return mess_id
            except Exception as e:
                logger("Fehler beim Schreiben in die Datenbank")
                self.mysql_start()
        else:
            self.mysql_start()



    def timer_read(self):
        self.Timer.read()

    def timer_operation(self):
        #try:
            logger("Starting Timeroperationthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):
                output = self.Timer.operate()
                for i in range(len(output)):
                    #print(output[i][0])
                    #print(output[i][1])
                    #print(output[i])

                    # original ohne Hysterese
                    #if float(output[i][1]) > float(self.isTemp[i]):  
                    #    #print("on")
                    #    self.state[i] = "on"
                    #else:
                    #    #print("off")
                    #    self.state[i] = "off"

                    if float(output[i][1]) - self.hysterese/2 >= float(self.isTemp[i]):  # mit Hysterese
                        self.state[i] = "on"
                    elif float(output[i][1]) + self.hysterese/2 <= float(self.isTemp[i]):  # mit Hysterese
                        self.state[i] = "off"
                logger("Timerloop: "+ str(self.state))
                self.hw_state()


                self.t_stop.wait(60)
            if self.t_stop.is_set():
                logger("Ausgetimed!")
        #except Exception as e:
        #    logger(e)



    def read_config(self):
        try:
            realpath = os.path.realpath(__file__)
            basepath = os.path.split(realpath)[0]
            setpath = os.path.join(basepath, 'settings')
            setfile = os.path.join(setpath, settingsfile)

            self.config = configparser.ConfigParser()
            logger("Loading " + setfile)
            self.config.read(setfile)
            self.basehost = self.config['BASE']['Host']
            self.baseport = int(self.config['BASE']['Port'])
            self.hysterese = float(self.config['BASE']['Hysterese'])
            self.clients = self.config['BASE']['Clients'].split(";")
            self.sensors = self.config['BASE']['Sensors'].split(";")
            self.sensor_ids = self.config['BASE']['Sensor_IDs'].split(";")
            self.pumpe = int(self.config['BASE']['Pumpe'])
            self.relais_tmp = self.config['BASE']['Relais'].split(";")
            self.relais = []
            for i in range(len(self.relais_tmp)):
                    tmp = (self.relais_tmp[i].split(","))
                    tmp1 = []
                    for j in range(len(tmp)):
                        tmp1.append(int(tmp[j]))
                    self.relais.append(tmp1)
            print(self.relais)
            self.polarity = self.config['BASE']['Polarity']
            self.unusedRel = self.config['BASE']['UnusedRel'].split(";")
            if self.polarity == "invers":
                self.on = 0
                self.off = 1
            else:
                self.on = 1
                self.off = 0
            self.state = []
            for i in range(len(self.clients)):
                self.state.append("off")
            self.logpath = os.path.join(basepath, 'log')
            self.timerpath = setpath
            self.mysqluser = self.config['BASE']['Mysqluser']
            self.mysqlpass = self.config['BASE']['Mysqlpass']
            self.mysqlserv = self.config['BASE']['Mysqlserv']
            self.mysqldb = self.config['BASE']['Mysqldb']

        except:
            logger("Configuration error")

    def set_hw(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        print(self.unusedRel)

        for i in self.unusedRel:
            i = int(i)
            print(i)
            GPIO.setup(i, GPIO.OUT)
            GPIO.output(i, self.off)
            logger("Setting BMC " + str(i) + " as unused -> off")
        for i in self.relais:
            for j in i:
                GPIO.setup(j, GPIO.OUT)
                GPIO.output(j, self.off)
                logger("Setting BMC " + str(j) + " as output")
        GPIO.setup(self.pumpe, GPIO.OUT)
        GPIO.output(self.pumpe, self.off)
        logger("Setting BMC " + str(self.pumpe) + " as output")
 
        
        

    def log_state(self):
        try:
            logger("Starting Logthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):

                print(self.sensor_values)
                print(self.isTemp)
                self.t_stop.wait(58)
                now = time.strftime('%Y-%m-%d %H:%M:%S')
                for idx in range(len(self.sensor_ids)):
                    if self.sensor_ids[idx].find("28-") == 0:
                        try:
                            self.sensor_values[idx] = self.w1.getValue(self.sensor_ids[idx])
                        except:
                            logger("Reading w1 sensor failed")
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
                self.mysql_write(now, "ntPumpeDG", float(GPIO.input(self.pumpe)))
                    #self.mysql_write(now, "ntVorlaufDG", self.w1.getValue(self.w1_slaves[1]))
                            #self.mysql_write(now, self.sensors[idx], self.w1.getValue(self.sensor_ids[idx]))
            if self.t_stop.is_set():
                logger("Ausgeloggt!")
        except Exception as e:
            logger(e)

    def set_pumpe(self):
        try:
            logger("Starting Pumpenthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):
                state = []
                for i in range(len(self.relais)):
                        for j in range(len(self.relais[i])):
                            #print(self.relais[i][j]
                            #print(self.relais[i][j])
                            state.append(GPIO.input(self.relais[i][j]))
                #print(state)
                #print(any(state))
                #print(state)
                if any(state) == self.on:
                    #print(self.pumpe)
                    if GPIO.input(self.pumpe) == self.off:
                        logger("Switching pump on")
                        GPIO.output(self.pumpe, self.on)
                else:
                    if GPIO.input(self.pumpe) == self.on:
                        logger("Switching pump off")
                    GPIO.output(self.pumpe, self.off)
                self.t_stop.wait(60)
                logger("Pumpenloop: Pumpe= "+ str(GPIO.input(self.pumpe)) + " State= " + str(state))
                pass
            if self.t_stop.is_set():
                logger("Ausgepumpt")
        except Exception as e:
            logger(e)

    def hw_state(self):
        logger("hw_state setting values " + str(self.state))
        for i in range(len(self.state)):
            if self.state[i] == "on":
                val = self.on
            else:
                val = self.off
            for j in range(len(self.relais[i])):
                GPIO.output(self.relais[i][j],val)
 

    def get_state(self):
        state = ""
        for i in range(len(self.clients)):
            state = state + " " + self.clients[i] + ":" + self.state[i] + ";"
        tmp = GPIO.input(self.pumpe)
        if tmp == 1:
            tmp = "on"
        else:
            tmp = "off"
        state = state + " Pumpe:" + tmp
        return state

    def get_temp(self):
        temp = ""
        #for i in range(len(self.clients)):
            #temp = temp + str(self.isTemp[i]) + ";"
        for i in range(len(self.sensor_values)):
            temp = temp + str(self.sensor_values[i]) + ";"
        return temp

    def set_state(self, room, state):
        try:
            room_idx = self.clients.index(room)
            logger("Setting room "+room+" "+state)
            self.state[room_idx] = state
            self.hw_state()
        except:
            logger("Error: No such room!")
            pass

    def stop(self):
        self.t_stop.set()
        logger("Steuerung: So long sucker!")
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
                    logger(msg_spl[0]+": Soll-Temp: "+msg_spl[1]+" °C, Ist-Temp: "+msg_spl[2]+ "°C")
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
                logger("So long sucker!")
                for i in self.relais:
                    for j in i:
                        GPIO.output(j, self.off)
                        logger("Switching BMC " + str(j) + " off")
                GPIO.output(self.pumpe, self.off)
                logger("Switching BMC " + str(self.pumpe) + " off")
                #for i in range(len(self.rel)):
                #    GPIO.output(self.rel[i], 0)
                #    time.sleep(self.delay)
 
                GPIO.cleanup()
                self.t_stop.set()
                self.mysql_close()
                break



app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
steuerung = steuerung()


# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return render_template("index.html")

@app.route("/timer")
def Timer():
    return render_template("timer.html")



@app.route("/_operate")
def operate():
    room = request.args.get('room')
    state = request.args.get('state')
    #print(room)
    #print(state)
    steuerung.set_state(room, state)
    return ""


@app.route("/_state")
def state():
    state=steuerung.get_state()
    temp=steuerung.get_temp()
    now=time.strftime("%H:%M:%S")
    return jsonify(heizungState=state,raumTemp=temp,rettime=now)

@app.route("/_gettime")
def gettime():
    rettime=now = str(time.time())
    return jsonify(rettime=rettime)


@app.route('/shutdown')
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

@app.route('/_reloadtimer')
def reload_timer():
    logger("Reload Timer")
    steuerung.timer_read()
    return "Timer reloaded"


def shutdown_server():
    #steuerung.stop()
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


if __name__ == "__main__":
    steuerung.start()
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    time.sleep(2)
    logger("Geschlafen")
    #print(threading.enumerate())
    steuerung.stop()
    #print(threading.enumerate())
    

