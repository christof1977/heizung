#!/usr/bin/env python3
#import socket
#import RPi.GPIO as GPIO
import sys
import time
#import configparser
#from timer import timer
import syslog
from libby import tempsensors
import mysql.connector
import threading
from threading import Thread
from flask import Flask, render_template, request, jsonify
#import pins as Pins

logging = True


def logger(msg):
    if logging == True:
        print(msg)
        syslog.syslog(str(msg))


class templogger(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.t_stop = threading.Event()
        self.mysqluser = "heizung"
        self.mysqlpass = "heizung"
        self.mysqlserv = "dose.fritz.box"
        self.mysqldb = "heizung"
        self.sensor_ids = [ "28-0316a1845fff", "28-0416b3ea69ff", "28-0316b46b6bff", "28-0416c02796ff" ]
        self.sensors = [ "kVorlauf", "kRuecklauf", "speicherRuecklauf", "speicherVorlauf" ]

        self.mysql_start()
        self.w1 = tempsensors.onewires()

        threading.Thread(target=self.log_temp).start()
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



    def log_temp(self):
        try:
            logger("Starting Logthread as " + threading.currentThread().getName())
            while(not self.t_stop.is_set()):

                self.t_stop.wait(58)
                now = time.strftime('%Y-%m-%d %H:%M:%S')
                
                for i in range(len(self.sensor_ids)):
                    #print(now + self.sensors[i] + "             "  + str(self.w1.getValue(self.sensor_ids[i])))
                    time.sleep(.2)
                    temp = float(self.w1.getValue(self.sensor_ids[i]))
                    if temp != 85:
                        self.mysql_write(now, self.sensors[i], temp)
                #print(" ")
            if self.t_stop.is_set():
                logger("Ausgeloggt!")
        except Exception as e:
            logger(e)




    def get_temp(self):
        temps = []
        names = []
        for i in range(len(self.sensor_ids)):
            temps.append(self.w1.getValue(self.sensor_ids[i]))
            names.append(self.sensors[i])
        return temps, names


    def stop(self):
        self.t_stop.set()
        logger("Temploggerthread: So long sucker!")
        #print(threading.enumerate())
        exit()



    def run(self):
        while True:
            try:
                pass
                time.sleep(1)
            except KeyboardInterrupt: # CTRL+C exiti
                logger("So long sucker!")
 
                self.t_stop.set()
                self.mysql_close()
                break



app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
templogger = templogger()


# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return render_template("index.html")

@app.route("/_gettemp")
def gettemp():
    temps, names = templogger.get_temp()
    print(temps)
    print(names)
    rettime = time.strftime("%H:%M:%S")
    return jsonify(temps=temps, names=names, rettime=rettime)




@app.route("/_gettime")
def gettime():
    rettime = str(time.time())
    return jsonify(rettime=rettime)


@app.route('/shutdown')
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


def shutdown_server():
    #steuerung.stop()
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


if __name__ == "__main__":
    templogger.start()
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    logger("Geschlafen wird!")
    templogger.stop()
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

    

