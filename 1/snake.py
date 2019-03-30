import curses
from curses import KEY_RIGHT, KEY_LEFT, KEY_DOWN, KEY_UP
from random import randint,choice


#Dimensions for the game
BOARD_WIDTH = 60
BOARD_HEIGHT = 25
MAX_X = BOARD_WIDTH - 1
MAX_Y = BOARD_HEIGHT - 1
SNAKE_LENGTH = 4
SNAKE_X = int(MAX_X/2)
SNAKE_Y = int(MAX_Y/2)
# SNAKE_Y = randint(SNAKE_LENGTH,MAX_Y)
TIMEOUT = 100

class Body(object):
    def __init__(self,x,y,char='~'):
        self.x = x
        self.y = y
        self.char = char
    
    @property
    def getCoord(self):
        return self.x,self.y

class Snake(object):

    REV_DIR_MAP = {
        KEY_UP: KEY_DOWN,
        KEY_DOWN: KEY_UP,
        KEY_LEFT: KEY_RIGHT,
        KEY_RIGHT: KEY_LEFT
    }

    def __init__(self,x,y,hChar,dir=None):
        self.body_list = []
        self.timeout = TIMEOUT

        # Initialise snake body from starting coordinates
        for i in range(SNAKE_LENGTH,0,-1):
            self.body_list.append(Body(x-i,y))

        #Add snake head to the body at starting coordinates
        self.body_list.append(Body(x,y,hChar))

        # self.window = window
        self.direction = None
        if dir == None:
            self.direction = choice([KEY_RIGHT, KEY_LEFT, KEY_DOWN, KEY_UP])
        else:
            self.direction = dir
        self.last_head_coord = (x,y)
        self.direction_map = {
            KEY_UP: self.move_up,
            KEY_DOWN: self.move_down,
            KEY_LEFT: self.move_left,
            KEY_RIGHT: self.move_right,
        }

    def add_body(self,body):
        self.body_list.extend(body)
    
    #Check for collision of head and body of snake
    @property
    def collision(self):
        return any(
            [body.getCoord == self.head.getCoord for body in self.body_list[:-1]]
        )
    
    def update(self):
        tail = self.body_list.pop(0)
        tail.x = self.body_list[-1].x
        tail.y = self.body_list[-1].y
        self.body_list.insert(-1,tail)
        self.last_head_coord = (self.head.x,self.head.y)
        self.direction_map[self.direction]()

    def change_direction(self,direction):
        if direction != Snake.REV_DIR_MAP[self.direction]: #Change direction only if head is not moving into body
            self.direction = direction
    
    # def render(self):
    #     for body in self.body_list:
    #         self.window.addstr(body.y,body.x,body.char)
    
    @property
    def head(self):
        return self.body_list[-1]

    @property
    def coord(self):
        return (self.head.x,self.head.y)

    # @property
    def getBody(self):
        return self.body_list

    def move_up(self):
        self.head.y -= 1
        if self.head.y < 1:
            self.head.y = MAX_Y

    def move_down(self):
        self.head.y += 1
        if self.head.y > MAX_Y:
            self.head.y = 1

    def move_left(self):
        self.head.x -= 1
        if self.head.x < 1:
            self.head.x = MAX_X

    def move_right(self):
        self.head.x += 1
        if self.head.x > MAX_X:
            self.head.x = 1