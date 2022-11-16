from flask_restful import Resource
from flask import jsonify
import json

class Mode(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        #self.schema = kwargs['schema']


    def get(self, room):
        return json.loads(self.steuerung.get_room_status(room))

    def put(self, room):
        return json.loads(self.steuerung.toggle_room_mode(room))
