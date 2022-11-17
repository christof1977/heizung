from flask_restful import Resource
from flask import jsonify
import json

class Roomlist(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']

    def get(self):
        return json.loads(self.steuerung.get_rooms())


class Mode(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        self.roomlist = json.loads(self.steuerung.get_rooms())["available_rooms"]

    def get(self, room):
        if room in self.roomlist:
            return json.loads(self.steuerung.get_room_mode(room))
        else:
            return {"answer": "getRoomMode", "error": "No such room"}

    def put(self, room):
        return json.loads(self.steuerung.toggle_room_mode(room))
