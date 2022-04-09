'''
This class acts as the main functionality file for
the Nautilus AUV. The "mind and brain" of the mission.
'''
# System imports
import os
import sys
import threading
import time
import math

# Custom imports
from queue import Queue
from api import Radio
from api import IMU
from api import Crc32
from api import PressureSensor
from api import MotorController
from api import MotorQueue
from missions import *

from static import global_vars

from threads.auv_send_data import AUV_Send_Data
from threads.auv_send_ping import AUV_Send_Ping
from threads.auv_receive import AUV_Receive

from static import constants
from static import global_vars


def threads_active(ts):
    for t in ts:
        if t.is_alive():
            return True
    return False


def stop_threads(ts):
    for t in ts:
        t.stop()


def start_threads(ts, queue, halt):
    # Initialize hardware
    try:
        pressure_sensor = PressureSensor()
        pressure_sensor.init()
        global_vars.log("Pressure sensor has been found")
    except:
        global_vars.log("Pressure sensor is not connected to the AUV.")

    try:
        imu = IMU.BNO055(serial_port=constants.IMU_PATH, rst=18)

        global_vars.log("IMU has been found.")
    except:
        global_vars.log("IMU is not connected to the AUV on IMU_PATH.")

    for rp in constants.RADIO_PATHS:
        try:
            global_vars.radio = Radio(rp['path'])
            global_vars.log(f"Successfully found radio device on {rp['radioNum']}.")
        except:
            global_vars.log(f"Warning: Cannot find radio device on {rp['radioNum']}. Trying next radiopath...")

    mc = MotorController()

    auv_motor_thread = MotorQueue(queue, halt)
    auv_r_thread = AUV_Receive(queue, halt, global_vars.radio, pressure_sensor, imu, mc)

    ts = []

    auv_s_thread = AUV_Send_Data(global_vars.radio, pressure_sensor, imu, mc)
    auv_ping_thread = AUV_Send_Ping(global_vars.radio)

    ts.append(auv_motor_thread)
    ts.append(auv_r_thread)
    ts.append(auv_s_thread)
    ts.append(auv_ping_thread)

    auv_motor_thread.start()
    auv_r_thread.start()
    auv_s_thread.start()
    auv_ping_thread.start()


if __name__ == '__main__':  # If we are executing this file as main
    queue = Queue()
    halt = [False]

    ts = []

    start_threads(ts, queue, halt)

    try:
        while threads_active(ts):
            if global_vars.stop_all_threads:
                global_vars.stop_all_threads = False
                stop_threads(ts)

            if global_vars.restart_threads:
                global_vars.restart_threads = False
                stop_threads(ts)

                # Reinitialize and restart all threads
                queue = Queue()
                halt = [False]
                ts = []

                start_threads(ts, queue, halt)

            time.sleep(1)
    except KeyboardInterrupt:
        # kill threads
        for t in ts:
            t.stop()

    print("waiting to stop")
    while threads_active(ts):
        time.sleep(0.1)
    print('done')
