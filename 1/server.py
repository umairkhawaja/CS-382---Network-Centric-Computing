from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread,Lock
import sys
from snake import Snake,Body,BOARD_HEIGHT,BOARD_WIDTH,MAX_X,MAX_Y,TIMEOUT
import json
from curses import KEY_RIGHT, KEY_LEFT, KEY_DOWN, KEY_UP
from random import randint
from time import sleep

if len(sys.argv) != 4:
    print("Usage: ", sys.argv[0], "<HOST> <PORT> <NUMBER OF PLAYERS>")
    sys.exit(1)

def getSnake(pid,players=2):
    global heads
    global active_players

    snake = None
    if pid == 1:
        snake = Snake(int(BOARD_WIDTH/players),int(BOARD_HEIGHT/players),heads[active_players-1])
        snake.change_direction(KEY_RIGHT)
    elif pid == 2:
        snake = Snake(int(BOARD_WIDTH/players),10+int(BOARD_HEIGHT/players),heads[active_players-1])
        snake.change_direction(KEY_RIGHT)
    return snake

def parseBody(bodylist):
    parsed = {}
    for i,body in enumerate(bodylist):
        parsed[i] = (body.x,body.y,body.char)
    return parsed

KEY_MAP = {
    '260' : KEY_LEFT,
    '259' : KEY_UP,
    '261' : KEY_RIGHT,
    '258' : KEY_DOWN
}

HOST = sys.argv[1]
PORT = int(sys.argv[2])
NUM_PLAYERS = int(sys.argv[3])
ENCODING = "utf8"

clients = {}
addresses = {}
BUFFSIZE = 259
ADDR = (HOST,PORT)


allClients = []
clientExit = {}
dir_threads = {}
mov_threads = {}
client_ack = {}

client_lock = Lock()
state_lock = Lock()
gs_lock = Lock()


active_players = 0
heads = ['@','%','#','8','*','$','+','O','D','X']
gameState = {}
state = {}
pid_map = {}

SERVER = socket(AF_INET,SOCK_STREAM)
SERVER.bind(ADDR)


def checkBoundaries():
    global gameState
    global state
    global clients
    global pid_map
    global active_players
    global client_lock
    global state_lock
    global gs_lock

    while True:
        try:
            if len(clients) == 1:
                for client in clients:
                    active_players = 0
                    try:
                        client.send("VICTORY".encode(ENCODING))
                        client.close()
                        break
                    except:
                        continue
            else:
                for client in clients:
                    try:
                        gs_lock.acquire()
                        snake = gameState[client]
                        gs_lock.release()
                        if snake.head.x == MAX_X\
                        or snake.head.y == MAX_Y\
                        or snake.head.x < 1\
                        or snake.head.y < 1:
                            client.send("BYE".encode(ENCODING))
                            del gameState[client]
                            state_lock.acquire()
                            del state[clients[client]]
                            state_lock.release()

                            print(f"{clients[client]} disconnected, Boundaries")

                            client_lock.acquire()
                            del clients[client]
                            client_lock.release()

                            active_players-=1
                            clientExit[client] = True
                            client.close()
                    except:
                        continue
                        # print(state)
        except RuntimeError:
            continue


def removeClient(client):
    global gameState
    global KEY_MAP
    global state
    global clients
    global clientExit
    global active_players
    try:
        client.send("BYE".encode(ENCODING))
        del gameState[client]
        state_lock.acquire()
        del state[clients[client]]
        state_lock.release()

        print(f"{clients[client]} disconnected, Head On Collision")

        client_lock.acquire()
        del clients[client]
        client_lock.release()

        active_players-=1
        clientExit[client] = True
        client.close()
    except:
        print("Connection already closed")

def rules():
    global allClients
    global gameState
    global clients
    global clientExit
    while len(allClients) > 1:
        heads = {}
        for clt in allClients:
            try:
                body = gameState[clt].getBody()
                pid = clients[clt]
                heads[clt] = (body[-1].y, body[-1].x)
            except:
                continue
        for clt, head in heads.items():
            count = 0
            matchings = []
            for clts, hed in heads.items():
                if hed == head:
                    count += 1
                    matchings.append(clts)
            if(len(matchings) > 1):
                for t in matchings:
                    try:
                        pid = clients[t]
                        if(clientExit[pid] == False):
                            removeClient(t)
                    except:
                        continue


def accept_conn():
    global active_players
    global gameState
    global allClients
    global NUM_PLAYERS
    global client_lock
    global state_lock

    while True:
        client, client_addr = SERVER.accept()
        print(f"{client_addr} has connected")
        allClients.append(client)
        player_id = active_players+1
        msg = "PID:"+str(player_id)
        client.send(msg.encode(ENCODING))
        
        client_lock.acquire()
        clients[client] = player_id
        client_lock.release()
        
        
        pid_map[player_id] = client
        clientExit[player_id] = False
        active_players+=1
        client_snake = getSnake(player_id,NUM_PLAYERS)

        gs_lock.acquire()
        gameState[client] = client_snake
        gs_lock.release()


        body = parseBody(gameState[client].getBody())
        data = json.dumps(body)
        
        state_lock.acquire()
        state[player_id] = data
        state_lock.release()
        
        
        data = json.dumps(state) + ";"
        client.send(
            bytes(
                data,
                ENCODING
            )
        )
        addresses[client] = client_addr
        dir_threads[client] = Thread(target=handle_client_direction,args=(client,))
        if(active_players == NUM_PLAYERS):
            handle_All_Clients()


def handle_All_Clients():
    global allClients
    global dir_threads
    global mov_threads
    global broadcast_thread

    for client in allClients:
        dir_threads[client].start()
    Thread(target=broadcastState).start()
    Thread(target=checkBoundaries).start()
    Thread(target=rules).start()
        # mov_threads[client].start()




def handle_client_direction(client):
    global gameState
    global KEY_MAP
    global state
    global clients
    global clientExit
    global active_players
    global client_lock
    global state_lock

    while True and client in clients:
        try:
            event = client.recv(BUFFSIZE).decode(ENCODING)
            if event in KEY_MAP:
                direction = KEY_MAP[event]

                gs_lock.acquire()
                snake = gameState[client]
                snake.change_direction(direction)
                snake.update()
                gs_lock.release()

                body = parseBody(snake.getBody())
                str_body = json.dumps(body)
                player_id = clients[client]

                state_lock.acquire()
                state[player_id] = str_body
                state_lock.release()
        except:
            continue
            

def broadcastState():
    global gameState
    global KEY_MAP
    global state
    global clients
    global clientExit
    global dir_threads
    global mov_threads
    global client_ack
    global client_lock
    global state_lock
    global gs_lock
    
    while True and active_players > 0:
        for client in gameState:
            gs_lock.acquire()
            gameState[client].update()
            gs_lock.release()
        
        sleep(0.005)
        client_lock.acquire()
        for sock in clients:
            try:
                player_id = clients[sock]
                body = parseBody(gameState[sock].getBody())
                str_body = json.dumps(body)
                state[player_id] = str_body
                data = json.dumps(state) + ";"
                # if data is not None:
                sock.send(data.encode(ENCODING))
            except:
                continue
        client_lock.release()
    

if __name__ == "__main__":
    try:
        SERVER.listen(NUM_PLAYERS)
        print(f"Listening on {ADDR}")
        accept_thread = Thread(target=accept_conn)
        accept_thread.start()
    except KeyboardInterrupt:
        accept_thread.join()
        SERVER.close()
        exit(1)
    finally:
        accept_thread.join()
        SERVER.close()
        exit(1)