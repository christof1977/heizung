from flask_restful import Resource
from flask import jsonify, request
import json

class Status(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        #self.schema = kwargs['schema']

    def get(self):
        #print(self.schema.validate(request.args))
        return json.loads(self.steuerung.get_status())
