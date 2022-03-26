import socket
import threading
import sys
import enum

IP = socket.gethostbyname(socket.gethostname())
SIZE = 1024
FORMAT = "utf-8"
TIMEOUT = 1
TIMEOUT_RECHARGING = 5
MAX_USERNAME_LENGTH = 18
MAX_KEY_ID_LENGTH = 3
MAX_CONFIRMATION_CODE_LENGTH = 5
MAX_CLIENT_OK_LENGTH = 10
MAX_CLIENT_RECHARGING_LENGTH = 10
MAX_CLIENT_FULL_POWER_LENGTH = 10
MAX_CLIENT_MESSAGE_LENGTH = 98


class Direction(enum.Enum):
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4


class Coordinate:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y

    def __sub__(self, other):
        x = self.x - other.x
        y = self.y - other.y
        return Coordinate(x, y)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y


def is_integer(x):
    try:
        int(x)
        return True
    except ValueError:
        return False


class Buffer:
    def __init__(self, conn):
        self.conn = conn
        self.buffer = b''

    def get_line(self, max_input_length, timeout):
        while b'\a\b' not in self.buffer:
            if len(self.buffer.decode(FORMAT)) > max_input_length:
                return None
            self.conn.settimeout(timeout)
            try:
                data = self.conn.recv(SIZE)
                #print(f"[DATA] {data.decode(FORMAT)}")
                self.buffer += data
            except socket.timeout:
                self.conn.settimeout(None)
                return None
            self.conn.settimeout(None)
        line, sep, self.buffer = self.buffer.partition(b'\a\b')
        if len(line.decode(FORMAT)) > max_input_length:
            return None
        return line.decode(FORMAT)


class Robot:

    def __init__(self, conn):
        self.username = None
        self.hash_username = None
        self.key_id = None
        self.state = 0
        self.connection = conn
        self.buffer = Buffer(conn)
        self.previous_coordinate = None
        self.direction = None
        self.directions_to_finish = set()
        self.made_straight_move = False

    def __send_message_to_client(self, msg, new_state):
        self.connection.send(msg.encode(FORMAT))
        self.state = new_state

    def __update_directions_to_finish(self, curr_coordinate):
        self.directions_to_finish = set()
        if curr_coordinate.x > 0:
            self.directions_to_finish.add(Direction.WEST)
        elif curr_coordinate.x < 0:
            self.directions_to_finish.add(Direction.EAST)
        if curr_coordinate.y > 0:
            self.directions_to_finish.add(Direction.SOUTH)
        elif curr_coordinate.y < 0:
            self.directions_to_finish.add(Direction.NORTH)

    def __update_direction_after_turning_right(self):
        if self.direction == Direction.NORTH:
            self.direction = Direction.EAST
        elif self.direction == Direction.EAST:
            self.direction = Direction.SOUTH
        elif self.direction == Direction.SOUTH:
            self.direction = Direction.WEST
        else:
            self.direction = Direction.NORTH

    def __update_direction_after_turning_left(self):
        if self.direction == Direction.NORTH:
            self.direction = Direction.WEST
        elif self.direction == Direction.EAST:
            self.direction = Direction.NORTH
        elif self.direction == Direction.SOUTH:
            self.direction = Direction.EAST
        else:
            self.direction = Direction.SOUTH

    def get_username(self):
        username = self.buffer.get_line(MAX_USERNAME_LENGTH, TIMEOUT)
        # if username == None:
        #     todo
        self.username = username
        self.__send_message_to_client("107 KEY REQUEST\a\b", 1)
        return True

    def get_client_key_id(self):
        key_id = self.buffer.get_line(MAX_KEY_ID_LENGTH, TIMEOUT)
        if not is_integer(key_id):
            self.__send_message_to_client("301 SYNTAX ERROR\a\b", -1)
            return False
        if not 0 <= int(key_id) <= 4:
            self.__send_message_to_client("303 KEY OUT OF RANGE\a\b", -1)
            return False
        g = (ord(c) for c in self.username)
        ascii_value = sum(g)
        self.hash_username = (ascii_value * 1000) % 65536
        msg = (self.hash_username + (self.authentication_keys[int(self.key_id)])[0]) % 65536
        self.__send_message_to_client(str(msg), 2)
        return True

    def confirm_client_key(self):
        confirmation_code = self.buffer.get_line(MAX_CONFIRMATION_CODE_LENGTH, TIMEOUT)
        if not is_integer(confirmation_code):
            self.__send_message_to_client("301 SYNTAX ERROR\a\b", -1)
            return False
        if (int(confirmation_code) - (self.authentication_keys[self.key_id])[1]) % 65536 == self.hash_username:
            self.__send_message_to_client("200 OK\a\b", 3)
            return True
        else:
            self.__send_message_to_client("300 LOGIN FAILED\a\b", -1)
            return False

    def make_first_move(self):
        self.__send_message_to_client("102 MOVE\a\b", 4)
        return True

    def make_second_action(self):
        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        curr_coordinate = Coordinate(int(robot_msg[4]), int(robot_msg[8]))
        if curr_coordinate == Coordinate(0, 0):  # we hit the sweet spot
            self.__send_message_to_client("105 GET MESSAGE\a\b", 10)
            return True
        else:
            self.previous_coordinate = curr_coordinate
            self.__send_message_to_client("102 MOVE\a\b", 5)
            return True

    def process_second_move(self):
        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        curr_coordinate = Coordinate(int(robot_msg[4]), int(robot_msg[8]))
        if curr_coordinate == Coordinate(0, 0):
            self.__send_message_to_client("105 GET MESSAGE\a\b", 10)
            return True
        elif curr_coordinate == self.previous_coordinate:
            self.__send_message_to_client("104 TURN RIGHT\a\b", 6)
            return True
        else:
            if curr_coordinate - self.previous_coordinate == Coordinate(0, 1):
                self.direction = Direction.NORTH
            elif curr_coordinate - self.previous_coordinate == Coordinate(1, 0):
                self.direction = Direction.EAST
            elif curr_coordinate - self.previous_coordinate == Coordinate(0, -1):
                self.direction = Direction.SOUTH
            else:
                self.direction = Direction.WEST
            self.__update_directions_to_finish(curr_coordinate)
            # check if we have good direction, if yes than make move, if not than turn right
            if self.direction in self.directions_to_finish:
                self.made_straight_move = True
                self.__send_message_to_client("102 MOVE\a\b", 8)
            else:
                self.made_straight_move = False
                self.__update_direction_after_turning_right()
                self.__send_message_to_client("104 TURN RIGHT\a\b", 8)
            self.previous_coordinate = curr_coordinate
            return True

    def make_second_second_move(self):
        # getting clint_ok message after turning around
        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        self.__send_message_to_client("102 MOVE\a\b", 7)
        return True

    def process_second_second_move(self):
        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        curr_coordinate = Coordinate(int(robot_msg[4]), int(robot_msg[8]))
        if curr_coordinate == Coordinate(0, 0):
            self.__send_message_to_client("105 GET MESSAGE\a\b", 10)
            return True
        if curr_coordinate - self.previous_coordinate == (1, -1):
            self.direction = Direction.SOUTH
        elif curr_coordinate - self.previous_coordinate == (-1, -1):
            self.direction = Direction.WEST
        elif curr_coordinate - self.previous_coordinate == (-1, 1):
            self.direction = Direction.NORTH
        else:
            self.direction = Direction.EAST
        self.__update_directions_to_finish(curr_coordinate)
        # check if we have good direction, if yes than make move, if not than turn right
        if self.direction in self.directions_to_finish:
            self.made_straight_move = True
            self.__send_message_to_client("102 MOVE\a\b", 8)
        else:
            self.made_straight_move = False
            self.__update_direction_after_turning_right()
            self.__send_message_to_client("104 TURN RIGHT\a\b", 8)
        self.previous_coordinate = curr_coordinate
        return True

    def navigate_to_finish(self):
        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        curr_coordinate = Coordinate(int(robot_msg[4]), int(robot_msg[8]))
        if curr_coordinate == Coordinate(0, 0):
            self.__send_message_to_client("105 GET MESSAGE\a\b", 10)
            return True
        self.__update_directions_to_finish(curr_coordinate)
        if curr_coordinate == self.previous_coordinate and self.made_straight_move:
            if self.direction in self.directions_to_finish and len(self.directions_to_finish) == 1:
                self.made_straight_move = False
                self.__update_direction_after_turning_right()
                self.__send_message_to_client("104 TURN RIGHT\a\b", 9)
            else:
                self.made_straight_move = False
                self.__update_direction_after_turning_right()
                self.__send_message_to_client("104 TURN RIGHT\a\b", 8)
        elif self.direction in self.directions_to_finish:
            self.made_straight_move = True
            self.__send_message_to_client("102 MOVE\a\b", 8)
        else:
            self.made_straight_move = False
            self.__update_direction_after_turning_right()
            self.__send_message_to_client("104 TURN RIGHT\a\b", 8)
        self.previous_coordinate = curr_coordinate
        return True


    def take_a_detour(self):
        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        self.__send_message_to_client("102 MOVE\a\b", 9)

        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        self.__update_direction_after_turning_left()
        self.__send_message_to_client("103 TURN LEFT\a\b", 9)

        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        self.__send_message_to_client("102 MOVE\a\b", 9)

        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        self.__send_message_to_client("102 MOVE\a\b", 9)

        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        self.__update_direction_after_turning_left()
        self.__send_message_to_client("103 TURN LEFT\a\b", 9)

        robot_msg = self.buffer.get_line(MAX_CLIENT_OK_LENGTH, TIMEOUT)
        curr_coordinate = Coordinate(int(robot_msg[4]), int(robot_msg[8]))
        self.made_straight_move = True
        self.previous_coordinate = curr_coordinate
        self.__send_message_to_client("102 MOVE\a\b", 8)
        return True

    def get_message_and_log_out(self):
        robot_msg = self.buffer.get_line(MAX_CLIENT_MESSAGE_LENGTH, TIMEOUT)
        self.__send_message_to_client("106 LOGOUT\a\b", 11)
        return False


    def make_action(self):
        return (self.automaton[self.state])(self)

    # state -1: final state, failure, no transitions from here
    # state 0:  initial state, getting username, sending request for key_id
    # state 1:  getting key_id, sending server confirmation
    # state 2:  getting client confirmation code, we calculate hash name and
    #           if it's ok we send last confirm to the client
    # state 3:  making initial move
    # state 4:  getting first coordinate, if it's the 0,0 we pick up message, otherwise make another move
    # state 5:  getting second coordinate, if its 0,0 we pick up message and change state to 10.
    #           if it's the same as previous that means we hit the block and have to turn around (go to state 6)
    #           if its different, we know our way and are ready for navigating to 0,0 (state 8)
    # state 6:  we made the turn. now we have to make last move to figure out our direction (state 7)
    # state 7:  we made a valid second move and now we compute our direction. we start navigating to 0,0 (go to state 8)
    # state 8:  we are navigating the client until it finds the 0,0. then we pick up the message
    # state 9:  special state when we have to move to finish in only one direction, but the obstacle is in front of us,
    #           so we have to take a detour. (right, move, left, move, move, left, move, right) than we
    #           switch to state 8 again
    # state 10: getting message from client and loging out
    # state 11: final state, success, no transitions from here
    automaton = {
        0: get_username,
        1: get_client_key_id,
        2: confirm_client_key,
        3: make_first_move,
        4: make_second_action,
        5: process_second_move,
        6: make_second_second_move,
        7: process_second_second_move,
        8: navigate_to_finish,
        9: take_a_detour,
        10: get_message_and_log_out
    }

    authentication_keys = {
        0: (23019, 32037),
        1: (32037, 29295),
        2: (18789, 13603),
        3: (16443, 29533),
        4: (18189, 21952)
    }


def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected")

    connected = True
    robot = Robot(conn)
    while connected:
        connected = robot.make_action()
    conn.close()


def main():
    port = int(sys.argv[1])
    print("[STARTING] Server is starting...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((IP, port))
    server.listen()
    print(f"[LISTENING] Server is listening on {IP}:{port}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


if __name__ == "__main__":
    main()
