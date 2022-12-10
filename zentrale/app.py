#!/usr/bin/env python3

import threading
from flask import Flask
from flask import request
from flask_restful import Api
from flask_restful import Resource, abort
from steuerung import steuerung
from flaskext.markdown import Markdown
#from marshmallow import Schema, fields

from resources.status import Status, Alive, HelpJsonCommands, HelpApi
from resources.room import Roomlist, RoomMode, RoomInfo, RoomStatus, RoomTimer, RoomShortTimer, RoomTemp, RoomNormTemp, Timer

#class StatusSchema(Schema):
#    room = fields.Str(required=False)

host_name = "0.0.0.0"
port = 5000 
app = Flask(__name__)
api = Api(app)
Markdown(app)

#status_schema = StatusSchema()

steuerung = steuerung()
api.add_resource(Alive, '/', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(Status, '/status', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(HelpJsonCommands, '/help', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(HelpApi, '/restapi', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(Roomlist, '/room', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(RoomInfo, '/room/<string:room>', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(RoomStatus, '/room/<string:room>/status', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(RoomMode, '/room/<string:room>/mode', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(RoomTimer, '/room/<string:room>/timer', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(RoomShortTimer, '/room/<string:room>/shorttimer', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(RoomTemp, '/room/<string:room>/temp', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(RoomNormTemp, '/room/<string:room>/settemp', resource_class_kwargs={'steuerung': steuerung})
api.add_resource(Timer, '/timer', resource_class_kwargs={'steuerung': steuerung})

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host=host_name, port=port, debug=True, use_reloader=False)).start()
    steuerung.run()
    

