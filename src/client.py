from enum import Enum
import socket
import threading
import time
import os

HOST = "127.0.0.1"
PORT = 5555

class ClientState(Enum):
    SHUTTING_DOWN = 1
    AWAITING_SHUTDOWN = 2
    PLAYING = 3
    AWAITING_CONNECTION = 4
    HANDLING_ERROR = 5

class GameState(Enum):
    WON = 1
    LOST = 2
    DRAW = 3
    PLAYING = 4

board_data = ""
board = []
board_ready_event = threading.Event()
board_updated = threading.Event()
shutdown_event = threading.Event()
player_num = -1
my_turn = False

# Basically a flag that allows the next frame to be rendered
advance_frame = True
move_accepted = False
game_running = True
game_over = False


def main() -> None:
    global my_turn, advance_frame, move_accepted, game_running, game_over

    shared_state = {"cur_state": ClientState.PLAYING, "game_state": GameState.PLAYING}

    client_socket: socket.socket = attempt_server_connect(shared_state)

    print(f"Connected to server at {HOST}:{PORT}")
    print(f"Waiting for game to start...")

    threading.Thread(target=listen, args=(client_socket, shared_state), daemon=True).start()

    board_ready_event.wait()

    while game_running:
        if advance_frame:
            advance_frame = False

            clear_terminal()
            print_board()

            if game_over:
                game_running = False
                my_turn = False
                shared_state["cur_state"] = ClientState.AWAITING_SHUTDOWN

            if my_turn:
                while not move_accepted:
                    move = input("Your move (1-9, or 'q' to quit): ")

                    match move:
                        case "q":
                            shared_state["cur_state"] = ClientState.SHUTTING_DOWN
                            break

                    if move.isdigit():
                        client_socket.send(("move:" + str(move)).encode())
                    time.sleep(0.25) # Allow time for server to process move
                move_accepted = False
            elif not game_over:
                print("Waiting for your turn...")

        # State should always be checked, not just during frame render
        match shared_state["cur_state"]:
            case ClientState.HANDLING_ERROR:
                print("Caught error...")
                game_running = False

            case ClientState.SHUTTING_DOWN:
                print("Quitting...")
                game_running = False

            case ClientState.AWAITING_SHUTDOWN:
                pass

            case ClientState.AWAITING_CONNECTION:
                print("Attempting server reconnect...")
                attempt_server_connect(shared_state)
                time.sleep(1)

    match shared_state["game_state"]:
        case GameState.WON:
            print("You won!")

        case GameState.LOST:
            print("You lost!")

        case GameState.DRAW:
            print("Draw!")
    print("Game Over!")

    shutdown_event.set()
    time.sleep(0.5)

    try:
        client_socket.send("info:closing".encode())
    except Exception as e:
        print(f"[ERROR] Ran into error when sending closing message: {e}")

    try:
        client_socket.shutdown(socket.SHUT_RDWR)
        client_socket.close()
    except Exception as e:
        print(f"[ERROR] Ran into error when closing connection: {e}")

    client_socket.close()


def attempt_server_connect(cur_state) -> socket.socket:
    while True:
        try:
            client_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((HOST, PORT))

            clear_terminal()

            # The player is now connected, they can begin playing.
            cur_state["cur_state"] = ClientState.PLAYING

            return client_socket
        except:
            seconds = 5
            print("Server connection failed...")
            print(f"Retrying connection in {seconds} seconds...")
            time.sleep(seconds)


def clear_terminal() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def listen(sock: socket.socket, cur_state) -> None:
    global board, player_num, my_turn, advance_frame, move_accepted, game_running, game_over, shutdown_event

    while game_running and not shutdown_event.is_set():
        try:
            type, data = sock.recv(1024).decode().split(":", 1)

            match type:
                case "pnum":
                    print(f"You are player {data}!")
                    player_num = data

                case "board":
                    parse_board(data)
                    board_updated.set()
                    advance_frame = True

                # Check what the data is, because this tag is multi-purpose
                case "info":
                    match data.split(":", 1)[0]:
                        case "closing":
                            cur_state["cur_state"] = ClientState.AWAITING_CONNECTION

                        case "yourturn":
                            board_data = data.split(":", 1)[1]
                            print(f"Board data: {board_data}")
                            parse_board(board_data)
                            advance_frame = True
                            my_turn = True

                        case "move_accepted":
                            advance_frame = True
                            move_accepted = True
                            my_turn = False

                        case "move_declined":
                            print("Invalid move! Try again.")

                        case "win":
                            print("You won!")
                            board_data = data.split(":", 1)[1]
                            parse_board(board_data)
                            game_over = True
                            cur_state["game_state"] = GameState.WON

                        case "lost":
                            print("You lost!")
                            board_data = data.split(":", 1)[1]
                            parse_board(board_data)
                            game_over = True
                            cur_state["game_state"] = GameState.LOST

                        case "draw":
                            print("The game is a draw!")
                            board_data = data.split(":", 1)[1]
                            parse_board(board_data)
                            game_over = True
                            cur_state["game_state"] = GameState.DRAW
        except Exception as e:
            print(f"[ERROR] Ran into error while listening: {e}")
            cur_state["cur_state"] = ClientState.HANDLING_ERROR


def parse_board(board_str: str) -> None:
    global board, advance_frame

    board_str = board_str[:-1]
    rows = board_str.split(",")

    board = [list(row) for row in rows]
    board_ready_event.set()

    advance_frame = True


def print_board() -> None:
    for row in board:
        for char in row:
            print(char, end="")
        print()


main()
