import os as _os
import json as _json

def get_key(jsonfile="conf.json", default = "SharderAPI-PVT-0000"):
    try:
        return _os.environ["PASSWORD"]
    except KeyError:
        try:
            with open(jsonfile, "r") as reader:
                return _json.load(reader)["PASSWORD"]
        except FileNotFoundError:
            return default
