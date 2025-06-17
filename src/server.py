from enum import Enum
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

game_running = True
board = [["." for _ in range(3)] for _ in range(3)]


def main() -> None:
    await_connections()

    # Send each player a copy of the board.
    for player in players:
        print(f"Sending pnum + board to player #{players.index(player)}")
        player.send(("pnum:" + str(players.index(player) + 1)).encode())
        player.send(("board:" + get_board_as_str()).encode())

    threading.Thread(target=handle_player, args=(player1, 1), daemon=True).start()
    threading.Thread(target=handle_player, args=(player2, 2), daemon=True).start()

    input()

    while game_running:
        players[cur_turn - 1].send("info:yourturn".encode())

    print("Shutting down server...")
    for player in players:
        player.send("info:closing".encode())
    server_socket.close()


def handle_player(sock: socket.socket, player_num: int) -> None:
    while True:
        print(f"Awaiting message from Player {player_num}...")
        try:
            msg = sock.recv(1024).decode()
            type, data = msg.split(":")

            if cur_turn == player_num:
                pass

        except Exception as e:
            if e.__class__ is ConnectionResetError:
                await_reconnect()
            print(f"[ERROR]: {e}")
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
    secs = 0
    thresh = 20

    while secs < thresh:
        time.sleep(1)


def get_board_as_str() -> str:
    global board

    result = ""

    for row in board:
        for piece in row:
            result += str(piece)
        result += "," # Delimiter

    print(result)
    return result


main()
