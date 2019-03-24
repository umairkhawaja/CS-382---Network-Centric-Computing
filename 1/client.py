from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
import sys
import curses
from curses import KEY_RIGHT, KEY_LEFT, KEY_DOWN, KEY_UP
from random import randint,choice
import json
from snake import BOARD_HEIGHT,BOARD_WIDTH,MAX_X,MAX_Y,TIMEOUT
from time import sleep

if len(sys.argv) != 3:
    print("Usage: ", sys.argv[0], "<HOST> <PORT>")
    sys.exit(1)

PLAYER_ID = None

HOST = sys.argv[1]
PORT = int(sys.argv[2])
ADDR = (HOST,PORT)
BUFFSIZE = 512
ENCODING = "utf8"

EXIT = False

def render(strjson,window):
    global PLAYER_ID
    window.clear()
    window.border(0)
    for pid,snake in strjson.items():
        obj = strjson[pid]
        obj = json.loads(obj)
        for i,val in obj.items():
            window.addstr(val[1],val[0],val[2])

def receive(window):
    global PLAYER_ID
    global EXIT
    while True:
        try:
            msg = client_socket.recv(BUFFSIZE).decode(ENCODING)
            if "PID:" in msg:
                msg = msg.split(':')
                PLAYER_ID = msg[1]
            elif "BYE" in msg:
                curses.nocbreak()
                client_socket.close()
                EXIT = True
                break
            elif msg == "VICTORY":
                window.clear()
                window.border(0)
                window.addstr(int(BOARD_HEIGHT/2),int(BOARD_WIDTH/2),"YOU WON!")
                # curses.endwin()
                # window.clear()
                client_socket.close()
                
                return
            else:
                i = msg.find('{')
                j = msg.find(';')
                msg = msg[i:j]
                state = json.loads(msg)
                render(state,window)
        except OSError:
            break

def send(window):
    global EXIT
    while True:
        if EXIT is not True:
            event = window.getch()
            if event in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT,27]:        
                client_socket.send(
                    str(event).encode(ENCODING)
                )
        else:
            break

if __name__ == "__main__":
    curses.initscr()
    curses.beep()
    curses.beep()
    window = curses.newwin(BOARD_HEIGHT,BOARD_WIDTH,0,0)
    window.timeout(TIMEOUT)
    window.nodelay(True)
    window.keypad(True)
    curses.noecho()
    curses.curs_set(0)
    window.border(0)
    client_socket = socket(AF_INET,SOCK_STREAM)
    client_socket.connect(ADDR)


    receive_thread = Thread(target=receive,args=(window,))
    send_thread = Thread(target=send,args=(window,))
    receive_thread.start()
    send_thread.start()

    receive_thread.join()
    send_thread.join()

    curses.echo()
    curses.endwin()
    client_socket.close()
    