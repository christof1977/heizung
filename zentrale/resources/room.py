from flask_restful import Resource, request
from flask import jsonify
import json

class Roomlist(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']

    def get(self):
        return json.loads(self.steuerung.get_rooms())


class RoomMode(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        self.roomlist = json.loads(self.steuerung.get_rooms())["available_rooms"]

    def get(self, room):
        if room in self.roomlist:
            return json.loads(self.steuerung.get_room_mode(room))
        else:
            return {"answer": "getRoomMode", "error": "No such room"}

    def put(self, room):
        mode = request.args.get("mode") #retrieve args from query string
        if room in self.roomlist:
            if not mode:
                return json.loads(self.steuerung.toggle_room_mode(room))
            else:
                return json.loads(self.steuerung.set_room_mode(room, mode))

        else:
            return {"answer": "getRoomMode", "error": "No such room"}

class RoomTimer(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        self.roomlist = json.loads(self.steuerung.get_rooms())["available_rooms"]

    def get(self, room):
        if room in self.roomlist:
            return json.loads(self.steuerung.get_room_timer(room))
        else:
            return {"answer": "getRoomMode", "error": "No such room"}

    def put(self, room):
        if room in self.roomlist:
            return json.loads(self.steuerung.set_room_timer(room))
        else:
            return {"answer": "getRoomMode", "error": "No such room"}

class RoomShortTimer(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        self.roomlist = json.loads(self.steuerung.get_rooms())["available_rooms"]

    def get(self, room):
        if room in self.roomlist:
            return json.loads(self.steuerung.get_room_shorttimer(room))
        else:
            return {"answer": "RoomShortTimer", "error": "No such room"}

    def put(self, room):
        action = request.args.get("action") #retrieve args from query string
        time = request.args.get("time") #retrieve args from query string
        mode = request.args.get("mode") #retrieve args from query string

        if room in self.roomlist:
            if action == "reset":
                return json.loads(self.steuerung.reset_room_shorttimer(room))
            elif action == "set":
                return json.loads(self.steuerung.set_room_shorttimer(room, time, mode))
            else:
                return {"answer": "RoomShortTimer", "error": "No such action"}
        else:
            return {"answer": "RoomShortTimer", "error": "No such room"}

class RoomNormTemp(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        self.roomlist = json.loads(self.steuerung.get_rooms())["available_rooms"]

    def get(self, room):
        if room in self.roomlist:
            return json.loads(self.steuerung.get_room_norm_temp(room))
        else:
            return {"answer": "RoomNormTemp", "error": "No such room"}

    def put(self, room):
        temp = request.args.get("temp") #retrieve args from query string
        if room in self.roomlist:
            return json.loads(self.steuerung.set_room_norm_temp(room, temp))
        else:
            return {"answer": "RoomNormTemp", "error": "No such room"}

class Timer(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        self.roomlist = json.loads(self.steuerung.get_rooms())["available_rooms"]

    def get(self):
        return json.loads(self.steuerung.get_timer())

    def put(self):
        action = request.args.get("action") #retrieve args from query string
        if action == "reload":
            return json.loads(self.steuerung.reload_timer())
        else:
            return {"answer": "reloadTimer", "error": "No such action"}


