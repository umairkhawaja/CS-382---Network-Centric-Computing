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
        snake = Snake(5,2,heads[active_players-1],KEY_RIGHT)
    elif pid == 2:
        snake = Snake(BOARD_WIDTH - 6 ,3,heads[active_players-1],KEY_LEFT)
    elif pid == 3:
        snake = Snake(5,BOARD_HEIGHT - 6,heads[active_players-1],KEY_RIGHT)        
    elif pid == 4:
        snake = Snake(BOARD_WIDTH - 6 ,BOARD_HEIGHT - 6,heads[active_players-1],KEY_LEFT)
    elif pid == 5:
        snake = Snake(BOARD_WIDTH//2,BOARD_HEIGHT - 6,heads[active_players-1],KEY_UP)
    else:
        snake = Snake(BOARD_WIDTH//2 ,5,heads[active_players-1],KEY_DOWN)

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
# LUMS = '10.130.62.83'
# PORT = 4151
PORT = int(sys.argv[2])
NUM_PLAYERS = int(sys.argv[3])
ENCODING = "utf8"

clients = {}
addresses = {}
BUFFSIZE = 512
ADDR = (HOST,PORT)


dir_threads = {}

client_lock = Lock()
state_lock = Lock()
gs_lock = Lock()


active_threads = []

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
            if len(clients) == 1 and active_players == 1:
                for client in clients:
                    active_players = 0
                    print(f'{clients[client]} wins boundaries!')
                    # try:
                    client.send("VICTORY".encode(ENCODING))
                    del clients[client]
                    # except:
                        # continue
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
                            removeClient(client)
                    except BrokenPipeError:
                        continue
        except RuntimeError:
            continue
        except KeyError:
            continue
        except BrokenPipeError:
            continue


def removeClient(client):
    global gameState
    global KEY_MAP
    global state
    global clients
    global active_players
    global state_lock
    global gs_lock

    try:
        client.send("BYE".encode(ENCODING))

        gs_lock.acquire()
        state_lock.acquire()
        client_lock.acquire()

        del gameState[client]
        del state[clients[client]]
        print(f"{clients[client]} disconnected")
        del clients[client]

        gs_lock.release()
        state_lock.release()
        client_lock.release()

        active_players-=1
        client.close()
    except:
        print("Connection already closed")



def checkCollisions():
    global allClients
    global gameState
    global clients
    global clientExit
    global gs_lock
    while len(clients) > 1:
        current_state = gameState.copy()
        try:
            for client in current_state:
                attacker = current_state[client]
                for  client2 in current_state:
                    if client != client2:
                        victim = current_state[client2]
                        victimBody = [[body.x,body.y] for body in victim.getBody()]
                        if attacker.coord == victim.coord:
                            removeClient(client)
                            removeClient(client2)
                        elif list(attacker.coord) in victimBody:
                            try:
                                print(f'Clash detected {clients[client]} clashed into {clients[client2]} at {attacker.coord} ==> {victimBody}')
                            except KeyError:
                                continue
                            removeClient(client)
                            if active_players == 1:
                                print(f'{clients[client]} wins collisions!')
                                client.send("VICTORY".encode(ENCODING))
                                del clients[client]
                                return
        except RuntimeError:
            print("Oops")
            continue
        except OSError:
            print("OS Error: Check Collisions")

def accept_conn():
    global active_players
    global gameState
    global NUM_PLAYERS
    global client_lock
    global state_lock
    global state
    global addresses
    global pid_map

    while active_players < NUM_PLAYERS:
        client, client_addr = SERVER.accept()
        print(f"{client_addr} has connected")
        active_players+=1
        player_id = active_players
        client_lock.acquire()
        clients[client] = player_id
        client_lock.release()
        
        pid_map[player_id] = client
        
        client_snake = getSnake(player_id,NUM_PLAYERS)


        gs_lock.acquire()
        gameState[client] = client_snake
        gs_lock.release()

        body = parseBody(gameState[client].getBody())

        str_body = json.dumps(body)
        msg = "PID:"+str(player_id)+";"+"INITIAL_POS:"+str_body+";"
        client.send(msg.encode(ENCODING))

        state_lock.acquire()
        state[player_id] = str_body
        state_lock.release()
        
        addresses[client] = client_addr
        dir_threads[client] = Thread(target=handle_client_direction,args=(client,))

        if(active_players == NUM_PLAYERS):
            handle_All_Clients()


def handle_All_Clients():
    global dir_threads
    global accept_threads

    for client in clients:
        dir_threads[client].start()
    
    t1 = Thread(target=broadcastState)
    t2 = Thread(target=checkBoundaries)
    t3 = Thread(target=checkCollisions)
    active_threads.extend([t1,t2,t3])
    t1.start()
    t2.start()
    t3.start()




def handle_client_direction(client):
    global gameState
    global KEY_MAP
    global state
    global clients
    global active_players
    global client_lock
    global state_lock
    
    while client in clients:
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
            elif event == "27":
                removeClient(client)
                return
        except OSError:
            print("OS Error: Handle Direction")
            continue
            

def broadcastState():
    global gameState
    global KEY_MAP
    global state
    global clients
    global client_lock
    global state_lock
    global gs_lock
    
    while True:
        current_state = gameState.copy()
        try:
            for client in current_state:
                current_state[client].update()

            sleep(0.05) # COntrol Speed from here. Removing this line makes game too fast

            client_lock.acquire()
            for sock in clients:
                player_id = clients[sock]
                body = parseBody(current_state[sock].getBody())
                str_body = json.dumps(body)
                state[player_id] = str_body
                data = json.dumps(state) + ";"
                try:
                    sock.send(data.encode(ENCODING))
                except BrokenPipeError:
                    print(f"Err broadcasting to {sock}")
                    continue
                except OSError:
                    print(f"Err broadcasting to {sock}")
                    continue
            client_lock.release()
        except RuntimeError:
            print("RuntimeError: Broadcast")
    

if __name__ == "__main__":
    try:
        SERVER.listen(NUM_PLAYERS)
        print(f"Listening on {ADDR}")
        accept_thread = Thread(target=accept_conn)
        accept_thread.start()
    except KeyboardInterrupt:
        accept_thread.join()
        for thread in active_threads:
            thread.join()
        SERVER.close()
        exit(1)
    finally:
        accept_thread.join()
        SERVER.close()
        exit(1)