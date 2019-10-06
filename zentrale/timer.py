#!/usr/bin/env python3

import time
import datetime
import csv
import os
import json

#TODO


class timer(object):
    pass

    def __init__(self, jsonfile):
        #self.clients = clients
        #self.path = path
        self.tl = self.read_json(jsonfile)

    def read_json(self, jsonfile):
        with open (jsonfile,"r") as fhd:
            data = json.load(fhd)
        return(data)

    def check_room(self, room):
        if(room in self.get_rooms()):
            ret = True
        else:
            ret = False
        return(ret)
        
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
        if not self.check_room(room):
            return(-1)
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

    def get_recent_set(self, room):
        if not self.check_room(room):
            return(-1)
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
       
    #clients = ["K", "BadEG", "WZ", "SZ", "AZ"]
    jsonfile = "settings/_timer.json"
    Timer = timer(jsonfile)
    rooms = Timer.get_rooms()
    room = "WZ"
    #Timer.check_room(room)

    timer_list = Timer.get_timer_list(room)
    print(timer_list)
    print(Timer.get_recent_set(room))

if __name__ == "__main__":
    main()
