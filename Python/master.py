import serial
import time
import math
import subprocess
import chess

# SERIAL COMMUNICATION
arduino = serial.Serial(port='COM5', baudrate=9600)
time.sleep(2)
arduino.reset_input_buffer()


# CONSTANTS
square_side_length = 50
board_margin = 35

y_dist_base_to_board_edge = 60
z_dist_board_top_to_base = 132.15

arm_length = 300
z_dist_TCP_to_grab_point = 104

x_vals = {"h": ((-3*square_side_length)-(square_side_length/2)), "g": ((-2*square_side_length)-(square_side_length/2)), 
          "f": ((-1*square_side_length)-(square_side_length/2)), "e": ((-1)*(square_side_length/2)),
          "d": (square_side_length/2), "c": ((square_side_length)+(square_side_length/2)), 
          "b": ((2*square_side_length)+(square_side_length/2)), "a": ((3*square_side_length)+(square_side_length/2))}

y_vals = {"8": (board_margin + 0*square_side_length + square_side_length/2 + y_dist_base_to_board_edge), 
          "7": (board_margin + 1*square_side_length + square_side_length/2 + y_dist_base_to_board_edge),
          "6": (board_margin + 2*square_side_length + square_side_length/2 + y_dist_base_to_board_edge), 
          "5": (board_margin + 3*square_side_length + square_side_length/2 + y_dist_base_to_board_edge),
          "4": (board_margin + 4*square_side_length + square_side_length/2 + y_dist_base_to_board_edge), 
          "3": (board_margin + 5*square_side_length + square_side_length/2 + y_dist_base_to_board_edge),
          "2": (board_margin + 6*square_side_length + square_side_length/2 + y_dist_base_to_board_edge), 
          "1": (board_margin + 7*square_side_length + square_side_length/2 + y_dist_base_to_board_edge)}

piece_heights = {"pawn": "47.1", "rook": "52.6", "knight": "60.5", "bishop": "68.4", "king": "91.3", "queen": "81.7"}
poised_gripper_heights = {"pawn": 151.1, "rook": 156.6, "knight": 164.5, "bishop": 172.4, "king": 195.3, "queen": 185.7}

close_angles = {"pawn": 85, "rook": 95, "bishop": 90, "knight": 85, "king": 100, "queen": 100}

servo_speed = 10
safe_servo_angle = 95
open_servo_angle = 120

# INITIALIZATION
zero_angles = [0, 0, 0]

position = "position startpos moves"

# FUNCTIONS
def send_to_engine(message):
    engine.stdin.write(f"{message}\n")
    engine.stdin.flush()

def check_for_engine_line(message):
    nextline = engine.stdout.readline()
    while not nextline.startswith(f"{message}"):
        nextline = engine.stdout.readline()

def get_engine_move(position, depth):
    send_to_engine(position)
    send_to_engine(f"go depth {depth}")
    nextline = engine.stdout.readline()
    while not nextline.startswith("bestmove"):
        nextline = engine.stdout.readline()
    parts = nextline.split()
    move = parts[1]
    return move

def get_target_angles(square, piece, is_poised): #THIS ONE IS GOOD
    file = square[0]
    rank = square[1]
    x = x_vals[file]
    y = y_vals[rank]
    if is_poised==0:
        z = float(piece_heights[f"{piece}"]) + z_dist_TCP_to_grab_point - z_dist_board_top_to_base
    else:
        z = float(poised_gripper_heights[f"{piece}"]) + z_dist_TCP_to_grab_point - z_dist_board_top_to_base

    l = math.sqrt(x**2 + y**2)
    phi = math.atan(z/l)*(180/math.pi)
    theta = math.acos(math.sqrt(z**2+l**2)/(2*arm_length))*(180/math.pi)
    a1 = phi+theta
    a2 = phi-theta
    a3 = math.atan(x/y)*(180/math.pi)

    angle_right = 90 - a1
    angle_left = abs(a2)
    angle_base = a3

    return [angle_right, angle_left, angle_base]

def get_travelling_directions(travelling_angles): #just reversed for dir_left per system
    if travelling_angles[0] > 0:
        dir_right = 1
    else:
        dir_right = 0;
    if travelling_angles[1] > 0:
        dir_left = 0
    else:
        dir_left = 1
    if travelling_angles[2] > 0:
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

def move_sequence(move):
    square1 = move[0:2]
    file1 = square1[0]
    rank1 = square1[1]
    piece1 = "pawn" #TEMP

    square2 = move[2:4]
    file2 = square2[0]
    rank2 = square2[1]

    square1_angles = get_target_angles(square1, piece1, 0)
    square2_angles = get_target_angles(square2, piece1, 0)
    square1_poised_angles = get_target_angles(square1, piece1, 1)
    square2_poised_angles = get_target_angles(square2, piece1, 1)

    #travelling_angles1 = square1_poised_angles
    #travelling_directions1 = get_travelling_directions(travelling_angles1)

    travelling_angles1 = square1_angles
    travelling_directions1 = get_travelling_directions(travelling_angles1)

    #travelling_angles2 = [square1_angles[i] - square1_poised_angles[i] for i in range(3)]
    #travelling_directions2 = get_travelling_directions(travelling_angles2)

    travelling_angles3 = [square1_poised_angles[i] - square1_angles[i] for i in range(3)]
    travelling_directions3 = get_travelling_directions(travelling_angles3)

    #travelling_angles4 = [square2_poised_angles[i] - square1_poised_angles[i] for i in range(3)]
    #travelling_directions4 = get_travelling_directions(travelling_angles4)

    travelling_angles4 = [square2_angles[i] - square1_poised_angles[i] for i in range(3)]
    travelling_directions4 = get_travelling_directions(travelling_angles4)

    travelling_angles5 = [zero_angles[i] - square2_angles[i] for i in range(3)]
    travelling_directions5 = get_travelling_directions(travelling_angles5)

    #travelling_angles5 = [square2_angles[i] - square2_poised_angles[i] for i in range(3)]
    #travelling_directions5 = get_travelling_directions(travelling_angles5)
    
    #travelling_angles6 = [square2_poised_angles[i] - square2_angles[i] for i in range(3)]
    #travelling_directions6 = get_travelling_directions(travelling_angles6)

    #travelling_angles7 = [zero_angles[i] - square2_poised_angles[i] for i in range(3)]
    #travelling_directions7 = get_travelling_directions(travelling_angles7)

    close_servo_angle = close_angles[piece1]

    move_servo(safe_servo_angle)
    move_servo(open_servo_angle)
    move_steppers(*travelling_angles1, *travelling_directions1)
    #move_steppers(*travelling_angles2, *travelling_directions2)
    move_servo(close_servo_angle)
    move_steppers(*travelling_angles3, *travelling_directions3)
    move_steppers(*travelling_angles4, *travelling_directions4)
    #move_steppers(*travelling_angles5, *travelling_directions5)
    move_servo(open_servo_angle)
    move_steppers(*travelling_angles5, *travelling_directions5)
    #move_steppers(*travelling_angles6, *travelling_directions6)
    move_servo(safe_servo_angle)
    #move_steppers(*travelling_angles7, *travelling_directions7)

# SUBPROCESS (CHESS ENGINE)
engine = subprocess.Popen([r"C:\Users\ebabb\Desktop\Chess Robot\stockfish\stockfish.exe"], 
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
send_to_engine("uci")
check_for_engine_line("uciok")
send_to_engine("isready")
check_for_engine_line("readyok")
send_to_engine("ucinewgame")


# INSTRUCTIONS
print("Moves are notated by listing the square the piece begins and the square it lands. For example, e2e4 is a pawn move from e2 to e4. \
There is no need to include a '+' at the end for moves that are checks. There is no need to include an 'x' for captures\n")
print("At any point, if you wish to resign, simply enter 'resign' as your move. The engine does not take draw offers nor offer them, so a draw only occurs if \
the 50 move rule is reached, or if there is a 3-fold repetition, both of which the engine will detect.\n")
colour = input("Which colour pieces: ")
depth = input("What difficulty (1 to 10): ")

while (True):
    move = input("Enter a move: ")
    position += f" {move}"

    engine_move = get_engine_move(position, depth)
    position += f" {engine_move}"
    print(f"The engine plays {engine_move}")
    move_sequence(engine_move)



