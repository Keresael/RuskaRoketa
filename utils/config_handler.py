import configparser

def create_config():
    config = configparser.ConfigParser()
    config.read('config.ini')

    config["Settings"] = {
        "Ign": "",
        "Tag": "",
        "Region": "",
        "Brodcaster": ""
    }

    with open('../config.ini', 'w') as configfile:
         config.write(configfile)

def get_config(section, value) -> str:
    config = configparser.ConfigParser()
    config.read('config.ini')
    if not config.has_section(section):
        create_config()
    return config.get(section, value)