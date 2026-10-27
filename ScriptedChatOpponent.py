'''ScriptedChatOpponent.py

A minimal opponent agent used only to generate a demonstration transcript.
It plays legal moves (same move_gen approach as RandomPlayer.py) but says
pre-scripted lines on specific turns instead of random banter -- in
particular, it literally asks the two mandatory trigger phrases from Part
II ("Tell me how you did that" and "What's your take on the game so
far?") early enough in a Tic-Tac-Toe game that they are guaranteed to
reach the other player before the game can possibly end.

Not part of the graded submission; just a tool for generating a transcript
that exercises specific Part II features on demand.
'''

from agent_base import KAgent
from game_types import State
from random import randint

SCRIPTED_LINES = [
    "Tell me how you did that",
    "What's your take on the game so far?",
    "ez tho ngl",
    "hmm interesting",
]


class OurAgent(KAgent):

    def __init__(self, twin=False):
        self.twin = twin
        self.nickname = 'Chatty'
        self.long_name = 'Chatty the Scripted Opponent'
        self.my_move_count = 0
        self.playing_mode = KAgent.DEMO

    def introduce(self):
        return "Hi, I'm Chatty. I ask a lot of questions."

    def prepare(self, game_type, what_side_to_play, opponent_nickname,
                expected_time_per_move=0.1, utterances_matter=True):
        self.my_move_count = 0
        return "OK"

    def make_move(self, state, current_remark, time_limit=1000,
                  use_alpha_beta=True, use_zobrist_hashing=False,
                  max_ply=3, special_static_eval_fn=None):
        board = state.board
        n = len(board)
        m = len(board[0])
        blanks = [(i, j) for i in range(n) for j in range(m)
                 if board[i][j] == ' ']
        i, j = blanks[randint(0, len(blanks) - 1)]
        new_state = State(old=state)
        new_state.board[i][j] = state.whose_move
        new_state.change_turn()

        line = (SCRIPTED_LINES[self.my_move_count]
               if self.my_move_count < len(SCRIPTED_LINES) else "ok")
        self.my_move_count += 1
        return [[(i, j), new_state], line]
