#DIRECTIONS
#right = 0 means moves backwards
#left = 0 means down towards board
#base = 0 means left

import serial
import time

#SERIAL COMMUNICATION
arduino = serial.Serial(port='COM5', baudrate=9600)
time.sleep(2)
arduino.reset_input_buffer()

#FUNCTIONS

def move_steppers(angle_right, angle_left, angle_base, dir_right, dir_left, dir_base):
    to_send = bytes([
        2,
        abs(int(angle_right)),
        int(dir_right),
        abs(int(angle_left)),
        int(dir_left),
        abs(int(angle_base)),
        int(dir_base)
        ])
    arduino.write(to_send)
    time.sleep(1)



move_steppers(45, 45, 0, 0, 1, 0)


