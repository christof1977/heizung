from flask_restful import Resource, request
from flask import jsonify
import json

class Alive(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']

    def get(self):
        return json.loads(self.steuerung.get_alive())


class Status(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        self.rooms = self.get_rooms()

    def get_rooms(self):
        ret = json.loads(self.steuerung.get_rooms())
        return ret["available_rooms"]

    def get(self):
        room = request.args.get("room") #retrieve args from query string
        if room and room in self.rooms:
            return json.loads(self.steuerung.get_room_status(room))
        else:
            return json.loads(self.steuerung.get_status())
