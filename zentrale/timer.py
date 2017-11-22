#!/usr/bin/env python3

import time
import csv

def read_config():
    import configparser
    config = configparser.ConfigParser()
    config.read('/home/heizung/heizung/zentrale/settings/heizung.ini')
    basehost = config['BASE']['Host']
    baseport = int(config['BASE']['Port'])
    clients = config['BASE']['Clients'].split(";")
    path = config['BASE']['Path']
    logpath = path+"/log/"
    timerpath = path+"/settings/"
    return clients, timerpath


class timer(object):
    pass

    def __init__(self, clients, path):
        self.clients = clients
        self.path = path
        

    def read(self):
        #import csv
        self.times = [[] for i in range(len(self.clients))]
        self.states = [[] for i in range(len(self.clients))]
        cl_idx = 0
        for client in self.clients:
            filename = self.path + client + ".csv"
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




def main():
    #import time
    #import csv
       
    clients, timerpath = read_config()
    #print(clients)
    #print(timerpath)
    Timer = timer(clients,timerpath)
    times, states = Timer.read()
    #print(times)
    #print(states)
    #Timer.show()
    output = Timer.operate()
    print(output)


if __name__ == "__main__":
    main()
