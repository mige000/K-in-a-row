'''
agent_base.py

Base class to be subclassed to create an agent for playing
"K-in-a-Row with Forbidden Squares" and related games.


THIS IS A TEMPLATE WITH STUBS FOR THE REQUIRED FUNCTIONS.

IMPORT IT INTO YOUR OWN AGENT MODULE AND SUBCLASS KAgent.
OVERRIDE METHODS AS NEEDED TO CREATE YOUR OWN AGENT.

YOU CAN PUT INTO YOUR MODULE WHATEVER ADDITIONAL FUNCTIONS 
YOU NEED IN ORDER TO ACHIEVE YOUR AGENT IMPLEMENTATION.

Updated Oct. 29, 2025 to handle 3 modes of game-play.
Additional modifications were made on April 20, 2026,
including changing the stats data structure from list 
to dict.
'''

VERBOSE = False

AUTHORS = 'Jane Smith and Laura Lee' # Override this in your agent file.
STUDENT_IDS = ['jsmith99', 'llee2039']

import time

# Base class for all K-in-a-Row agents.

class KAgent:

    # Playing modes:
    DEMO = 0
    COMPETITION = 1
    AUTOGRADER = 2

    def __init__(self, twin=False):
        self.twin=False
        self.nickname = 'Nic'
        if twin: self.nickname = 'Mic'
        self.long_name = 'Templatus Skeletus'
        if twin: self.long_name += ' II'
        self.persona = 'bland'
        self.voice_info = {'Chrome': 10, 'Firefox': 2, 'other': 0}
        self.playing = "don't know yet" # e.g., "X" or "O".
        self.image = None
        self.alpha_beta_cutoffs_this_turn = -1
        self.num_static_evals_this_turn = -1
        self.zobrist_table_num_entries_this_turn = -1
        self.zobrist_table_num_hits_this_turn = -1
        self.current_game_type = None
        self.playing_mode = KAgent.DEMO

    def introduce(self):
        intro = '\nMy name is Templatus Skeletus.\n'+\
            '"An instructor" made me.\n'+\
            'Somebody please turn me into a real game-playing agent!\n' 
        return intro

    def nickname(self):
        return self.nickname

    def set_playing_mode(self, mode):
        # Can be called by a game-master or autograder
        self.playing_mode = mode
 
    # Receive and acknowledge information about the game from
    # the game master:
    def prepare(
            self,
            game_type,
            what_side_to_play,
            opponent_nickname,
            expected_time_per_move = 0.1, # Time limits can be
                                          # changed mid-game by the game master,
                                          # via the make_move method.
            utterances_matter = True):    # If False, just return 'OK' for each utterance
                                          # and do not import any LLM modules..

       # Write code to save the relevant information in variables
       # local to this instance of the agent.
       # Game-type info can be in global variables.
       if VERBOSE: print("Change this to return 'OK' when ready to test the method.")
       return "Not-OK"
                
    def make_move(self, current_state, current_remark, time_limit=1000,
                  use_alpha_beta=True,
                  use_zobrist_hashing=False, max_ply=3,
                  special_static_eval_fn=None):  # Used in AUTOGRADER mode.
        if VERBOSE: print("make_move has been called")

        if VERBOSE: print("code to compute a good move should go here.")
        # Here's a placeholder:
        a_default_move = [0, 0] # This might be legal ONCE in a game,
        # if the square is not forbidden or already occupied.
    
        new_state = current_state # This is not allowed, and even if
        # it were allowed, the newState should be a deep COPY of the old.
    
        new_remark = "I need to think of something appropriate.\n" +\
        "Well, I guess I can say that this move is probably illegal."

        if VERBOSE: print("Returning from make_move")
        if not self.playing_mode == KAgent.AUTOGRADER:
            # We are playing in either DEMO mode or COMPETITION mode:
            return [[a_default_move, new_state], new_remark]
        
        # We are playing in AUTOGRADER mode, so return statistics.
        # Dictionary of statistics returned in AUTOGRADER mode:
        # Here -1 indicates that no measurement has been made yet.
        stats = {
        # KEY                                      INTEGER VALUE'S MEANING
        'alpha_beta_cutoffs_this_turn': -1,        # number of alpha-beta cutoffs this move
        'num_static_evals_this_turn': -1,          # number of static evaluations performed
        'zobrist_table_num_entries_this_turn': -1, # entries written to Zobrist hash table
        'zobrist_table_num_hits_this_turn': -1,    # successful Zobrist table lookups this turn
        'zobrist_num_useful_hits_for_minimax': -1, # number of Zobrist hits that had enough ply to be used in minimax.
        'zobrist_num_useful_hits_for_ordering': -1 # number of Zobrist hits used in ordering children for alpha-beta.
        }
        # Modify the stats dictionary as needed to provide meaningful results.

        return [[a_default_move, new_state]+[stats], new_remark]

    # The main adversarial search function:
    def minimax(
            self,
            state,
            depth_remaining,
            pruning=False,
            alpha=None,
            beta=None):
        if VERBOSE: print("Calling minimax. We need to implement its body.")

        default_score = 0 # Value of the passed-in state. Needs to be computed.
    
        return [default_score, "my own optional stuff", "more of my stuff"]
        # Only the score is required here but other stuff can be returned
        # in the list, after the score, in case you want to pass info
        # back from recursive calls that might be used in your utterances,
        # stats, etc. 
 
    def static_eval(self, state, game_type=None):
        if VERBOSE: print('calling static_eval. Its value needs to be computed!')
        # Values should be higher when the states are better for X,
        # lower when better for O.
        return 0
 

GAME_TYPE = None  # not known yet.
