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
from api import Radio
from api import IMU
from api import PressureSensor
from api import MotorController
from missions import *

# Constants for the AUV
RADIO_PATH = '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'
IMU_PATH = '/dev/serial0'
PING = 0xFF
THREAD_SLEEP_DELAY = 0.05
CONNECTION_TIMEOUT = 3

# Encoding headers
POSITION_DATA = 0b10000
HEADING_DATA = 0b10001
VOLTAGE_DATA = 0b10010
TEMP_DATA = 0b10011
MOVEMENT_STAT_DATA = 0b10100
MISSION_STAT_DATA = 0b10101
FLOODED_DATA = 0b10110
DEPTH_DATA = 0b10111
WATER_DEPTH_DATA = 0

DEPTH_ENCODE = DEPTH_DATA << 11 

MAX_TIME = 600
MAX_ITERATION_COUNT = MAX_TIME / THREAD_SLEEP_DELAY / 7


def log(val):
    print("[AUV]\t" + val)


class AUV():
    """ Class for the AUV object. Acts as the main file for the AUV. """

    def __init__(self):
        """ Constructor for the AUV """
        self.radio = None
        self.pressure_sensor = None
        self.imu = None
        self.mc = MotorController()
        self.connected_to_bs = False
        self.time_since_last_ping = 0.0
        self.current_mission = None
        self.timer = 0

        # Get all non-default callable methods in this class
        self.methods = [m for m in dir(AUV) if not m.startswith('__')]

        try:
            self.pressure_sensor = PressureSensor()
            self.pressure_sensor.init()
            log("Pressure sensor has been found")
        except:
            log("Pressure sensor is not connected to the AUV.")

        try:
            self.imu = IMU(IMU_PATH)
            log("IMU has been found.")
        except:
            log("IMU is not connected to the AUV on IMU_PATH.")

        try:
            self.radio = Radio(RADIO_PATH)
            log("Radio device has been found.")
        except:
            log("Radio device is not connected to AUV on RADIO_PATH.")

        self.main_loop()

    def x(self, data):
        self.mc.update_motor_speeds(data)

    def test_motor(self, motor):
        """ Method to test all 4 motors on the AUV """

        if motor == "FORWARD":  # Used to be LEFT motor
            self.mc.test_forward()
        elif motor == "TURN":  # Used to be RIGHT MOTOR
            self.mc.test_turn()
        elif motor == "FRONT":
            self.mc.test_front()
        elif motor == "BACK":
            self.mc.test_back()
        elif motor == "ALL":
            self.mc.test_all()
        else:
            raise Exception('No implementation for motor name: ', motor)

    def run_motors(self, x, y):
        # stops auv
        self.mc.zero_out_motors()

        forward_speed = 0
        turn_speed = 0

        # turn right
        if (y > 0):
            turn_speed = 90
        # turn left
        elif (y < 0):
            turn_speed = -90

        # turn auv
        self.mc.update_motor_speeds([0, turn_speed, 0, 0])

        # TODO implement so motors run until we've turned y degrees

        time.sleep(5)

        self.mc.zero_out_motors()

        # move forward
        if (x != 0):
            forward_speed = 90
            self.mc.update_motor_speeds([forward_speed, 0, 0, 0])

            # TODO implement so motors run until we've moved x meters
            time.sleep(5)

        self.mc.zero_out_motors()

    def main_loop(self):
        """ Main connection loop for the AUV. """

        log("Starting main connection loop.")
        while True:

            # Always try to update connection status.
            if time.time() - self.time_since_last_ping > CONNECTION_TIMEOUT:
                # Line read was EMPTY, but 'before' connection status was successful? Connection verification failed.
                if self.connected_to_bs is True:
                    log("Lost connection to BS.")

                    # reset motor speed to 0 immediately and flush buffer
                    self.mc.update_motor_speeds([0, 0, 0, 0])
                    log("DEBUG TODO speeds reset")

                    # enforce check in case radio is not found
                    if self.radio is not None:
                        self.radio.flush()

                    self.connected_to_bs = False

            if self.radio is None or self.radio.is_open() is False:
                try:  # Try to connect to our devices.
                    self.radio = Radio(RADIO_PATH)
                    log("Radio device has been found!")
                except:
                    pass
            else:
                try:
                    # Always send a connection verification packet and attempt to read one.
                    # self.radio.write(AUV_PING)
                    self.radio.write(0xFF, 1)

                    if self.connected_to_bs is True:  # Send our AUV packet as well.

                        # TODO Data sending logic
                        #
                        # if (sending_data):
                        #    if(data.read(500000) != EOF)
                        #        send("d("+data.nextBytes+")")
                        #    else:
                        #        send("d_done()")
                        #        sending_data = False

                        # TODO default values in case we could not read anything
                        heading = 0
                        temperature = 0
                        pressure = 0

                        if self.imu is not None:
                            try:
                                #heading = self.imu.quaternion[0]
                                compass = self.imu.magnetic
                                if compass is not None:
                                    heading = math.degrees(math.atan2(compass[1], compass[0]))

                                    # heading = round(
                                    #    abs(heading * 360) * 100.0) / 100.0

                                temperature = self.imu.temperature
                                # (Heading, Temperature)
                                if temperature is not None:
                                    temperature = str(temperature)
                                else:
                                    temperature = 0

                            except:
                                # TODO print statement, something went wrong!
                                heading = 0
                                temperature = 0
                                #self.radio.write(str.encode("log(\"[AUV]\tAn error occurred while trying to read heading and temperature.\")\n"))

                        if self.pressure_sensor is not None:
                            self.pressure_sensor.read()

                            # defaults to mbars
                            pressure = self.pressure_sensor.pressure()
                            mbar_to_depth = (pressure-1013.25)/1000 * 10.2
                            if mbar_to_depth < 0:
                                mbar_to_depth = 0
                            for_depth = math.modf(mbar_to_depth)
                            # standard depth of 10.2
                            y = int(round(for_depth[0],1) * 10)
                            x = int(for_depth[1])
                            x = x << 4
                            depth_encode = (DEPTH_ENCODE | x | y)
                            log("Pressure Read: " + str(self.pressure_sensor.pressure())
                                + ", x: " + str((x >> 4)) + ", y: " + str(y))  # TODO Heading and temperature


                            #conversion for bars
                            WATER_DEPTH_DATA = pressure * 10.2

                            self.radio.write(depth_encode, 2)



                    # Read three bytes
                    line = self.radio.read(3)
                    print("Line read ", line)
                    # self.radio.flush()

                    while(line != b'' and len(line) == 3):

                        if int.from_bytes(line, "big") == 0xFFFFFF:  # We have a ping!
                            self.time_since_last_ping = time.time()
                            if self.connected_to_bs is False:
                                log("Connection to BS verified.")
                                self.connected_to_bs = True

                                # TODO test case: set motor speeds
                                data = [1, 2, 3, 4]
                                self.x(data)

                        else:
                            # Line was read, but it was not equal to a BS_PING

                            # Decode into a normal utd-8 encoded string and delete newline character
                            #message = line.decode('utf-8').replace("\n", "")
                            print(line)
                            message = int.from_bytes(line, "big")
                            log("Possible command found. Line read was: " + str(message))
                            print(type(message))
                            message = int(message)
                            # 0000001XSY or 0000000X

                            # navigation command
                            if (message & 0x020000 > 0):
                                x = (message & 0x01F600) >> 9
                                sign = (message & 0x000100) >> 8
                                y = (message & 0x0000FF)

                                if (sign == 1):
                                    y = y * -1

                                log("Running motor command with (x, y): " + str(x) + "," + str(y))
                                self.run_motors(x, y)

                            # misison command
                            else:
                                # TODO
                                x = (message & 0x3)
                                log("Start Command Run with (x): " + str(x))
                                self.start_mission(x)

                                # if len(message) > 2 and "(" in message and ")" in message:
                                #     # Get possible function name
                                #     possible_func_name = message[0:message.find(
                                #         "(")]

                                #     if possible_func_name in self.methods:
                                #         log(
                                #             "Recieved command from base station: " + message)
                                #         self.time_since_last_ping = time.time()
                                #         self.connected_to_bs = True

                                #         try:  # Attempt to evaluate command.
                                #             # Append "self." to all commands.
                                #             eval('self.' + message)
                                #             #self.radio.write(str.encode("log(\"[AUV]\tSuccessfully evaluated command: " + possible_func_name + "()\")\n"))
                                #         except Exception as e:
                                #             # log error message
                                #             log(str(e))
                                #             # Send verification of command back to base station.
                                #             self.radio.write(str.encode("log(\"[AUV]\tEvaluation of command " +
                                #                                         possible_func_name + "() failed.\")\n"))

                        line = self.radio.read(3)

                    # end while
                    self.radio.flush()

                except Exception as e:
                    log("Error: " + str(e))
                    self.radio.close()
                    self.radio = None
                    log("Radio is disconnected from pi!")
                    continue

            if(self.current_mission is not None):
                print(self.timer)
                self.current_mission.loop()

                # TODO statements because max time received
                self.timer = self.timer + 1
                if self.timer > MAX_ITERATION_COUNT:
                    # kill mission, we exceeded time
                    self.abort_mission()

            time.sleep(THREAD_SLEEP_DELAY)

    def start_mission(self, mission):
        """ Method that uses the mission selected and begin that mission """
        if(mission == 0):  # Echo-location.
            try:  # Try to start mission
                self.current_mission = Mission1(
                    self, self.mc, self.pressure_sensor, self.imu)
                self.timer = 0
                log("Successfully started mission " + str(mission) + ".")
                #self.radio.write(str.encode("mission_started("+str(mission)+")\n"))
            except Exception as e:
                raise Exception("Mission " + str(mission) +
                                " failed to start. Error: " + str(e))
        # elif(mission == 2):
        #     self.current_mission = Mission2()
        # if self.current_mission is None:
        #     self.current_mission = Mission1()

    def d_data(self):
        # TODO Set sending data flag
        # self.sending_data = true
        pass

    def abort_mission(self):
        aborted_mission = self.current_mission
        self.current_mission = None
        aborted_mission.abort_loop()
        log("Successfully aborted the current mission.")
        #self.radio.write(str.encode("mission_failed()\n"))


def main():
    """ Main function that is run upon execution of auv.py """
    auv = AUV()


if __name__ == '__main__':  # If we are executing this file as main
    main()
