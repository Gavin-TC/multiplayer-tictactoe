from enum import Enum
from nt import truncate
import socket
import threading
import time

HOST = "0.0.0.0"
PORT = 5555

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

player1: socket.socket | None = None
player2: socket.socket | None = None
player1_addr: socket.AddressFamily | None = None
player2_addr: socket.AddressFamily | None = None

players = []
addrs = []

cur_turn = 1
cur_move = -1
advance_turn = True
move_accepted = False

game_running = True
board = [["." for _ in range(3)] for _ in range(3)]


def main() -> None:
    global game_running, cur_turn, cur_move, advance_turn, move_accepted

    await_connections()

    # Send each player a copy of the board and their assigned player number.
    for player in players:
        print(f"Sending `pnum` and `board` to Player #{players.index(player) + 1}")
        player.send(("pnum:" + str(players.index(player) + 1)).encode())
        time.sleep(0.2)
        player.send(("board:" + get_board_as_str()).encode())

    threading.Thread(target=handle_player, args=(player1, 1), daemon=True).start()
    threading.Thread(target=handle_player, args=(player2, 2), daemon=True).start()

    print("[SERVER] Game is starting!")
    while game_running:
        if is_draw(board):
            print("[SERVER] Game is a draw!")
            game_running = False
            break

        players[cur_turn - 1].send(("info:yourturn:" + get_board_as_str()).encode())

        while move_accepted == False:
            pass
        move_accepted = False
    try:
        for player in players:
            player.send("info:closing".encode())
    except Exception as e:
        print(f"[SERVER][ERROR] Error occurred when shutting down: {e}")

    print("Server successfully shut down.")
    server_socket.close()


def is_valid(move) -> bool:
    if move.isdigit():
        move = int(move) - 1
        if 0 <= move <= 8 and board[move // 3][move % 3] == ".":
            return True
    return False

def is_win(board) -> bool:
    # Check rows
    for row in board:
        if row[0] == row[1] == row[2] != ".":
            return True

    # Check columns
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] != ".":
            return True

    # Check diagonals
    if board[0][0] == board[1][1] == board[2][2] != ".":
        return True
    if board[0][2] == board[1][1] == board[2][0] != ".":
        return True

    return False


def is_draw(board):
    return all(cell != "." for row in board for cell in row)


def handle_player(sock: socket.socket, player_num: int) -> None:
    global cur_turn, board, move_accepted

    while True:
        print(f"Awaiting message from Player {player_num}...")
        try:
            msg = sock.recv(1024).decode()
            print(f"Received message from Player {player_num}: `{msg}`")
            type, data = msg.split(":", 1)

            match type:
                case "move":
                    if cur_turn == player_num:
                        move = data
                        if is_valid(move):
                            print(f"[SERVER: INFO] Move `{move}` is valid.")
                            sock.send("info:move_accepted".encode())
                            board[(int(move) - 1) // 3][(int(move) - 1) % 3] = "X" if player_num == 1 else "O"

                            # After every valid move, check if the game is over.
                            if is_win(board):
                                print(f"[SERVER: INFO] Player {player_num} wins!")
                                sock.send(("info:win:" + get_board_as_str()).encode())
                                print(f"[SERVER: INFO] Player {player_num % 2 + 1} lost!")
                                players[player_num % 2].send(("info:lost:" + get_board_as_str()).encode())
                                return
                            else:
                                cur_turn = cur_turn % 2 + 1
                                move_accepted = True
                                time.sleep(0.1) # Give time for client to receive previous message
                                for player in players:
                                    player.send(("board:" + get_board_as_str()).encode())
                        else:
                            print(f"[SERVER] Move `{move}` is invalid.")
                            sock.send("info:move_declined".encode())
                            cur_turn = cur_turn % 2 + 1
                case "info":
                    match data:
                        case "closing":
                            print(f"[SERVER: INFO] Player {player_num} disconnected.")
        except Exception as e:
            if e.__class__ is ConnectionResetError:
                await_reconnect()
            print(f"[ERROR] While handling Player {player_num}: {e}")
            break


def await_connections() -> None:
    global player1, player2, player1_addr, player2_addr

    print(f"Server listening on {HOST}:{PORT}...")
    while player2 is None:
        client_socket, client_addr = server_socket.accept()

        if not player1:
            player1 = client_socket
            player1_addr = client_addr
            players.append(player1)
            addrs.append(player1_addr)
            print("Player 1 has connected...")

        elif not player2:
            player2 = client_socket
            player2_addr = client_addr
            players.append(player2)
            addrs.append(player2_addr)
            print("Player 2 has connected...")

    print("Both players have connected!")


# [UNFINISHED]
# This method waits for a user to reconnect after disconnecting
# If the user does not reconnect within `thresh` seconds, then the server shuts down.
# [UNFINISHED]
def await_reconnect() -> None:
    return


def get_board_as_str() -> str:
    global board
    result = ""

    for row in board:
        for piece in row:
            result += str(piece)
        result += "," # Delimiter
    return result


main()
