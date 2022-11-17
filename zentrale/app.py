#!/usr/bin/env python3

import threading
from flask import Flask
from flask import request
from flask_restful import Api
from flask_restful import Resource, abort
from steuerung import steuerung
#from marshmallow import Schema, fields

from resources.status import Status
from resources.status import Alive
from resources.room import Roomlist
from resources.room import Mode

#class StatusSchema(Schema):
#    room = fields.Str(required=False)

host_name = "0.0.0.0"
port = 5000 
app = Flask(__name__)
api = Api(app)


#status_schema = StatusSchema()


if __name__ == "__main__":
    steuerung = steuerung()
    api.add_resource(Alive, '/', resource_class_kwargs={'steuerung': steuerung})
    api.add_resource(Status, '/status', resource_class_kwargs={'steuerung': steuerung})
    api.add_resource(Roomlist, '/room', resource_class_kwargs={'steuerung': steuerung})
    api.add_resource(Mode, '/room/<string:room>', resource_class_kwargs={'steuerung': steuerung})
    threading.Thread(target=lambda: app.run(host=host_name, port=port, debug=True, use_reloader=False)).start()
    steuerung.run()
    

