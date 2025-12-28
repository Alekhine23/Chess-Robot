from stockfish import Stockfish                 #used to get engine recommended moves
import chess                                    #used for game state tracking (draw, checkmate, captures, etc.)
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
margin = 33

y_dist_base_to_board = 70
z_dist_board_to_base = 132.15

arm_length = 300
TCP_to_grab = 104

y_vals = [] #ranks 1 through 8
for i in range(7, -1 , -1):
    y_vals.append(int(margin + i*square_length + square_length/2 + y_dist_base_to_board))

x_vals_half = [] #files a through h
for i in range(3, -1, -1):
    print(i)
    x_vals_half.append(int((i*square_length) + (square_length/2)))
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
capture_angles = [30, 45, 50] #Arbitrary; can dump anywhere on the side, adjust per user setup
position = []
board = chess.Board()

piece_map = {
    chess.PAWN: "pawn",
    chess.ROOK: "rook", 
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.QUEEN: "queen",
    chess.KING: "king"
}

stockfish = Stockfish(path="/Users/ebabb/Documents/Chess_Robot/stockfish.exe")

#FUNCTIONS
def get_angles(square, piece, is_poised):
    file = int(ord(square[0]) - ord('a'))
    rank = int(square[1]) - 1
    x = x_vals[file]
    y = y_vals[rank]
    if is_poised==0:
        z = float(piece_heights[f"{piece}"]) + TCP_to_grab - z_dist_board_to_base
    else:
        z = float(poised_gripper_heights[f"{piece}"]) + TCP_to_grab - z_dist_board_to_base

    l = math.sqrt(x**2 + y**2)
    phi = math.atan(z/l)*(180/math.pi)
    theta = math.acos(math.sqrt(z**2+l**2)/(2*arm_length))*(180/math.pi)
    a1 = phi+theta
    a2 = phi-theta
    a3 = math.atan(x/y)*(180/math.pi)

    angle_right = 90 - a1
    angle_left = a2
    angle_base = a3

    return [angle_right, angle_left, angle_base]

def get_directions(angles):
    if angles[0] > 0:
        dir_right = 1
    else:
        dir_right = 0
    if angles[1] > 0:
        dir_left = 1
    else:
        dir_left = 0
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
    if (move == "O-O") or (move == "O-O-O"):        # Castling sequence
        if move == "O-O":
            king_square1 = "e8"
            king_square2 = "g8"
            rook_square1 = "h8"
            rook_square2 = "f8"
        else:
            king_square1 = "e8"
            king_square2 = "c8"
            rook_square1 = "a8"
            rook_square2 = "d8"
        king_square1_angles = get_angles(king_square1, "king", 0)
        king_square1_angles_poised = get_angles(king_square1, "king", 1)
        king_square2_angles = get_angles(king_square2, "king", 0)
        king_square2_angles_poised = get_angles(king_square2, "king", 1)

        rook_square1_angles = get_angles(rook_square1, "rook", 0)
        rook_square1_angles_poised = get_angles(rook_square1, "rook", 1)
        rook_square2_angles = get_angles(rook_square2, "rook", 0)
        rook_square2_angles_poised = get_angles(rook_square2, "rook", 1)

        angles1 = king_square1_angles_poised
        dirs1 = get_directions(angles1)
        move_steppers(*angles1, *dirs1)

        angles2 = [king_square1_angles[i] - king_square1_angles_poised[i] for i in range(3)]
        dirs2 = get_directions(angles2)
        move_steppers(*angles2, *dirs2)
        move_servo(close_angles["king"])

        angles3 = [king_square1_angles_poised[i] - king_square1_angles[i] for i in range(3)]
        dirs3 = get_directions(angles3)
        move_steppers(*angles3, *dirs3)

        angles4 = [king_square2_angles_poised[i] - king_square1_angles_poised[i] for i in range(3)]
        dirs4 = get_directions(angles4)
        move_steppers(*angles4, *dirs4)

        angles5 = [king_square2_angles[i] - king_square2_angles_poised[i] for i in range(3)]
        dirs5 = get_directions(angles5)
        move_steppers(*angles5, *dirs5)
        move_servo(open_angle)

        angles6 = [king_square2_angles_poised[i] - king_square2_angles[i] for i in range(3)]
        dirs6 = get_directions(angles6)
        move_steppers(*angles6, *dirs6)

        angles7 = [rook_square1_angles_poised[i] - king_square2_angles_poised[i] for i in range(3)]
        dirs7 = get_directions(angles7)
        move_steppers(*angles7, *dirs7)

        angles8 = [rook_square1_angles[i] - rook_square1_angles_poised[i] for i in range(3)]
        dirs8 = get_directions(angles8)
        move_steppers(*angles8, *dirs8)
        move_servo(close_angles["rook"])

        angles9 = [rook_square1_angles_poised[i] - rook_square1_angles[i] for i in range(3)]
        dirs9 = get_directions(angles9)
        move_steppers(*angles9, *dirs9)

        angles10 = [rook_square2_angles_poised[i] - rook_square1_angles_poised[i] for i in range(3)]
        dirs10 = get_directions(angles10)
        move_steppers(*angles10, *dirs10)

        angles11 = [rook_square2_angles[i] - rook_square2_angles_poised[i] for i in range(3)]
        dirs11 = get_directions(angles11)
        move_steppers(*angles11, *dirs11)
        move_servo(open_angle)

        angles12 = [rook_square2_angles_poised[i] - rook_square2_angles[i] for i in range(3)]
        dirs12 = get_directions(angles12)
        move_steppers(*angles12, *dirs12)

        angles13 = [zero_angles[i] - rook_square2_angles_poised[i] for i in range(3)]
        dirs13 = get_directions(angles13)
        move_steppers(*angles13, *dirs13)
    else: 
        if board.is_capture(chess.Move.from_uci(move)):                  #if move is capture, clear square first
            if board.is_en_passant(chess.Move.from_uci(move)):
                temp = move[2:4]
                clear_square = temp[0] + str(int(temp[1]) + 1)   #one square closer to robot is the square to clear if en passant
            else:
                clear_square = move[2:4]
            clear_piece = piece_map[(board.piece_at(chess.parse_square(clear_square))).piece_type]
            
            clear_square_angles = get_angles(clear_square, clear_piece, 0)
            clear_square_angles_poised = get_angles(clear_square, clear_piece, 1)

            angles1 = clear_square_angles_poised
            dirs1 = get_directions(angles1)
            move_steppers(*angles1, *dirs1)

            angles2 = [clear_square_angles[i] - clear_square_angles_poised[i] for i in range(3)]
            dirs2 = get_directions(angles2)
            move_steppers(*angles2, *dirs2)
            move_servo(close_angles[clear_piece])

            angles3 = [clear_square_angles_poised[i] - clear_square_angles[i] for i in range(3)]
            dirs3 = get_directions(angles3)
            move_steppers(*angles3, *dirs3)
            
            angles4 = [capture_angles[i] - clear_square_angles_poised[i] for i in range(3)]
            dirs4 = get_directions(angles4)
            move_steppers(*angles4, *dirs4)
            move_servo(open_angle)

            angles5 = [zero_angles[i] - capture_angles[i] for i in range(3)]
            dirs5 = get_directions(angles5)
            move_steppers(*angles5, *dirs5)
        
        #carry on with normal move
        square1 = move[0:2]
        piece1 = piece_map[(board.piece_at(chess.parse_square(square1))).piece_type]
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

# INSTRUCTIONS
print("Moves are notated by listing the square the piece begins and the square it lands. For example, e2e4 is a pawn move from e2 to e4. \
There is no need to include a '+' at the end for moves that are checks. There is no need to include an 'x' for captures\n")
print("At any point, if you wish to resign, simply enter 'resign' as your move. The engine does not take draw offers nor offer them, so a draw only occurs if \
the 50 move rule is reached, or if there is a 3-fold repetition, both of which the engine will detect.\n")
print("As default, you will play as white")
depth = int(input("What ELO difficulty would you like to play against? (0 to 3000): "))
stockfish.set_elo_rating(depth)

# MAIN LOOP
while (True):
    human_move = input("Play a move and enter it here: ")
    if human_move == "resign":
        print("Thank you for playing, black wins")
        break

    while (True):
        try:
            if chess.Move.from_uci(human_move) in board.legal_moves:
                break
        except (chess.InvalidMoveError, ValueError):
            pass
        human_move = input("Please play a valid move: ")

    position.append(human_move)
    board.push(chess.Move.from_uci(human_move))         
    stockfish.set_position(position)     

    if board.is_stalemate():
        print("Draw by stalemate")
        break
    elif board.is_insufficient_material():
        print("Draw by insufficient material")
        break
    elif board.can_claim_threefold_repetition():
        print("Draw by threefold repetition")
        break
    elif board.can_claim_fifty_moves():
        print("Draw by fifty move rule")
        break
    elif board.is_checkmate():
        print("White wins by checkmate")
        break

    fish_move = stockfish.get_best_move()
    print(f"The robot plays {fish_move}")
    make_fish_move(fish_move)

    position.append(fish_move)
    board.push(chess.Move.from_uci(fish_move)) 
    stockfish.set_position(position)

    if board.is_stalemate():
        print("Draw by stalemate")
        break
    elif board.is_insufficient_material():
        print("Draw by insufficient material")
        break
    elif board.can_claim_threefold_repetition():
        print("Draw by threefold repetition")
        break
    elif board.can_claim_fifty_moves():
        print("Draw by fifty move rule")
        break
    elif board.is_checkmate():
        print("White wins by checkmate")
        break

#END
print("Thank you for playing!")