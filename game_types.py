'''game_types.py

Defines a State class useful in all K-in-a-Row games.
Defines a Game_Type class describing game parameters.
Also defines 3 specific game instances: TTT, FIAR, and Cassini.

Board token convention (used throughout all game files):
  ' '  (space)  -- empty square, available for play
  'X'           -- occupied by player X
  'O'           -- occupied by player O
  '-'           -- forbidden square (cannot be played)

Key invariant: the win length k is stored in Game_Type, NOT in State.
Your static_eval function must receive a game_type argument (or have
stored one from prepare) in order to know the value of k.
'''

#GAME_TYPE = None # Used in State.__str__

class State:
    '''Represents a game position in any K-in-a-Row variant.

    Attributes:
      board        -- list of lists of strings (see token convention above)
      whose_move   -- 'X' or 'O', indicating whose turn it is
      finished     -- True once a win has been detected (set by the game master)

    To create an initial state:
      State(initial_state_data=(board_2d_list, whose_move_string))
    To copy a state before modifying it (always copy before applying a move):
      State(old=existing_state)
    '''
    def __init__(self, old=None, initial_state_data=None):
        if old==None:
            if initial_state_data==None:
                print("No old state or initial state data given to State().")
                raise Exception("in game_types.py, State() needs args.")
            else:
                # Translate string into initial state.
                self.board = initial_state_data[0]
                self.whose_move = initial_state_data[1]
        else:
            self.board = deep_copy(old.board)
            self.whose_move = old.whose_move # Changing whose move not done here.
        self.finished = False # Set to True if a win is detected.
        
    def __str__(self):
        text = ''
        M = len(self.board[0])
        horizontalBorder = "+"+3*M*"-"+"+\n"
        text += horizontalBorder
        for row in self.board:
            line = "|"
            for item in row:
                if item==' ': item = "."
                line += " "+item+" "
            line += "|\n"
            text += line
        text += horizontalBorder
        if not self.finished:
            text += "It is "+self.whose_move+"'s turn to move.\n"
        return text

            
    def change_turn(self):
        # Modify whose turn it is, in this state.
        if self.whose_move=="X": self.whose_move="O"
        else: self.whose_move="X"

def deep_copy(board_data):
    return [row[:] for row in board_data]

class Game_Type:
    '''Describes the parameters of a K-in-a-Row game variant.

    Key attributes:
      k            -- number of tokens in a line required to win
      n            -- number of rows on the board
      m            -- number of columns on the board
      initial_state -- the starting State for this game type
      long_name    -- human-readable name (used in transcripts)
      short_name   -- abbreviated name (used in filenames)
      turn_limit   -- maximum number of turns before the game is declared a draw
      default_time_per_move -- suggested time limit in seconds

    Note: k is the critical value your static_eval needs. It is NOT in State.
    '''
    def __init__(self, long_name, short_name, k, n, m, initial_state_data, turn_limit, default_time_per_move):
        self.long_name = long_name
        self.short_name = short_name
        self.k = k
        self.n = n
        self.m = m
        self.initial_state = State(initial_state_data = initial_state_data)
        self.turn_limit = turn_limit
        self.default_time_per_move = default_time_per_move

    def __str__(self):
        text = ''
        text += self.short_name + " is a Game_Type with k = "+str(self.k)
        return text
        
TTT_INITIAL_STATE_DATA = \
              [[[' ',' ',' '],
                [' ',' ',' '],
                [' ',' ',' ']], "X"]

TTT = Game_Type("Tic-Tac-Toe",
                 "TTT",
                 3,
                 3,
                 3,
                 TTT_INITIAL_STATE_DATA,
                 9,
                 1)

FIVE_INITIAL_STATE_DATA = \
              [[['-',' ',' ',' ',' ',' ','-'],
                [' ',' ',' ',' ',' ',' ',' '],
                [' ',' ',' ',' ',' ',' ',' '],
                [' ',' ',' ',' ',' ',' ',' '],
                [' ',' ',' ',' ',' ',' ',' '],
                [' ',' ',' ',' ',' ',' ',' '],
                ['-',' ',' ',' ',' ',' ','-']], "X"]

FIAR = Game_Type("Five-in-a-Row on a Seven-by-Seven Board with Corners Forbidden",
                 "5-in-a-Row",
                 5,
                 7,
                 7,
                 FIVE_INITIAL_STATE_DATA,
                 45,
                 0.25)

CASSINI_INITIAL_STATE_DATA = \
              [[[' ',' ',' ',' ',' ',' ',' ',' '],
                [' ','O',' ',' ',' ',' ',' ',' '],
                [' ',' ',' ','-','-',' ',' ',' '],
                [' ',' ','-','-','-','-',' ',' '],
                [' ',' ',' ','-','-',' ',' ',' '],
                [' ',' ',' ',' ',' ',' ',' ',' '],
                [' ',' ',' ',' ',' ',' ','O',' ']], "X"]

Cassini = Game_Type("Cassini (5 in a row that does not hit Saturn)",
                    "Cassini",
                    5,
                    7,
                    8,
                    CASSINI_INITIAL_STATE_DATA,
                    44,
                    1)

def test():
    global GAME_TYPE
    GAME_TYPE = Cassini
    print(GAME_TYPE.initial_state)

if __name__ == "__main__":
    test()
    
