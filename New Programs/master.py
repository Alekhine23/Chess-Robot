from stockfish import Stockfish
import chess
import math
import serial
import time
import numpy as np

#SERIAL COMMUNICATION
arduino = serial.Serial(port='COM5', baudrate=9600)
time.sleep(2)
arduino.reset_input_buffer()

#CONSTANTS
square_length = 50
margin = 35

y_dist_base_to_board = 70
z_dist_board_to_base = 132.15

arm_length = 300
TCP_to_grab = 104

#FIX THIS IN MATH CODE
y_vals = [] #ranks 1 through 8
for i in range(7, -1 , -1):
    y_vals.append(int(margin + i*square_length + square_length/2 + y_dist_base_to_board))

x_vals_half = [] #files a through h
for i in range(3, -1, -1):
    x_vals_half.append(int((i*square_length) - (square_length/2)))
x_vals = x_vals_half
for i in x_vals_half[::-1]:
    x_vals.append(int(-i))

piece_heights = {"pawn": "47.1", "rook": "52.6", "knight": "60.5", "bishop": "68.4", "king": "91.3", "queen": "81.7"}
poised_gripper_heights = {"pawn": 151.1, "rook": 156.6, "knight": 164.5, "bishop": 172.4, "king": 195.3, "queen": 185.7}
close_angles = {"pawn": 95, "rook": 95, "bishop": 95, "knight": 95, "king": 95, "queen": 95}

servo_speed = 10
safe_angle = 95
open_angle = 120

#INITIALIZATION
zero_angles = [0, 0, 0]
capture_angles = [1, 1, 1] #FIND THESE OUT FOR REAL
position = []

#position = "position startpos moves"
stockfish = Stockfish(path="/Users/ebabb/Documents/Chess_Robot/stockfish.exe")

#FUNCTIONS
def get_angles(square, piece, is_poised):
    #ANGLES
    file = int(ord(square[0]) - ord('a'))
    rank = int(square[1]) - 1
    x = x_vals[file]
    y = y_vals[rank]
    if is_poised==0:
        z = float(piece_heights[f"{piece}"]) + TCP_to_grab - z_dist_board_to_base
        print(z)
    else:
        z = float(poised_gripper_heights[f"{piece}"]) + TCP_to_grab - z_dist_board_to_base
        print(z)

    l = math.sqrt(x**2 + y**2)
    phi = math.atan(z/l)*(180/math.pi)
    theta = math.acos(math.sqrt(z**2+l**2)/(2*arm_length))*(180/math.pi)
    a1 = phi+theta
    a2 = phi-theta
    a3 = math.atan(x/y)*(180/math.pi)

    angle_right = 90 - a1
    angle_left = abs(a2)
    angle_base = a3

    # #DIRECTIONS
    # if angle_right > 0:
    #     dir_right = 1
    # else:
    #     dir_right = 0
    # if angle_left > 0:
    #     dir_left = 0
    # else:
    #     dir_left = 1
    # if angle_base > 0:
    #     dir_base = 1
    # else:
    #     dir_base = 0

    return [angle_right, angle_left, angle_base]

def get_directions(angles): #just reversed for dir_left per system
    if angles[0] > 0:
        dir_right = 1
    else:
        dir_right = 0
    if angles[1] > 0:
        dir_left = 0
    else:
        dir_left = 1
    if angles[2] > 0:
        dir_base = 1
    else:
        dir_base = 0
    return [dir_right, dir_left, dir_base]

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

def move_servo(angle):
    to_send = bytes([
        1,
        int(angle),
        int(servo_speed)
        ])
    arduino.write(to_send)
    time.sleep(0.1)

def make_fish_move(move):
    if move == "O-O":
        1 #make stuff for castling
    elif move == "O-O-O":
        1 #make stuff for castling
    else: 
        if stockfish.get_what_is_on_square(move[2:4]) != None: #CAPTURE
            square2 = move[2:4]
            piece2_obj = stockfish.get_what_is_on_square(square2)
            piece2 = str(piece2_obj).split('.')[-1].split('_')[-1].lower()

            square2_angles = get_angles(square2, piece2, 0)
            square2_angles_poised = get_angles(square2, piece2, 1)

            angles1 = square2_angles_poised
            dirs1 = get_directions(angles1)
            move_steppers(*angles1, *dirs1)

            angles2 = [square2_angles[i] - square2_angles_poised[i] for i in range(3)]
            dirs2 = get_directions(angles2)
            move_steppers(*angles2, *dirs2)
            move_servo(close_angles[piece2])

            angles3 = [square2_angles_poised[i]-square2_angles[i] for i in range(3)]
            dirs3 = get_directions(angles3)
            move_steppers(*angles3, *dirs3)
            
            angles4 = [capture_angles[i] - square2_angles_poised[i] for i in range(3)]
            dirs4 = get_directions(angles4)
            move_steppers(*angles4, *dirs4)
            move_servo(open_angle)

            angles5 = [zero_angles[i] - capture_angles[i] for i in range(3)]
            dirs5 = get_directions(angles5)
            move_steppers(*angles5, *dirs5)

            # square2_targets = get_targets(square2, piece2, 0)
            # square2_targets_poised = get_targets(square2, piece2, 1)

            # move_steppers(square2_targets_poised)
            # move_steppers([square2_targets[i] - square2_targets_poised[i] for i in range(3)])
            # move_servo(close_angles[piece2])
            # move_steppers([square2_targets_poised[i] - square2_targets[i] for i in range(3)])
            # move_steppers([capture_angles[i] - square2_targets_poised[i] for i in range(3)])
            # move_servo(open_angle)
            # move_steppers([zero_angles[i] - capture_angles[i] for i in range(3)])
        
        #carry on with normal move
        square1 = move[0:2]
        piece1_obj = stockfish.get_what_is_on_square(square1)
        piece1 = str(piece1_obj).split('.')[-1].split('_')[-1].lower()
        square2 = move[2:4]

        square1_angles = get_angles(square1, piece1, 0)
        square1_angles_poised = get_angles(square1, piece1, 1)
        square2_angles = get_angles(square2, piece1, 0)
        square2_angles_poised = get_angles(square2, piece1, 1)

        angles1 = square1_angles_poised
        dirs1 = get_directions(angles1)
        move_steppers(*angles1, *dirs1)

        angles2 = [square1_angles[i] - square1_angles_poised[i] for i in range(3)]
        dirs2 = get_directions(angles2)
        move_steppers(*angles2, *dirs2)
        move_servo(close_angles[piece1])

        angles3 = [square1_angles_poised[i] - square1_angles[i] for i in range(3)]
        dirs3 = get_directions(angles3)
        move_steppers(*angles3, *dirs3)

        angles4 = [square2_angles_poised[i] - square1_angles_poised[i] for i in range(3)]
        dirs4 = get_directions(angles4)
        move_steppers(*angles4, *dirs4)

        angles5 = [square2_angles[i] - square2_angles_poised[i] for i in range(3)]
        dirs5 = get_directions(angles5)
        move_steppers(*angles5, *dirs5)
        move_servo(open_angle)

        angles6 = [square2_angles_poised[i] - square2_angles[i] for i in range(3)]
        dirs6 = get_directions(angles6)
        move_steppers(*angles6, *dirs6)

        angles7 = [zero_angles[i] - square2_angles_poised[i] for i in range(3)]
        dirs7 = get_directions(angles7)
        move_steppers(*angles7, *dirs7)


        # square1_targets = get_targets(square1, piece1, 0)
        # square1_targets_poised = get_targets(square1, piece1, 1)
        # square2_targets = get_targets(square2, piece1, 0)
        # square2_targets_poised = get_targets(square2, piece1, 1)

        # move_steppers(square1_targets_poised)
        # move_steppers([square1_targets[i] - square1_targets_poised[i] for i in range(3)])
        # move_servo(close_angles[piece1])
        # move_steppers([square1_targets_poised[i] - square1_targets[i] for i in range(3)])
        # move_steppers([square2_targets_poised[i] - square1_targets_poised[i] for i in range(3)])
        # move_steppers([square2_targets[i] - square2_targets_poised[i] for i in range(3)])
        # move_servo(open_angle)
        # move_steppers([square2_targets_poised[i] - square2_targets[i] for i in range(3)])
        # move_steppers([zero_angles[i] - square2_targets_poised[i] for i in range(3)])

# INSTRUCTIONS
print("Moves are notated by listing the square the piece begins and the square it lands. For example, e2e4 is a pawn move from e2 to e4. \
There is no need to include a '+' at the end for moves that are checks. There is no need to include an 'x' for captures\n")
print("At any point, if you wish to resign, simply enter 'resign' as your move. The engine does not take draw offers nor offer them, so a draw only occurs if \
the 50 move rule is reached, or if there is a 3-fold repetition, both of which the engine will detect.\n")
print("As default, you will play as white")
depth = input("What ELO difficulty would you like to play against? (0 to 3000): ")

#MAIN LOOP
while (True):
    human_move = input("Play a move and enter it here: ")
    position.append(human_move)
    stockfish.set_position(position)

    fish_move = stockfish.get_best_move()
    position.append(fish_move)
    print(f"Robot plays {fish_move}")

    make_fish_move(fish_move)