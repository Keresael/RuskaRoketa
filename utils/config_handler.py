import configparser
from os import write


def create_config():
    config = configparser.ConfigParser()
    file_path = '../config.ini'
    files_read = config.read(file_path)

    if not files_read:
        with open(file_path, 'w') as configfile:
            pass

    config["Details"] = {
        "Riot_Ign": "Deidxra",
        "Riot_Tag": "666",
        "Riot_Region": "EUW",
        "Twitch_Brodcaster": "Deidxraa"
    }

    with open(file_path, 'w') as configfile:
         config.write(configfile)

def get_config(section, value) -> str:
    config = configparser.ConfigParser()
    config.read('config.ini')
    if not config.has_section(section):
        create_config()
    return config.get(section, value)

if __name__ == "main":
   create_config()