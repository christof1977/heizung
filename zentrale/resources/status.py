from flask_restful import Resource, request
from flask import jsonify
import json
import markdown
import markdown.extensions.fenced_code
from flask import render_template, make_response

class Alive(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']

    def get(self):
        return json.loads(self.steuerung.get_alive())


class Status(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']
        self.roomlist = self.get_rooms()

    def get_rooms(self):
        ret = json.loads(self.steuerung.get_rooms())
        return ret["available_rooms"]

    def get(self):
        room = request.args.get("room") #retrieve args from query string
        if room and room in self.roomlist:
            return json.loads(self.steuerung.get_room_status(room))
        else:
            return json.loads(self.steuerung.get_status())


class HelpJsonCommands(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']

    def get(self):
        readme_file = open("steuerung.md", "r")
        md_template_string = markdown.markdown(readme_file.read(), extensions=["fenced_code"])
        headers = {'Content-Type': 'text/html'}
        return make_response(md_template_string,200,headers)

class HelpApi(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']

    def get(self):
        readme_file = open("restapi.md", "r")
        md_template_string = markdown.markdown(readme_file.read(), extensions=["fenced_code"])
        headers = {'Content-Type': 'text/html'}
        return make_response(md_template_string,200,headers)

class Mixer(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']

    def get(self):
        avail = json.loads(self.steuerung.get_mixer())
        running = json.loads(self.steuerung.mixer_running())
        ff_is_temp = json.loads(self.steuerung.get_ff_is_temp())
        ff_set_temp = json.loads(self.steuerung.get_ff_set_temp())
        if(avail["answer"]=="available"):
            ret = {"mixer":{"available":avail["answer"], "running":running["answer"], "ff_set_temp": ff_set_temp["answer"], "ff_is_temp": ff_is_temp["answer"]}}
        else:
            ret = {"mixer":{"available":avail["answer"]}}
        return(ret)

class FfSetTemp(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']

    def get(self):
        return json.loads(self.steuerung.get_ff_set_temp())

class FfIsTemp(Resource):
    def __init__(self, **kwargs):
        self.steuerung = kwargs['steuerung']

    def get(self):
        return json.loads(self.steuerung.get_ff_is_temp())

