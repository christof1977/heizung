#!/usr/bin/env python3

import time
import datetime
import csv
import os
import json

def read_config():
    import configparser
    config = configparser.ConfigParser()
    config.read('/home/heizung/heizung/zentrale/settings/heizung.ini')
    clients = config['BASE']['Clients'].split(";")
    path = config['BASE']['Path']
    timerpath = path+"/settings/"
    return clients, timerpath


class timer(object):
    pass

    def __init__(self, jsonfile, clients, path):
        self.clients = clients
        self.path = path
        self.tl = self.read_json(jsonfile)

    def read_json(self, jsonfile):
        with open (jsonfile,"r") as fhd:
            data = json.load(fhd)
        return(data)
        

    def read(self):
        #import csv
        self.times = [[] for i in range(len(self.clients))]
        self.states = [[] for i in range(len(self.clients))]
        cl_idx = 0
        for client in self.clients:
            filename = os.path.join(self.path, client + ".csv")
            try:
                with open(filename, newline='') as csvfile:
                    reader = csv.reader(csvfile, delimiter=',')
                    for row in reader:
                        self.times[cl_idx].append(row[0])
                        self.states[cl_idx].append(row[1])
                #print(self.times[cl_idx])
                #print(self.states[cl_idx])
                cl_idx += 1
            except:
                print("Error")


        #print(self.times)
        #print(self.states)
        #print(now)
        return self.times, self.states

    def show(self):
        i = 0
        for client in self.clients:
            print(client)
            n = 0
            for j in self.times[i]:
                print(j + " -> " + self.states[i][n])
                n += 1
            print("")
            i += 1


    def operate(self):
        #import time
        output=[]
        now=time.strftime("%H:%M")
        for i in range(len(self.clients)):
            for j in range(len(self.times[i])):
                if now < self.times[i][j]:
                    idx = j - 1
                    break
                idx = j
            output.append([(self.clients[i]), (self.states[i][idx])])
        return output

    def get_day_list(self, dayrange):
        days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        dow = []
        sep = dayrange.find("-")
        if(sep == -1):
            sep = dayrange.find(",")
            if(sep == -1): # Single day in list
                for d in dayrange.split(","):
                    dow.append(days.index(d))
            else: # List of comma separated days
                for d in dayrange.split(","):
                    dow.append(days.index(d))
        else: # Range between two days, seperated by "-"
            tmpdow = []
            for d in dayrange.split("-"):
                tmpdow.append(days.index(d))
            dow = []
            if(len(tmpdow)!=2):
                print("Error, using first and last day")
                dow.append(tmp[0])
                dow.append(tmp[len(tmp)-1])
            else:
                for i in range(tmpdow[0], tmpdow[1]+1):
                    dow.append(i)
        return(dow)

    def get_rooms(self):
        return(self.tl.keys())

    def get_timer_list(self, room):
        timer_list = {}
        for dayrange in self.tl[room]["settings"].keys():
            dow = self.get_day_list(dayrange)
            times = self.tl[room]["settings"][dayrange]
            times_sorted = sorted(times,key=lambda x : time.strptime(x,"%H:%M"))
            temps = []
            for t in times_sorted:
                temps.append(times[t])
            for d in dow:
                timer_list[d] = [times_sorted,temps]
        return(timer_list)

    def get_recent_temp(self, room):
        now = datetime.datetime.now()
        timer_list = self.get_timer_list(room)
        day = datetime.datetime.today().weekday()
        timer_list[day]
        temp = None
        for j in range(len(timer_list[day][0])):
            datestring = str(now.year) + "-" + str(now.month) + "-" + str(now.day) + " " + timer_list[day][0][j]
            d=datetime.datetime.strptime(datestring,'%Y-%m-%d %H:%M')
            if now > d:
                temp = timer_list[day][1][j]
        if(temp is None):
            temp = timer_list[day][1][-1]
        return(temp)

def main():
       
    clients = ["K", "BadEG", "WZ", "SZ", "AZ"]
    jsonfile = "settings/timer.json"
    #print(clients)
    #print(timerpath)
    Timer = timer(jsonfile, clients, "settings/")
    #times, states = Timer.read()
    rooms = Timer.get_rooms()
    room = "WZ"

    #timer_list = Timer.get_timer_list(room)
    print(Timer.get_recent_temp(room))


    #print(states)
    #Timer.show()
    #output = Timer.operate()
    #print(output)


if __name__ == "__main__":
    main()
