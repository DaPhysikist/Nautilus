# Constants for the AUV
RADIO_PATH = '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'
IMU_PATH = '/dev/serial0'
PING = 0xFFFFFF
SEND_SLEEP_DELAY = 1
RECEIVE_SLEEP_DELAY = 0.1
PING_SLEEP_DELAY = 3
CONNECTION_TIMEOUT = 6

# Encoding headers
POSITION_DATA = 0b000
HEADING_DATA = 0b001
MISC_DATA = 0b010
TEMP_DATA = 0b10011
DEPTH_DATA = 0b011

DEPTH_ENCODE = DEPTH_DATA << 21
HEADING_ENCODE = HEADING_DATA << 21
MISC_ENCODE = MISC_DATA << 21
POSITION_ENCODE = POSITION_DATA << 21

DEF_DIVE_SPD = 100

MAX_TIME = 600
MAX_ITERATION_COUNT = MAX_TIME / SEND_SLEEP_DELAY / 7
