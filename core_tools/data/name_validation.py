import re

def validate_dataset_name(name):
    if len(name) < 2:
        raise Exception(f"Dataset name {name} is too short. Min length is 2 chars")
    if len(name) > 100:
        raise Exception("Dataset name is too long. Max is 100")
    if '{' in name:
        raise Exception(f"Illegal name. Did you forget the f in front of the string? {name}")
    if not re.match(r"^[A-Za-z0-9_\-.,:()[\]*+&/ ]*$", name):
        raise Exception(f"Invalid dataset name {name}")

def validate_data_identifier_value(value):
    if len(value) < 1:
        raise Exception(f"Name {value} is too short. ")
    if len(value) > 30:
        raise Exception("Name {value} is too long. Max is 25")
    if '{' in value:
        raise Exception(f"Illegal name. Did you forget the f in front of the string? {value}")
    if not re.match(r"^[A-Za-z][A-Za-z0-9_\-.,:()[\]* ]*$", value):
        raise Exception(f"Invalid name {value}")

def validate_param_name(value):
    return validate_data_identifier_value(value)
