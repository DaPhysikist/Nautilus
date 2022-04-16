import threading
import os
from api import Radio
import constants
# determines if connected to BS
connected = False

# Determines if AUV threads should be stopped / restarted
stop_all_threads = False
restart_threads = False

depth_offset = 0

radio = None


def path_existance(radioPaths):
    for rp in radioPaths:
        if os.path.exists(rp['path']):
            return True
    return False


def connect_to_radio():
    for rp in constants.RADIO_PATHS:
        try:
            radio = Radio(rp['path'])
            print("Successfully found radio device on ", rp['radioNum'])
        except:
            print("Warning: Cannot find radio device on ", rp['radioNum'], "Trying next radiopath...")


def log(val):
    print("[AUV]\t" + val)
