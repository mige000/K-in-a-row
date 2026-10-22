'''Game_Master_Offline.py based on GameMaster.py

 Updated Oct. 29, 2025. Previously updated
 Jan. 30, 2025 and Nov. 17, 2024.
 See the test function at the end for how to customize
 the runs: choice of games and agents.

(C) 2025, the authors.  Provided for use with this assignment.

'''

from time import sleep, time

from winTesterForK import winTesterForK
from game_types import TTT, FIAR, Cassini

# --- Recording the game ---------------------------------------------------
# A game can be written out in more than one format at once.  Each "recorder"
# is told about the events of the game as they happen and writes them however
# it likes:
#   gameToHTML  -- an HTML page with a picture of the board after every move
#   gameToJSON  -- a JSON transcript that the browser game master can replay,
#                  speaking the utterances aloud
# Turn either off here if you do not want that file.  You should not need to
# change anything else about the recording to do the assignment.
USE_HTML = True
USE_JSON = True


class _Recorders:
    '''Forwards every call to each active recorder, so that the game loop
    below can just say RECORDERS.move(...) once instead of testing a flag
    for each format.'''

    def __init__(self):
        self.list = []

    def __getattr__(self, event_name):
        def fan_out(*args, **kwargs):
            for recorder in self.list:
                getattr(recorder, event_name)(*args, **kwargs)
        return fan_out


RECORDERS = _Recorders()
if USE_HTML:
    import gameToHTML
    RECORDERS.list.append(gameToHTML.HTMLRecorder())
if USE_JSON:
    import gameToJSON
    RECORDERS.list.append(gameToJSON.JSONRecorder())

TIME_PER_MOVE = 1.0 # In seconds
INITIAL_STATE = TTT.initial_state

ALLOW_CERTAIN_IMPORTS = True

# Establish global variables, with defaults for now.
K = None
N = None
M = None
TURN_LIMIT = None

# To be called from WebGameAgent if using the web:
def set_game(game_type):
    global K, GAME_TYPE, TURN_LIMIT, N, M, INITIAL_STATE
    K = game_type.k
    N = game_type.n
    M = game_type.m
    GAME_TYPE = game_type
    TURN_LIMIT = game_type.turn_limit
    INITIAL_STATE = game_type.initial_state

PLAYERX = None
PLAYERO = None
def set_players(px, po):
    global PLAYERX, PLAYERO
    PLAYERX = px
    PLAYERO = po

FINISHED = False
def runGame():
    currentState = INITIAL_STATE
    player1 = PLAYERX
    player2 = PLAYERO

    RECORDERS.start(GAME_TYPE, player1, player2, 1)

    renderCommentary('The Gamemaster says, "Players, introduce yourselves."')
    intro1 = player1.introduce()
    intro2 = player2.introduce()
    renderCommentary('     (Playing X:) ' + intro1)
    renderCommentary('     (Playing O:) ' + intro2)
    RECORDERS.introduction('X', player1, intro1)
    RECORDERS.introduction('O', player2, intro2)

    for player, side, other in ((player1, 'X', player2), (player2, 'O', player1)):
        try:
            player.prepare(GAME_TYPE, side, other.nickname)
        except Exception as e:
            print("Failed to prepare perhaps because: ", e)
            report = ('Player ' + side + ' (' + player.nickname
                      + ') failed to prepare, and loses by default.')
            renderCommentary(report)
            RECORDERS.result(report, winner=('O' if side == 'X' else 'X'))
            report = 'Congratulations to ' + other.nickname + '!'
            renderCommentary(report)
            RECORDERS.result(report)
            RECORDERS.end()
            return

    announcement = "We're playing " + GAME_TYPE.long_name + '.'
    renderCommentary('The Gamemaster says: ' + announcement)
    renderCommentary('The Gamemaster says: Let\'s Play!')
    renderCommentary('The initial state is...')
    RECORDERS.commentary(announcement)
    RECORDERS.commentary("Let's Play!")

    currentRemark = "The game is starting."
    RECORDERS.state(currentState)
    XsTurn = True
    global FINISHED
    FINISHED = False
    turnCount = 0
    printState(currentState)
    while not FINISHED:
        who = currentState.whose_move
        mover = player1 if XsTurn else player2
        XsTurn = not XsTurn

        started = time()
        playerResult = mover.make_move(currentState, currentRemark, TIME_PER_MOVE)
        elapsed = time() - started

        if playerResult is None:
            FINISHED = True; continue
        moveAndState, currentRemark = playerResult
        if moveAndState is None:
            FINISHED = True; continue
        move, currentState = moveAndState[0], moveAndState[1]
        # An agent may return its statistics as a third element; if it does not,
        # they are read off the agent instead.  See gameToJSON.collect_stats.
        returned_stats = moveAndState[2] if len(moveAndState) > 2 else None

        moveReport = "Move is by " + who + " to " + str(move)
        utteranceReport = mover.nickname + ' says: ' + currentRemark
        renderCommentary(moveReport)
        renderCommentary(utteranceReport)
        RECORDERS.move(who, mover, move, currentState, currentRemark,
                       stats=collect_stats(mover, elapsed, returned_stats))

        possibleWin = winTesterForK(currentState, move, K)
        if possibleWin != "No win":
            FINISHED = True
            currentState.finished = True
            printState(currentState)
            renderCommentary(possibleWin)
            RECORDERS.state(currentState, finished=True)
            RECORDERS.result(possibleWin, winner=who)
            RECORDERS.end()
            return

        printState(currentState)
        RECORDERS.state(currentState)
        turnCount += 1
        if turnCount == TURN_LIMIT: FINISHED = True
        else:
            sleep(WAIT_TIME_AFTER_MOVES) # NOT TOO FAST.

    printState(currentState)
    renderCommentary("Game over; it's a draw.")
    RECORDERS.state(currentState, finished=True)
    RECORDERS.result("Game Over; it's a draw", winner=None)
    RECORDERS.end()


def collect_stats(player, elapsed, returned_stats):
    if USE_JSON:
        return gameToJSON.collect_stats(player, elapsed, returned_stats)
    return None


def printState(s):
    global FINISHED
    board = s.board
    who = s.whose_move
    horizontalBorder = "+"+3*M*"-"+"+"
    renderCommentary(horizontalBorder)
    for row in board:
        line = "|"
        for item in row:
            line += " "+item+" "
        line += "|"
        renderCommentary(line)
    renderCommentary(horizontalBorder)
    if not FINISHED:
      renderCommentary("It is "+who+"'s turn to move.\n")

# Temporary function.  Remove when other channels are working.
def renderCommentary(stuff):
    print(stuff)

def render_move_and_state(move, state):
   # NOTE: THIS DEFN WILL BE OVERWRITTEN WHEN USED ON THE WEB.
   print(move, state)

def render_utterance(who, utterance):
   # NOTE: THIS DEFN WILL BE OVERWRITTEN WHEN USED ON THE WEB.
   print(who+' says: '+utterance)

WAIT_TIME_AFTER_MOVES = 0.01
def set_wait_time(t):
    global WAIT_TIME_AFTER_MOVES
    WAIT_TIME_AFTER_MOVES = float(t)

def test():
    # Stand-alone test
    print("Starting stand-alone test of GameMaster.py")
    # Edit this to change what version of K-in-a-Row is used.
    set_game(TTT) # default is Tic-Tac-Toe
    #set_game(FIAR) # Five in a Row
    # Import 1 or 2 agent files here.
    # If using only 1, create 2 instances of it, one of
    # which is a "twin".

    #import yourID_KInARow as h
    import RandomPlayer as h
    px = h.OurAgent()
    po = h.OurAgent(twin=True)
    set_players(px, po)
    print("Players are set.")
    print("Now let's run the game.")
    print("Players will play in DEMO mode (the default).")
    runGame()

if __name__ == '__main__':
    test()
