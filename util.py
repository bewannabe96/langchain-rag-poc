import json


def is_valid_json(input_string):
    try:
        json.loads(input_string)
    except ValueError:
        return False
    return True
