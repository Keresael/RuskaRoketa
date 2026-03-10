import configparser

file_path = '../config.ini'

def create_config():
    config = configparser.ConfigParser()
    files_read = config.read(file_path)

    if not files_read:
        with open(file_path, 'w') as configfile:
            pass

    config["Details"] = {
        "Riot_Ign": "Deidxra",
        "Riot_Tag": "666",
        "Riot_Region": "EUW",
        "Riot_Server": "Europe",
        "LolPros_Name": "Deidara",
        "Twitch_Brodcaster": "Deidxraa"
    }

    with open(file_path, 'w') as configfile:
         config.write(configfile)

def get_config(section, value) -> str:
    config = configparser.ConfigParser()
    config.read(file_path)
    if not config.has_section(section):
        create_config()
    return config.get(section, value)

if __name__ == "main":
   create_config()