from enum import Enum
from time import sleep
import socket
import threading
import time
import os

HOST = "127.0.0.1"
PORT = 5555

class ClientState(Enum):
    SHUTTING_DOWN = 1
    PLAYING = 2
    AWAITING_CONNECTION = 3

board_data = ""
board = []
board_ready_event = threading.Event()
player_num = -1
my_turn = False

def main() -> None:
    game_running = True
    shared_state = {"cur_state": ClientState.PLAYING}

    client_socket = attempt_server_connect()

    print(f"Connected to server at {HOST}:{PORT}")

    threading.Thread(target=listen, args=(client_socket, shared_state), daemon=True).start()
    threading.Thread(target=handle_state, args=(client_socket, shared_state), daemon=True).start()

    board_ready_event.wait()

    while game_running and shared_state["cur_state"] == ClientState.PLAYING:
        for row in board:
            for char in row:
                print(char, end="")
            print()

        if my_turn == True:
            move = input("Enter a move: ")
            match move:
                case 'q':
                    shared_state["cur_state"] = ClientState.SHUTTING_DOWN
            client_socket.send(("move:" + str(move)).encode())
        else:
            print("Wait for your turn...")

        match shared_state["cur_state"]:
            case ClientState.AWAITING_CONNECTION:
                attempt_server_connect()

    client_socket.send("closing".encode())


def attempt_server_connect() -> socket.socket | None:
    while True:
        try:
            client_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((HOST, PORT))

            clear_terminal()

            return client_socket
        except:
            seconds = 5
            print("Server connection failed...")
            print(f"Retrying connection in {seconds} seconds...")
            time.sleep(seconds)


def clear_terminal() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def listen(sock: socket.socket, cur_state):
    global board, my_turn

    while True:
        try:
            msg = sock.recv(1024).decode()
            print(f"msg: '{msg}'")
            type, data = msg.split(":")

            match type:
                case "pnum":
                    print(f"You are player {data}!")
                    player_num = data

                case "board":
                    board = data
                    print(f"Received board: {board}")
                    parse_board(board)

                case "info":
                    match data:
                        case "closing":
                            cur_state["cur_state"] = ClientState.AWAITING_CONNECTION
                        case "yourturn":
                            my_turn = True
        except Exception as e:
            print(f"[ERROR] Ran into error while listening: {e}")
            break


def parse_board(board_str: str) -> None:
    global board

    board_str = board_str[:-1]
    rows = board_str.split(",")

    board = [list(row) for row in rows]
    board_ready_event.set()


# kinda useless atm
def handle_state(sock: socket.socket, cur_state) -> None:
    while True:
        match cur_state["cur_state"]:
            case ClientState.SHUTTING_DOWN:
                print("Shutting client down...")
                break


main()
