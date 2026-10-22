''' autograder.py

Student self-check autograder for K-in-a-Row agents.

Run from your working directory with:
    python3 autograder.py

Edit the AGENT_FILE line near the top to match your submission file name
(omit the .py extension).

Tests and point values (match the course grading outline):

  PART I — Code for Playing K-in-a-Row  (20 pts autograded)
    T0: Load and instantiate agent      (0 pts -- gates all other tests)
    T1: prepare and introduce           (2 pts)
    T2: Full TTT game play-through      (4 pts game validity)
    T3: Static evaluation ordering      (4 pts)
    T4: Minimax without pruning         (5 pts)
    T5: Alpha-beta pruning              (5 pts)

  PART II — Code for Dialog  (6 of 20 pts autograded here)
    T2: Utterances non-empty            (6 pts, checked during game play-through)
    Remaining 14 pts in Part II are TA-graded from your game transcript.

  Total autograded here: 26 pts
  Remaining 74 pts (Part II TA portion + Part III Learning Diary) are staff-graded.

NOTE: The official course autograder may use different test states or
additional tests.  Passing all tests here is a strong indicator but
does not guarantee a full score on the official autograder.
'''

# ------------------------------------------------------------------
# Change this to match YOUR agent file name (no .py extension):
AGENT_FILE = 'yourID_KInARow'
# ------------------------------------------------------------------

import importlib
import time
import game_types
from agent_base import KAgent
import spec_static_by_table
from winTesterForK import winTesterForK
import RandomPlayer as random_player_module


# =====================================================================
# Test States
# =====================================================================

# --- Tic-Tac-Toe states for static eval (A = best for O, E = best for X) ---

A = game_types.State(initial_state_data = \
    [[['X',' ','O'],
      [' ','O','X'],
      ['O',' ','X']], "X"])   # O wins diagonally

B = game_types.State(initial_state_data = \
    [[['X',' ','O'],
      ['X',' ',' '],
      ['O','X',' ']], "O"])   # Good for O

C = game_types.State(initial_state_data = \
    [[['X',' ','O'],
      [' ',' ',' '],
      [' ',' ',' ']], "X"])   # Neutral

D = game_types.State(initial_state_data = \
    [[['O','X','X'],
      [' ',' ','O'],
      ['X','O',' ']], "X"])   # Good for X

E = game_types.State(initial_state_data = \
    [[['X','O','O'],
      ['X',' ','X'],
      ['X',' ','O']], "O"])   # X wins column 0

# --- Cassini states for static eval (F = best for O, J = best for X) ---

F = game_types.State(initial_state_data = \
    [[[' ',' ',' ',' ',' ',' ',' ','X'],
      [' ','O','O','O','O','O',' ',' '],
      [' ',' ',' ','-','-',' ',' ',' '],
      [' ',' ','-','-','-','-','X','X'],
      [' ',' ',' ','-','-',' ',' ',' '],
      [' ','X','X',' ',' ',' ',' ',' '],
      [' ',' ',' ',' ',' ',' ','O',' ']], "X"])   # O wins in row 1

G = game_types.State(initial_state_data = \
    [[[' ',' ',' ',' ',' ',' ',' ','X'],
      [' ','O','O',' ','O','O',' ',' '],
      [' ','O',' ','-','-',' ',' ',' '],
      [' ',' ','-','-','-','-','X','X'],
      [' ',' ',' ','-','-',' ',' ',' '],
      [' ','X','X',' ',' ',' ',' ',' '],
      [' ',' ',' ',' ',' ','O','O',' ']], "X"])   # Good for O

H = game_types.State(initial_state_data = \
    [[[' ',' ',' ',' ',' ',' ',' ',' '],
      [' ','O',' ',' ',' ',' ','O','X'],
      [' ',' ',' ','-','-',' ',' ',' '],
      [' ',' ','-','-','-','-',' ',' '],
      [' ',' ',' ','-','-',' ',' ',' '],
      [' ','X',' ',' ',' ',' ','X',' '],
      ['O',' ',' ',' ',' ',' ','O',' ']], "O"])   # Roughly neutral

I = game_types.State(initial_state_data = \
    [[[' ',' ',' ','O',' ',' ',' ','X'],
      [' ','O',' ',' ',' ','O','O','X'],
      ['O',' ',' ','-','-','O',' ','X'],
      [' ',' ','-','-','-','-','X',' '],
      [' ',' ',' ','-','-','X',' ',' '],
      [' ','X','X',' ',' ',' ',' ',' '],
      [' ',' ','O',' ',' ',' ','O',' ']], "X"])   # Good for X

J = game_types.State(initial_state_data = \
    [[[' ','O',' ',' ',' ',' ',' ','O'],
      [' ','O',' ',' ',' ',' ',' ','O'],
      [' ','O',' ','-','-',' ',' ',' '],
      [' ',' ','-','-','-','-','X','O'],
      [' ',' ',' ','-','-',' ',' ',' '],
      [' ','X','X','X','X','X',' ',' '],
      [' ',' ',' ',' ',' ',' ','O',' ']], "O"])   # X wins in row 5

# --- Minimax / alpha-beta test state ---
# It is O's turn.  Blank squares in row-major order: (1,1), (1,2), (2,0), (2,1).
# Correct best move for O with the special evaluator at depth 2: (1, 2).
# Plain-minimax leaf count (row-major ordering): 12.
# Alpha-beta leaf count   (row-major ordering):  8.

MM_TEST_STATE = game_types.State(initial_state_data = \
    [[['O','O','X'],
      ['X',' ',' '],
      [' ',' ','X']], "O"])


# =====================================================================
# Helper Functions
# =====================================================================

def count_inversions(lst):
    '''Return the number of pairs (i, j) with i < j where lst[i] >= lst[j].'''
    n = len(lst)
    c = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            if lst[i] >= lst[j]:
                c += 1
    return c


def print_inversions(vals, labels):
    '''Print each inverted pair from vals/labels (only called when inversions > 0).'''
    for i in range(len(vals) - 1):
        for j in range(i + 1, len(vals)):
            if vals[i] >= vals[j]:
                print("  Inverted: {} ({}) >= {} ({})".format(
                    labels[i], vals[i], labels[j], vals[j]))


def validate_make_move_result(result, old_state, label):
    '''
    Check that a value returned by make_move has the required structure.
    Returns (is_valid, error_message).
    '''
    if not isinstance(result, list) or len(result) < 2:
        return False, label + ": make_move must return a list of length >= 2."
    move_and_state = result[0]
    utterance = result[1]
    if not isinstance(utterance, str):
        return False, label + ": result[1] (the utterance) must be a string, got: " + repr(type(utterance))
    if not isinstance(move_and_state, list) or len(move_and_state) < 2:
        return False, label + ": result[0] must be a list of length >= 2."
    move = move_and_state[0]
    new_state = move_and_state[1]
    if not hasattr(move, '__len__') or len(move) != 2:
        return False, label + ": The move must be a pair (i, j); got: " + repr(move)
    try:
        i, j = int(move[0]), int(move[1])
    except (TypeError, ValueError):
        return False, label + ": Move coordinates must be integers; got: " + repr(move)
    if not (hasattr(new_state, 'board') and hasattr(new_state, 'whose_move')):
        return False, label + ": result[0][1] must be a State object (needs .board and .whose_move)."
    if new_state is old_state:
        return False, (label + ": make_move returned the SAME State object it received.\n"
                       "  Always use State(old=current_state) to make a deep copy before modifying.")
    expected = 'O' if old_state.whose_move == 'X' else 'X'
    if new_state.whose_move != expected:
        return False, (label + ": whose_move was not toggled correctly.\n"
                       "  After " + old_state.whose_move + " moves, new state should show "
                       + expected + "'s turn; got: " + repr(new_state.whose_move))
    return True, ""


# =====================================================================
# Game Loop (used by T2)
# =====================================================================

def run_one_game(student_agent, random_agent, student_plays, game_type):
    '''
    Run one complete game of game_type.
      student_plays: 'X' or 'O'
    Returns (passed, game_pts, utt_ok, messages).
      passed:   True if no exception or format error occurred.
      game_pts: 2 if passed, else 0.
      utt_ok:   True if every student utterance was a non-empty string.
    '''
    messages = []
    utt_issues = []
    K = game_type.k
    current_state = game_types.State(old=game_type.initial_state)
    remark = "Let's play!"

    for turn in range(game_type.turn_limit):
        whose = current_state.whose_move
        is_student = (whose == student_plays)
        label = "turn {}, {}'s move".format(turn + 1, whose)

        try:
            if is_student:
                result = student_agent.make_move(current_state, remark, 5.0)
            else:
                result = random_agent.make_move(current_state, remark, 5.0)
        except Exception as e:
            messages.append("  EXCEPTION on {}: {}".format(label, e))
            messages.append("  Board at time of failure:\n" + str(current_state))
            return False, 0, False, messages

        if result is None or result[0] is None:
            messages.append("  make_move returned None on {}.".format(label))
            return False, 0, False, messages

        # Validate format only for student moves (RandomPlayer is trusted).
        if is_student:
            ok, err = validate_make_move_result(result, current_state, label)
            if not ok:
                messages.append("  FORMAT ERROR on " + err)
                return False, 0, False, messages
            # Check utterance non-emptiness for Part II scoring.
            utt = result[1] if isinstance(result[1], str) else ""
            if not utt.strip():
                utt_issues.append("  turn {}: utterance was empty or whitespace-only.".format(turn + 1))

        move = result[0][0]
        new_state = result[0][1]
        remark = result[1] if isinstance(result[1], str) else ""
        current_state = new_state

        try:
            win_result = winTesterForK(current_state, move, K)
        except Exception as e:
            messages.append("  winTesterForK raised an exception on {}: {}".format(label, e))
            win_result = "No win"

        if win_result != "No win":
            messages.append("  Game ended on turn {}: {}".format(turn + 1, win_result))
            utt_ok = (len(utt_issues) == 0)
            if utt_issues:
                messages.extend(utt_issues)
            return True, 2, utt_ok, messages

    messages.append("  Game reached turn limit -- draw.")
    utt_ok = (len(utt_issues) == 0)
    if utt_issues:
        messages.extend(utt_issues)
    return True, 2, utt_ok, messages


# =====================================================================
# T0: Load Agent
# =====================================================================

def load_agent(agent_file):
    '''Try to import the agent module and create OurAgent(). Gates all tests.'''
    print("\n" + "=" * 60)
    print("T0: Loading Agent")
    print("=" * 60)
    try:
        p = importlib.import_module(agent_file)
    except Exception as e:
        print("FAILED to import '{}': {}".format(agent_file, e))
        print("Check that your file name matches AGENT_FILE and has no syntax errors.")
        return None, None
    try:
        agent = p.OurAgent()
    except Exception as e:
        print("FAILED to instantiate OurAgent(): " + str(e))
        print("Make sure your class is named OurAgent and __init__ takes no required args.")
        return None, None
    print("Loaded:   " + agent_file)
    print("Nickname: " + str(agent.nickname))
    for attr in ('AUTHORS', 'STUDENT_IDS'):
        if hasattr(p, attr):
            print("{}: {}".format(attr, getattr(p, attr)))
        else:
            print("WARNING: module attribute '{}' not found.".format(attr))
    print("T0 passed.")
    return p, agent


# =====================================================================
# T1: prepare and introduce
# =====================================================================

def test_prepare_and_introduce(agent, agent_module):
    '''Test prepare (must return "OK") and introduce (non-empty string). 2 pts.'''
    print("\n" + "=" * 60)
    print("T1: Prepare and Introduce  (2 points)")
    print("=" * 60)
    score = 0.0

    # --- prepare ---
    print("\n--- prepare ---")
    try:
        response = agent.prepare(game_types.TTT, 'X', 'Opponent')
    except Exception as e:
        print("EXCEPTION during prepare: " + str(e))
        print("Fix prepare so it runs without exceptions before testing further.")
        return 0.0
    if response == 'OK':
        print("prepare returned 'OK'.  (+1 pt)")
        score += 1.0
    else:
        print("prepare returned {!r} instead of 'OK'.".format(response))
        print("Return the exact string 'OK' at the end of your prepare method.")

    # --- D5: current_game_type saved? ---
    if hasattr(agent, 'current_game_type') and agent.current_game_type is not None:
        print("agent.current_game_type is set after prepare.  Good.")
    else:
        print("NOTE: agent.current_game_type is None (or not set) after prepare.")
        print("  Save game_type in prepare so static_eval works in DEMO/COMPETITION mode.")

    # --- introduce ---
    print("\n--- introduce ---")
    try:
        intro = agent.introduce()
    except Exception as e:
        print("EXCEPTION during introduce: " + str(e))
        return score
    if isinstance(intro, str) and len(intro.strip()) > 0:
        print("introduce returned a non-empty string.  (+1 pt)")
        score += 1.0
        print("Introduction text:")
        for line in intro.splitlines():
            print("  " + line)
    else:
        print("introduce did not return a non-empty string.  Got: " + repr(intro))

    # --- D1: twin check (diagnostic only) ---
    print("\n--- Diagnostic: twin ---")
    try:
        twin = agent_module.OurAgent(twin=True)
        print("Base nickname: " + str(agent.nickname))
        print("Twin nickname: " + str(twin.nickname))
        if twin.nickname == agent.nickname:
            print("NOTE: Twin and base agent share the same nickname.")
            print("  Consider making the twin distinct (e.g. append 'Jr.')")
            print("  to make self-play output easier to read.")
        else:
            print("Twin nickname differs from base.  Good.")
        twin_intro = twin.introduce()
        print("Twin introduction text:")
        for line in twin_intro.splitlines():
            print("  " + line)
    except Exception as e:
        print("Could not instantiate or test OurAgent(twin=True): " + str(e))

    print("\nT1 score: {}/2".format(score))
    return score


# =====================================================================
# T2: Full game play-through
# =====================================================================

def test_full_game(agent_module):
    '''Run two complete TTT games (student as X, then as O).
    Returns (game_score, utt_score): game validity 0-4 pts, utterances 0-6 pts.'''
    print("\n" + "=" * 60)
    print("T2: Full TTT Game Play-through")
    print("    4 pts (game validity) + 6 pts (utterances non-empty, Part II)")
    print("=" * 60)
    game_score = 0.0
    utt_score = 0.0

    rand_o = random_player_module.OurAgent(twin=True)   # plays O in Game A
    rand_x = random_player_module.OurAgent()            # plays X in Game B

    # --- Game A: student plays X ---
    print("\n--- Game A: student agent plays X vs. RandomPlayer (O) ---")
    student_a = agent_module.OurAgent()
    try:
        ok_a = student_a.prepare(game_types.TTT, 'X', rand_o.nickname)
        rand_o.prepare(game_types.TTT, 'O', student_a.nickname)
    except Exception as e:
        print("EXCEPTION during prepare for Game A: " + str(e))
        ok_a = None
    if ok_a != 'OK':
        print("Student agent prepare did not return 'OK'; skipping Game A.")
    else:
        student_a.set_playing_mode(KAgent.DEMO)
        passed, gpts, utt_ok, msgs = run_one_game(student_a, rand_o, 'X', game_types.TTT)
        for m in msgs:
            print(m)
        if passed:
            print("Game A completed without exceptions.  (+{} game pts)".format(gpts))
            game_score += gpts
            if utt_ok:
                print("All utterances in Game A were non-empty.  (+3 utterance pts)")
                utt_score += 3
            else:
                print("Some utterances in Game A were empty.  (+0 utterance pts)")
                print("  Every make_move call must return a non-empty string as result[1].")
        else:
            print("Game A FAILED.  See messages above.")

    # --- Game B: student plays O ---
    print("\n--- Game B: RandomPlayer (X) vs. student agent (O) ---")
    student_b = agent_module.OurAgent()
    try:
        ok_b = student_b.prepare(game_types.TTT, 'O', rand_x.nickname)
        rand_x.prepare(game_types.TTT, 'X', student_b.nickname)
    except Exception as e:
        print("EXCEPTION during prepare for Game B: " + str(e))
        ok_b = None
    if ok_b != 'OK':
        print("Student agent prepare did not return 'OK'; skipping Game B.")
    else:
        student_b.set_playing_mode(KAgent.DEMO)
        passed, gpts, utt_ok, msgs = run_one_game(student_b, rand_x, 'O', game_types.TTT)
        for m in msgs:
            print(m)
        if passed:
            print("Game B completed without exceptions.  (+{} game pts)".format(gpts))
            game_score += gpts
            if utt_ok:
                print("All utterances in Game B were non-empty.  (+3 utterance pts)")
                utt_score += 3
            else:
                print("Some utterances in Game B were empty.  (+0 utterance pts)")
                print("  Every make_move call must return a non-empty string as result[1].")
        else:
            print("Game B FAILED.  See messages above.")

    # --- D3: timing diagnostic ---
    print("\n--- Diagnostic: make_move timing (DEMO mode, TTT initial state, depth 3) ---")
    try:
        timer_agent = agent_module.OurAgent()
        timer_agent.prepare(game_types.TTT, 'X', 'Timer')
        timer_agent.set_playing_mode(KAgent.DEMO)
        t0 = time.time()
        timer_agent.make_move(game_types.TTT.initial_state, "Go.", max_ply=3)
        elapsed = time.time() - t0
        print("make_move took {:.3f} seconds at depth 3 on a 3x3 board.".format(elapsed))
        if elapsed > 2.0:
            print("WARNING: {:.3f}s is quite slow for TTT at depth 3.".format(elapsed))
            print("  Consider optimizing your static_eval or move generator before")
            print("  competing on larger boards with tighter time limits.")
        else:
            print("Timing looks fine for a 3x3 board.")
    except Exception as e:
        print("Could not complete timing test: " + str(e))

    print("\nT2 game validity score:  {}/4".format(game_score))
    print("T2 utterance score:      {}/6  (counts toward Part II)".format(utt_score))
    return game_score, utt_score


# =====================================================================
# T3: Static evaluation
# =====================================================================

def test_static_eval(agent_module):
    '''Check that static_eval preserves relative ordering across 10 states. 4 pts.'''
    print("\n" + "=" * 60)
    print("T3: Static Evaluation  (4 points)")
    print("=" * 60)

    # --- TTT group ---
    print("\n--- TTT states (values should strictly increase A --> E) ---")
    ttt_agent = agent_module.OurAgent()
    try:
        ttt_agent.prepare(game_types.TTT, 'X', 'Grader')
    except Exception as e:
        print("EXCEPTION preparing agent for TTT group: " + str(e))
        return 0.0

    ttt_states = [A,              B,              C,          D,              E]
    ttt_labels = ['A (win for O)', 'B (good for O)', 'C (neutral)',
                  'D (good for X)', 'E (win for X)']
    ttt_vals = []
    for state, label in zip(ttt_states, ttt_labels):
        try:
            v = ttt_agent.static_eval(state, game_types.TTT)
        except Exception as e:
            print("EXCEPTION in static_eval for {}: {}".format(label, e))
            v = 0
        ttt_vals.append(v)
        print("  {:22s}: {}".format(label, v))

    inv1 = count_inversions(ttt_vals)
    if inv1 == 0:
        print("No inversions in TTT group.  Good.")
    else:
        print("Inversions in TTT group: {}".format(inv1))
        print_inversions(ttt_vals, ttt_labels)

    # --- Cassini group ---
    print("\n--- Cassini states (values should strictly increase F --> J) ---")
    cas_agent = agent_module.OurAgent()
    try:
        cas_agent.prepare(game_types.Cassini, 'X', 'Grader')
    except Exception as e:
        print("EXCEPTION preparing agent for Cassini group: " + str(e))
        cas_agent = ttt_agent   # fall back; static_eval accepts game_type arg anyway

    cas_states = [F,              G,              H,            I,              J]
    cas_labels = ['F (win for O)', 'G (good for O)', 'H (neutral)',
                  'I (good for X)', 'J (win for X)']
    cas_vals = []
    for state, label in zip(cas_states, cas_labels):
        try:
            v = cas_agent.static_eval(state, game_types.Cassini)
        except Exception as e:
            print("EXCEPTION in static_eval for {}: {}".format(label, e))
            v = 0
        cas_vals.append(v)
        print("  {:22s}: {}".format(label, v))

    inv2 = count_inversions(cas_vals)
    if inv2 == 0:
        print("No inversions in Cassini group.  Good.")
    else:
        print("Inversions in Cassini group: {}".format(inv2))
        print_inversions(cas_vals, cas_labels)

    total_inv = inv1 + inv2
    score = (20 - total_inv) / 5.0
    print("\nTotal inversions: {}".format(total_inv))
    print("T3 score: {}/4".format(score))
    return score


# =====================================================================
# T4: Minimax without alpha-beta
# =====================================================================

def test_minimax(agent_module):
    '''Check minimax move choice and leaf count (no pruning). 5 pts.'''
    print("\n" + "=" * 60)
    print("T4: Minimax (no alpha-beta)  (5 points)")
    print("=" * 60)
    print("Test state (O to move, depth 2):")
    print(MM_TEST_STATE)
    score = 0.0

    a = agent_module.OurAgent()
    a.set_playing_mode(KAgent.AUTOGRADER)
    try:
        prep = a.prepare(game_types.TTT, 'X', 'Op Ponent')
    except Exception as e:
        print("EXCEPTION during prepare: " + str(e))
        return 0.0
    if prep != 'OK':
        print("prepare did not return 'OK'; cannot run T4.")
        return 0.0

    spec_static_by_table.STATIC_EVAL_COUNT = 0
    try:
        response = a.make_move(
            MM_TEST_STATE,
            "Do your thing.",
            use_alpha_beta=False,
            use_zobrist_hashing=False,
            max_ply=2,
            special_static_eval_fn=spec_static_by_table.special_static_eval_fn)
    except Exception as e:
        print("EXCEPTION during make_move: " + str(e))
        return 0.0

    se_count = spec_static_by_table.STATIC_EVAL_COUNT
    raw_move = response[0][0]
    best_move = tuple(raw_move) if hasattr(raw_move, '__iter__') else raw_move

    print("Move chosen:          {}".format(best_move))
    print("Leaves evaluated:     {}".format(se_count))

    # --- Move correctness (3 pts) ---
    if best_move == (1, 2):
        print("Correct move (1, 2).  (+3 pts)")
        score += 3
    else:
        print("Wrong move.  Expected (1, 2), got {}.".format(best_move))
        print("  Check that you use special_static_eval_fn when provided,")
        print("  and that your value is correctly backed up through the tree.")

    # --- Leaf count (2 pts) ---
    if se_count == 12:
        print("Correct leaf count (12).  (+2 pts)")
        score += 2
    else:
        print("Wrong leaf count.  Expected 12, got {}.".format(se_count))
        print("  Plain minimax at depth 2 here visits exactly 4 O-moves x 3 X-responses = 12 leaves.")
        print("  This count does NOT depend on move ordering.")
        print("  Check your depth-limit logic and that you call the special_static_eval_fn")
        print("  at every leaf (when depth_remaining == 0 or no moves remain).")

    # --- D2: AUTOGRADER stats diagnostic ---
    print("\n--- Diagnostic: AUTOGRADER mode stats ---")
    inner = response[0]
    if len(inner) >= 3 and isinstance(inner[2], dict):
        stats = inner[2]
        for key, val in stats.items():
            note = "  (placeholder -- not yet implemented)" if val == -1 else ""
            print("  {:44s} = {}{}".format(key, val, note))
    else:
        print("  result[0] has {} elements and no stats dict in AUTOGRADER mode.".format(len(inner)))
        print("  In AUTOGRADER mode, append a stats dict to [move, state]:")
        print("  See the stats dict template in agent_base.py's make_move stub.")

    print("\nT4 score: {}/5".format(score))
    return score


# =====================================================================
# T5: Alpha-beta pruning
# =====================================================================

def test_alpha_beta(agent_module):
    '''Check alpha-beta move choice and leaf count. 5 pts.'''
    print("\n" + "=" * 60)
    print("T5: Alpha-Beta Pruning  (5 points)")
    print("=" * 60)
    print("Test state (O to move, depth 2, same state as T4):")
    print(MM_TEST_STATE)
    print("Row-major blank squares: (1,1), (1,2), (2,0), (2,1)")
    print("Expected move: (1, 2)    Expected leaf count with row-major ordering: 8")
    score = 0.0

    a = agent_module.OurAgent()
    a.set_playing_mode(KAgent.AUTOGRADER)
    try:
        prep = a.prepare(game_types.TTT, 'X', 'Op Ponent')
    except Exception as e:
        print("EXCEPTION during prepare: " + str(e))
        return 0.0
    if prep != 'OK':
        print("prepare did not return 'OK'; cannot run T5.")
        return 0.0

    spec_static_by_table.STATIC_EVAL_COUNT = 0
    try:
        response = a.make_move(
            MM_TEST_STATE,
            "Do your thing.",
            use_alpha_beta=True,
            use_zobrist_hashing=False,
            max_ply=2,
            special_static_eval_fn=spec_static_by_table.special_static_eval_fn)
    except Exception as e:
        print("EXCEPTION during make_move: " + str(e))
        return 0.0

    se_count = spec_static_by_table.STATIC_EVAL_COUNT
    raw_move = response[0][0]
    best_move = tuple(raw_move) if hasattr(raw_move, '__iter__') else raw_move

    print("Move chosen:          {}".format(best_move))
    print("Leaves evaluated:     {}".format(se_count))

    # --- Move correctness (3 pts) ---
    if best_move == (1, 2):
        print("Correct move (1, 2).  (+3 pts)")
        score += 3
    else:
        print("Wrong move.  Expected (1, 2), got {}.".format(best_move))
        print("  An incorrect move here often means alpha-beta is pruning incorrectly")
        print("  (cutting off branches that should not be cut), leading to the wrong")
        print("  backed-up value at the root.  Check your cutoff conditions.")

    # --- Leaf count with ordering feedback (2 pts) ---
    if se_count == 8:
        print("Correct leaf count (8).  (+2 pts)")
        print("Row-major ordering in AUTOGRADER mode confirmed.")
        score += 2
    elif 8 < se_count < 12:
        print("Leaf count is {} (expected 8 with row-major ordering).".format(se_count))
        print("  Alpha-beta IS pruning (count < 12), but less than the reference.")
        print("  In AUTOGRADER mode, your move generator must iterate row by row,")
        print("  left to right within each row -- the same order as RandomPlayer's")
        print("  move_gen function.  With this ordering, the reference evaluates")
        print("  exactly 8 leaves on this state.")
        print("  IMPORTANT: this row-major requirement applies only in AUTOGRADER mode.")
        print("  In DEMO and COMPETITION modes you are free (and encouraged) to use")
        print("  any ordering that improves tournament performance.")
    elif se_count == 12:
        print("Leaf count is 12 -- the same as plain minimax.")
        print("  Alpha-beta does not appear to be pruning at all.")
        print("  Make sure your cutoff checks run when use_alpha_beta=True and that")
        print("  you pass alpha and beta values into each recursive call.")
    elif se_count < 8:
        print("Leaf count is {} (fewer than 8 -- possible over-pruning).".format(se_count))
        print("  Check that you update alpha (or beta) AFTER evaluating each child,")
        print("  and that your cutoff condition uses strict inequality (> for max, < for min).")
    else:
        print("Unexpected leaf count: {}.".format(se_count))

    print("\nT5 score: {}/5".format(score))
    return score


# =====================================================================
# Main
# =====================================================================

if __name__ == "__main__":
    print("\nK-in-a-Row -- Student Self-Check Autograder")
    print("Agent file: " + AGENT_FILE)

    agent_module, agent = load_agent(AGENT_FILE)
    if agent_module is None:
        print("\nCannot continue: agent failed to load.  Fix the errors above and re-run.")
        raise SystemExit(1)

    t1           = test_prepare_and_introduce(agent, agent_module)
    t2_game, t2_utt = test_full_game(agent_module)
    t3           = test_static_eval(agent_module)
    t4           = test_minimax(agent_module)
    t5           = test_alpha_beta(agent_module)

    part1_total = t1 + t2_game + t3 + t4 + t5
    part2_auto  = t2_utt
    auto_total  = part1_total + part2_auto

    print("\n" + "=" * 60)
    print("AUTOGRADER SUMMARY")
    print("=" * 60)
    print()
    print("PART I — Code for Playing K-in-a-Row        / 20")
    print("  T1  prepare / introduce:        {:.1f} / 2".format(t1))
    print("  T2  full game play-through:     {:.1f} / 4".format(t2_game))
    print("  T3  static evaluation:          {:.1f} / 4".format(t3))
    print("  T4  minimax (no pruning):       {:.1f} / 5".format(t4))
    print("  T5  alpha-beta pruning:         {:.1f} / 5".format(t5))
    print("  " + "-" * 40)
    print("  Part I total:                  {:.1f} / 20".format(part1_total))
    print()
    print("PART II — Code for Dialog (autograded portion)")
    print("  Utterances non-empty (T2):      {:.1f} / 6".format(part2_auto))
    print("  (Remaining 14 pts are TA-graded from your game transcript)")
    print()
    print("=" * 60)
    print("  Total autograded:              {:.1f} / 26".format(auto_total))
    print("=" * 60)
    print()
    print("Remaining 74 pts are staff-graded:")
    print("  Part II  dialog quality (TA):        14 / 14")
    print("  Part III learning diary (TA):        60 / 60")
    print()
    print("NOTE: The official course autograder may use different test states or")
    print("additional tests.  Passing all tests here is a strong indicator but")
    print("does not guarantee a full score on the official autograder.")
