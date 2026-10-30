'''
n1coleh_KInARow.py
Authors: Nicole Ham, Rena Yin

An agent for playing "K-in-a-Row with Forbidden Squares" and related games.

THIS IS A TEMPLATE WITH STUBS FOR THE REQUIRED FUNCTIONS.
YOU CAN ADD WHATEVER ADDITIONAL FUNCTIONS YOU NEED IN ORDER
TO PROVIDE A GOOD STRUCTURE FOR YOUR IMPLEMENTATION.

'''

from agent_base import KAgent
from game_types import State, Game_Type
from winTesterForK import winTesterForK

AUTHORS = 'Nicole Ham and Rena Yin' 
STUDENT_IDS = ['n1coleh', 'yin123'] # The first ID here should
# match the one in the file name, e.g., jsmith99_KInARow.py.

import time # You'll probably need this to avoid losing a
 # game due to exceeding a time limit.
import random

# Create your own type of agent by subclassing KAgent:

class OurAgent(KAgent):  # Keep the class name "OurAgent" so a game master
    # knows how to instantiate your agent class.

    def __init__(self, twin=False):
        self.twin=twin
        self.nickname = 'Smirk'
        if twin: self.nickname = 'Smirk Jr.'
        self.long_name = 'Smirk the Insufferable'
        if twin: self.long_name = 'Smirk the Passive-Aggressive'
        # Base agent trash-talks openly; the twin says the same things
        # wrapped in fake politeness.
        self.persona = 'smug rage-baiter'
        if twin: self.persona = 'passive-aggressive rage-baiter'
        self.voice_info = {'Chrome': 10, 'Firefox': 2, 'other': 0}
        self.playing = "don't know yet" # e.g., "X" or "O".
        self.alpha_beta_cutoffs_this_turn = -1
        self.num_static_evals_this_turn = -1
        self.zobrist_table_num_entries_this_turn = -1
        self.zobrist_table_num_hits_this_turn = -1
        self.zobrist_table_num_lookups_this_turn = -1
        self.zobrist_num_useful_hits_for_minimax = -1
        self.zobrist_num_useful_hits_for_ordering = -1
        self.zobrist_keys = None     # zobrist_keys[i][j][token] -> random 64-bit int
        self.zobrist_side_key = None # XORed in when it is O's turn
        self.transposition_table = {}  # hash -> (depth, value, flag, best_move)
        self.use_zobrist = False     # whether the current search uses the table
        self.root_hash = None
        self.current_game_type = None
        self.playing_mode = KAgent.DEMO
        self.special_static_eval_fn = None
        self.deadline = None         # perf_counter() value at which search must stop
        self.search_root = None      # root state of the current search
        self.preferred_move = None   # best root move from the previous depth
        self.opponent_nickname = 'you'
        self.utterances_matter = True
        self.reset_dialog()

    # Per-game memory used to make utterances (see compose_utterance).
    def reset_dialog(self):
        self.decks = {}              # category -> unused lines, so we don't repeat
        self.utt_count = 0
        self.last_reply_category = None
        self.score_history = []      # backed-up score after each of our moves, from our side
        self.last_search = None      # numbers from the last search, for "how did you do that"
        self.previous_search = None  # search for the move the opponent just saw
        self.game_history = []       # real moves/remarks, never minimax branches
        self.history_complete = True
        self._history_state = None   # copied board returned on our previous turn

    def introduce(self):
        if self.twin:
            intro = '\nHi! I\'m ' + self.long_name + '.\n' + \
                'I was made by ' + AUTHORS + ' (' + ', '.join(STUDENT_IDS) + ').\n' + \
                'I\'m sure you\'ll do your best. It probably won\'t be enough, but still. :)\n'
        else:
            intro = '\nMy name is ' + self.long_name + '.\n' + \
                'I was made by ' + AUTHORS + ' (' + ', '.join(STUDENT_IDS) + ').\n' + \
                'I have never lost a game. (I have lost several games.)\n' + \
                'Let\'s make this quick, I have a nap scheduled.\n'
        return intro

    # Receive and acknowledge information about the game from
    # the game master:
    def prepare(
        self,
        game_type,
        what_side_to_play,
        opponent_nickname,
        expected_time_per_move = 0.1, # Time limits can be
                                      # changed mid-game by the game master.

        utterances_matter=True):      # If False, just return 'OK' for each utterance,
                                      # or something simple and quick to compute
                                      # and do not import any LLM or special APIs.
                                      # During the tournament, this will be False..
        # Save the setup on this agent so other methods can use it later.
        # Optionally, import your LLM API here.
        # Then you can use it to help create utterances.
        self.current_game_type = game_type
        self.playing = what_side_to_play
        self.opponent_nickname = opponent_nickname
        self.expected_time_per_move = expected_time_per_move
        self.utterances_matter = utterances_matter
        self.reset_dialog()
        self.init_zobrist(game_type.n, game_type.m)

        # The autograder checks for this exact string before running any tests.
        # The caller controls playing_mode; preserve its selected mode.
        return "OK"
   
    # The core of your agent's ability should be implemented here:             
    def make_move(self, current_state, current_remark, time_limit=1000,
                  use_alpha_beta=True,
                  use_zobrist_hashing=False, max_ply=3,
                  special_static_eval_fn=None):
        # --- HOW TO IMPLEMENT make_move ---
        # 1. Generate candidate moves: iterate over rows and columns of
        #    current_state.board; any square equal to ' ' is a legal move.
        # 2. For each candidate position (i, j), build a successor state:
        #      new_s = State(old=current_state)       # deep copy
        #      new_s.board[i][j] = current_state.whose_move
        #      new_s.change_turn()                    # switch X <-> O
        # 3. Count blank squares before searching to detect a full board (draw)
        #    and to limit recursion depth appropriately.
        # 4. Call self.minimax(...) on the current state to get the best move.
        # 5. Compose an utterance string appropriate to your agent's persona.
        # 6. Return format:
        #      DEMO / COMPETITION: [[move, new_state], utterance]
        #      AUTOGRADER:         [[move, new_state, stats], utterance]
        #    where stats is a dict with keys defined in agent_base.py, e.g.:
        #      stats['alpha_beta_cutoffs_this_turn']        = self.alpha_beta_cutoffs_this_turn
        #      stats['num_static_evals_this_turn']          = self.num_static_evals_this_turn
        #      stats['zobrist_table_num_entries_this_turn'] = self.zobrist_table_num_entries_this_turn
        #      stats['zobrist_table_num_hits_this_turn']    = self.zobrist_table_num_hits_this_turn

        start = time.perf_counter()

        # Reset per-turn statistics.
        self.alpha_beta_cutoffs_this_turn = 0
        self.num_static_evals_this_turn = 0
        self.special_static_eval_fn = special_static_eval_fn

        # Leave a safety margin so we return before the game master's limit.
        self.deadline = None
        move_deadline = None
        if self.playing_mode != KAgent.AUTOGRADER and time_limit is not None:
            budget = max(0.0, time_limit)
            self.deadline = start + TIME_SAFETY_FRACTION * budget
            move_deadline = start + budget

        # Have a legal move ready even if the first search cannot finish.
        # next() copies just one successor, rather than building all of them.
        fallback = next(successors_and_moves(current_state), None)
        if fallback is None:
            best_move, best_state = None, State(old=current_state)
            best_state.change_turn()
        else:
            best_move, best_state = fallback

        # Zobrist hashing: on when requested, and always in real games
        # (DEMO/COMPETITION), where the game master never asks for it.
        self.use_zobrist = use_zobrist_hashing or \
            (self.playing_mode != KAgent.AUTOGRADER and ZOBRIST_IN_GAMES)
        if self.use_zobrist:
            board = current_state.board
            if self.zobrist_keys is None or len(self.zobrist_keys) != len(board) \
                    or len(self.zobrist_keys[0]) != len(board[0]):
                self.init_zobrist(len(board), len(board[0]))
            # The table persists between our moves in a game (positions repeat
            # across turns), but test searches start clean so their stats are
            # reproducible and special-evaluator values never mix with ours.
            if self.playing_mode == KAgent.AUTOGRADER or special_static_eval_fn is not None \
                    or len(self.transposition_table) > MAX_TABLE_ENTRIES:
                self.transposition_table = {}
            self.root_hash = self.zobrist_hash(current_state)
            self.zobrist_table_num_entries_this_turn = 0
            self.zobrist_table_num_lookups_this_turn = 0
            self.zobrist_table_num_hits_this_turn = 0
            self.zobrist_num_useful_hits_for_minimax = 0
            self.zobrist_num_useful_hits_for_ordering = 0
        else:
            self.zobrist_table_num_entries_this_turn = -1
            self.zobrist_table_num_lookups_this_turn = -1
            self.zobrist_table_num_hits_this_turn = -1
            self.zobrist_num_useful_hits_for_minimax = -1
            self.zobrist_num_useful_hits_for_ordering = -1

        # Count blank squares to detect a full board and limit depth.
        num_blanks = count_blanks(current_state)
        best_score, depth_reached = None, 0
        timed_out = False
        used_fallback = True
        self.search_root = current_state
        self.preferred_move = None

        if self.playing_mode == KAgent.AUTOGRADER:
            # Exactly one search at max_ply, in plain row-major order,
            # so the leaf counts match what the autograder expects.
            depths = [min(max_ply, num_blanks)]
        else:
            # Iterative deepening: search depth 1, 2, 3, ... until time runs
            # out, keeping the result of the deepest search that finished.
            depths = range(1, num_blanks + 1)

        try:
            for depth in depths:
                self._check_search_deadline()
                result = self.minimax(current_state, depth, pruning=use_alpha_beta)
                # The last leaf may itself have taken us past the deadline.
                self._check_search_deadline()
                if result[1] is not None:
                    best_move, best_state = result[1], result[2]
                    best_score, depth_reached = result[0], depth
                    used_fallback = False
                    self.preferred_move = best_move  # search it first next depth
        except SearchTimeout:
            # Keep the fallback or the previous fully completed result.
            timed_out = True
        finally:
            # Do not leave an expired deadline or root preference for later calls.
            self.deadline = None
            self.search_root = None
            self.preferred_move = None
            self.use_zobrist = False

        self.previous_search = self.last_search
        self.last_search = {'depth': depth_reached,
                            'evals': self.num_static_evals_this_turn,
                            'cutoffs': self.alpha_beta_cutoffs_this_turn,
                            'seconds': time.perf_counter() - start,
                            'score': best_score,
                            'move': best_move,
                            'k': self.current_game_type.k,
                            'pruning': bool(use_alpha_beta),
                            'iterative_deepening': self.playing_mode != KAgent.AUTOGRADER,
                            'special_evaluator': special_static_eval_fn is not None,
                            'timed_out': timed_out,
                            'used_fallback': used_fallback,
                            'zobrist_entries': self.zobrist_table_num_entries_this_turn,
                            'zobrist_lookups': self.zobrist_table_num_lookups_this_turn,
                            'zobrist_hits': self.zobrist_table_num_hits_this_turn,
                            'zobrist_useful_minimax': self.zobrist_num_useful_hits_for_minimax,
                            'zobrist_useful_ordering': self.zobrist_num_useful_hits_for_ordering}
        history_entry = None
        if not self.utterances_matter:
            new_remark = 'OK'
        elif move_deadline is not None and time.perf_counter() >= move_deadline:
            # Don't start optional dialogue work when the whole budget is gone.
            new_remark = "No comment. Your move."
        else:
            try:
                if self.playing_mode == KAgent.DEMO:
                    history_entry = self.remember_turn(current_state, current_remark,
                                                       best_move, best_state)
                new_remark = self.compose_utterance(current_state, current_remark,
                                                    best_move, best_state, best_score)
            except Exception:
                # Never forfeit a game over a remark.
                new_remark = "No comment. Your move."

        # Record the actual outgoing remark after composing it, so a narrative
        # cannot quote its own as-yet-unspoken response.
        if history_entry is not None:
            history_entry['utterance'] = new_remark

        if self.playing_mode != KAgent.AUTOGRADER:
            return [[best_move, best_state], new_remark]

        stats = {
            'alpha_beta_cutoffs_this_turn': self.alpha_beta_cutoffs_this_turn,
            'num_static_evals_this_turn': self.num_static_evals_this_turn,
            'zobrist_table_num_entries_this_turn': self.zobrist_table_num_entries_this_turn,
            'zobrist_table_num_hits_this_turn': self.zobrist_table_num_hits_this_turn,
            'zobrist_num_useful_hits_for_minimax': self.zobrist_num_useful_hits_for_minimax,
            'zobrist_num_useful_hits_for_ordering': self.zobrist_num_useful_hits_for_ordering,
            'zobrist_table_num_lookups_this_turn': self.zobrist_table_num_lookups_this_turn
        }
        return [[best_move, best_state, stats], new_remark]

    def _check_search_deadline(self):
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            raise SearchTimeout()

    # The main adversarial search function:
    def minimax(self,
            state,
            depth_remaining,
            pruning=False,
            alpha=None,
            beta=None):
        # --- HOW TO IMPLEMENT minimax ---
        # Base cases — call static_eval and return its value:
        #   - depth_remaining == 0  (depth limit reached)
        #   - no blank squares remain on the board (draw)
        #   - terminal win/loss state (do not generate moves after a win)
        # Recursive case:
        #   is_max = (state.whose_move == 'X')   # X maximizes, O minimizes
        #   best_val = -inf if is_max else +inf
        #   For each successor state generated by your move generator:
        #     result = self.minimax(successor, depth_remaining - 1, pruning, alpha, beta)
        #     Update best_val and best_move.
        #     If pruning is True: check alpha/beta cutoff and break early.
        #     Update alpha (if is_max) or beta (if not is_max) after each child.
        # Return at minimum [score, best_move, best_state].
        # Additional values after index 0 can carry info back to make_move.

        # Give up on this search if we are out of time; make_move falls back
        # to the result of the last depth that finished.
        self._check_search_deadline()

        # None means "no bound".
        if alpha is None: alpha = float('-inf')
        if beta is None: beta = float('inf')
        is_root = state is self.search_root

        # Zobrist lookup.  A deep-enough entry can answer this node outright
        # (never at the root, which must return a real successor state);
        # otherwise its stored best move is searched first.
        key, table_move = None, None
        if self.use_zobrist:
            key = self.root_hash if is_root else getattr(state, 'zobrist_key', None)
            if key is None:
                key = self.zobrist_hash(state)
            self.zobrist_table_num_lookups_this_turn += 1
            entry = self.transposition_table.get(key)
            if entry is not None:
                self.zobrist_table_num_hits_this_turn += 1
                entry_depth, entry_val, entry_flag, entry_move = entry
                if entry_depth >= depth_remaining and not is_root and (
                        entry_flag == EXACT
                        or (entry_flag == LOWER and entry_val >= beta)
                        or (entry_flag == UPPER and entry_val <= alpha)):
                    self.zobrist_num_useful_hits_for_minimax += 1
                    return [entry_val, None, None]
                table_move = entry_move

        # Base cases: game finished, depth limit reached, or no blank squares remain.
        # Stop at the depth limit or a draw, even without a finished flag.
        # Hypothetical successors do not have finished set by the game master,
        # so also detect wins from the board before allowing any further moves.
        if state.finished or count_blanks(state) == 0:
            leaf_depth = TERMINAL_DEPTH   # exact however deep anyone searches
        elif depth_remaining == 0:
            leaf_depth = 0
        elif has_winner(state, self.current_game_type.k):
            leaf_depth = TERMINAL_DEPTH
        else:
            leaf_depth = None
        if leaf_depth is not None:
            val = self.evaluate(state)
            if key is not None:
                self.store(key, leaf_depth, val, EXACT, None)
            return [val, None, None]

        alpha_orig, beta_orig = alpha, beta
        is_max = (state.whose_move == 'X')  # X maximizes, O minimizes
        best_val = float('-inf') if is_max else float('inf')
        best_move = None
        best_state = None

        children = successors_and_moves(state)
        first = None
        if table_move is not None:
            first = table_move
            self.zobrist_num_useful_hits_for_ordering += 1
        elif is_root and self.preferred_move is not None \
                and self.playing_mode != KAgent.AUTOGRADER:
            # Try the previous depth's best move first for more cutoffs.
            first = self.preferred_move
        if first is not None:
            children = sorted(children, key=lambda c: c[0] != first)

        game_type = self.current_game_type
        for move, successor in children:
            # A move that completes k in a row ends the game, so the
            # successor is a leaf no matter how much depth remains.
            if game_type is not None and \
                    winTesterForK(successor, move, game_type.k) != 'No win':
                successor.finished = True
            if key is not None:
                # Incremental hash: add the new token, flip whose turn it is.
                successor.zobrist_key = key ^ self.zobrist_side_key ^ \
                    self.zobrist_keys[move[0]][move[1]][state.whose_move]
            result = self.minimax(successor, depth_remaining - 1, pruning, alpha, beta)
            self._check_search_deadline()
            val = result[0]

            if (is_max and val > best_val) or (not is_max and val < best_val):
                best_val = val
                best_move = move
                best_state = successor

            if pruning:
                if is_max:
                    if best_val >= beta:
                        self.alpha_beta_cutoffs_this_turn += 1
                        break
                    alpha = max(alpha, best_val)
                else:
                    if best_val <= alpha:
                        self.alpha_beta_cutoffs_this_turn += 1
                        break
                    beta = min(beta, best_val)

        if key is not None:
            # With pruning, a value outside the original window is only a bound.
            if not pruning or alpha_orig < best_val < beta_orig:
                flag = EXACT
            elif best_val <= alpha_orig:
                flag = UPPER
            else:
                flag = LOWER
            self.store(key, depth_remaining, best_val, flag, best_move)

        return [best_val, best_move, best_state]

    # ---- Zobrist hashing ---------------------------------------------------

    # One random 64-bit key per (square, token), plus one for "O to move".
    # A fixed seed keeps runs reproducible.
    def init_zobrist(self, rows, columns):
        rng = random.Random(415)
        self.zobrist_keys = [[{'X': rng.getrandbits(64), 'O': rng.getrandbits(64)}
                              for _ in range(columns)] for _ in range(rows)]
        self.zobrist_side_key = rng.getrandbits(64)
        self.transposition_table = {}

    # Full hash of a state; minimax updates it incrementally instead.
    def zobrist_hash(self, state):
        h = 0
        for i, row in enumerate(state.board):
            for j, token in enumerate(row):
                if token == 'X' or token == 'O':
                    h ^= self.zobrist_keys[i][j][token]
        if state.whose_move == 'O':
            h ^= self.zobrist_side_key
        return h

    # Write an entry, keeping whichever of the old and new was searched deeper.
    def store(self, key, depth, value, flag, move):
        old = self.transposition_table.get(key)
        if old is None or depth >= old[0]:
            self.transposition_table[key] = (depth, value, flag, move)
            self.zobrist_table_num_entries_this_turn += 1

    # Uses the special static evaluator when one was given (AUTOGRADER mode),
    # otherwise our own static_eval.  Counts every evaluation.
    def evaluate(self, state):
        # Return a numeric score: positive = good for X, negative = good for O.
        # Use game_type.k (the win length) to evaluate partial lines.
        # IMPORTANT: k is NOT stored in the state — you must get it from game_type.
        # In DEMO/COMPETITION mode game_type will be None; use self.current_game_type
        # (which you should have saved during prepare).
        self.num_static_evals_this_turn += 1
        if self.special_static_eval_fn is not None:
            return self.special_static_eval_fn(state)
        return self.static_eval(state, self.current_game_type)
 
    def static_eval(self, state, game_type=None):
        """Score potential winning segments: positive favors X, negative O.

        Generalizes the unblocked-line heuristic from Adversarial Search I,
        slides 9–11, to variable k and boards with forbidden squares.
        """
        if game_type is None:
            game_type = self.current_game_type
        if game_type is None:
            raise ValueError("static_eval needs a game_type or a prior prepare call.")

        board = state.board
        rows, columns = len(board), len(board[0])
        k = game_type.k
        score = 0
        # At most four segments start at each cell. This finite win score
        # exceeds the sum of all possible nonwinning segment contributions.
        win_score = 4 * rows * columns * 10**k + 1
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for row in range(rows):
            for column in range(columns):
                for dr, dc in directions:
                    end_row = row + (k - 1) * dr
                    end_column = column + (k - 1) * dc
                    if not (0 <= end_row < rows and 0 <= end_column < columns):
                        continue

                    segment = [board[row + step * dr][column + step * dc]
                               for step in range(k)]
                    if '-' in segment:
                        continue
                    x_count = segment.count('X')
                    o_count = segment.count('O')

                    # Completed win dominates ordinary positional scores
                    if x_count == k:
                        return win_score
                    if o_count == k:
                        return -win_score

                    # Neither player can complete a segment occupied by both
                    if x_count and o_count:
                        continue
                    if x_count:
                        score += 10**(x_count - 1)
                    elif o_count:
                        score -= 10**(o_count - 1)

        if count_blanks(state) == 0:
            return 0
        return score
 
    # ---- Dialog ----------------------------------------------------------

    def remember_turn(self, state, remark, move, new_state):
        """Observe the opponent's real move, then record our selected move."""
        before = self._history_state or self.current_game_type.initial_state
        same_size = (len(before.board) == len(state.board)
                     and all(len(a) == len(b) for a, b in zip(before.board, state.board)))
        changes = ([(r, c) for r in range(len(state.board))
                    for c in range(len(state.board[r]))
                    if before.board[r][c] != state.board[r][c]] if same_size else [])
        opponent = other(state.whose_move)
        legal_change = False
        if same_size and len(changes) == 1:
            r, c = changes[0]
            legal_change = (before.board[r][c] == ' '
                            and state.board[r][c] == opponent
                            and before.whose_move == opponent)
        if legal_change:
            self._remember_move(before, state, changes[0], remark)
        elif not same_size or changes or before.whose_move != state.whose_move:
            # A skipped turn or mid-game starting position is an observation,
            # not permission to invent who moved where.
            self.history_complete = False
            self.game_history.append({'player': None, 'move': None,
                                      'board': [row[:] for row in state.board],
                                      'whose_move': state.whose_move,
                                      'utterance': remark, 'events': []})

        entry = None
        if move is not None:
            entry = self._remember_move(state, new_state, move, '')
        self._history_state = State(old=new_state)
        return entry

    def _remember_move(self, before, after, move, remark):
        player = before.whose_move
        k = self.current_game_type.k
        events = []
        if winTesterForK(after, move, k) != 'No win':
            events.append({'kind': 'win'})
        else:
            if blocks_win(before, move, other(player), k):
                events.append({'kind': 'blocked'})
            threats = winning_squares(after, player, k)
            if threats:
                events.append({'kind': 'threat', 'squares': threats})
        entry = {'player': player, 'move': tuple(move),
                 'board': [row[:] for row in after.board],
                 'whose_move': after.whose_move, 'utterance': remark,
                 'events': events}
        self.game_history.append(entry)
        return entry

    # Build this turn's remark from the board, the search result, and the
    # opponent's last remark.  Rule-based: the most notable situation picks
    # a category of lines, then we may add a reply to the opponent or a
    # brag that uses the real search numbers.
    def compose_utterance(self, state, remark, move, new_state, score):
        me = state.whose_move
        opp = other(me)
        game_type = self.current_game_type
        k = game_type.k if game_type is not None else None
        self.utt_count += 1

        my_score = None
        if score is not None:
            my_score = score if me == 'X' else -score  # positive = good for us
            self.score_history.append(my_score)

        # Special requests get a real answer (in character, of course).
        lowered = (remark or '').lower()
        if 'how' in lowered and ('did that' in lowered or 'do that' in lowered):
            return self.style(self.explain_last_move(k, previous=True))
        if 'take on the game' in lowered or 'game so far' in lowered:
            return self.style(self.game_so_far())

        # Most notable situation first.
        if k is None or move is None:
            category = 'even'
        elif winTesterForK(new_state, move, k) != 'No win':
            category = 'i_won'
        elif my_score is not None and my_score >= win_score_for(state, k):
            category = 'forced_win'
        elif my_score is not None and my_score <= -win_score_for(state, k):
            category = 'forced_loss'
        elif blocks_win(state, move, opp, k):
            category = 'blocked'
        elif winning_squares(new_state, me, k):
            category = 'threat'
        elif self.utt_count == 1:
            category = 'opening'
        elif my_score is not None and my_score > 2 * 10**(k - 3):
            category = 'ahead'
        elif my_score is not None and my_score < -2 * 10**(k - 3):
            category = 'behind'
        else:
            category = 'even'

        fields = {'opp': self.opponent_nickname, 'k': k}
        fields.update(self.last_search)
        line = self.pick(category, fields)

        reply = self.respond_to(remark, fields)
        if reply:
            line = reply + ' ' + line
        elif self.utt_count % 3 == 0 and self.last_search['evals'] > 0:
            line += ' ' + self.pick('stats', fields)
        return self.style(line)

    # Take the next unused line from a category, reshuffling when it runs out.
    def pick(self, category, fields):
        deck = self.decks.get(category)
        if not deck:
            deck = LINES[category][:]
            random.shuffle(deck)
            self.decks[category] = deck
        return deck.pop().format(**fields)

    # React to keywords in the opponent's remark, or sometimes quote it back.
    def respond_to(self, remark, fields):
        remark = (remark or '').strip()
        if not remark or remark in GAME_MASTER_REMARKS:
            return None
        lowered = remark.lower()
        category = None
        for keywords, keyword_category in REMARK_KEYWORDS:
            if any(word in lowered for word in keywords):
                category = keyword_category
                break
        if category is None and self.utt_count % 2 == 0:
            category = 'question' if '?' in remark else 'quote_back'
        # Don't answer the same way twice in a row (keeps self-play from
        # getting stuck trading the same comeback).
        if category is None or category == self.last_reply_category:
            self.last_reply_category = None
            return None
        self.last_reply_category = category
        if category == 'quote_back':
            return 'You said: "' + remark + '" ' + self.pick('quote_back', fields)
        return self.pick(category, fields)

    # The twin says everything with fake politeness tacked on.
    def style(self, line):
        if self.twin:
            line += ' ' + random.choice(TWIN_SUFFIXES)
        return line

    # Opponent requests refer to our previous visible move, not the new one.
    # Direct calls can still explain the most recently selected move.
    def explain_last_move(self, k, previous=False):
        s = self.previous_search if previous else self.last_search
        if s is None:
            return ("I don't have an earlier move to explain yet. "
                    "You're requesting a sequel before the pilot. Let me play first.")

        which_move = 'previous move' if previous else 'move I just selected'
        algorithm = 'minimax with alpha-beta pruning' if s['pruning'] else 'plain minimax (pruning disabled)'
        search = 'iterative deepening' if s['iterative_deepening'] else 'one fixed-depth search'
        parts = [f"Ah, you want the director's commentary. Fine. For my {which_move} at {s['move']}: "
                 f"I used {algorithm} and {search}."]
        if s['used_fallback']:
            parts.append("No searched move was accepted; I used the first legal square as a fallback. "
                         "No, that wasn't a secret master plan. Sometimes a square is just a square.")
        else:
            parts.append(f"My deepest completed iteration was {s['depth']} ply, "
                         f"with a backed-up score of {s['score']} (higher favors X, lower favors O). "
                         "Thinking ahead. Controversial, I know.")
        if s['timed_out']:
            parts.append("The search deadline was reached; unfinished work did not replace my saved move. "
                         "The clock cut my microphone, not my standards.")
        parts.append(f"Across this move's search, I made {s['evals']:,} static evaluation calls "
                     f"and recorded {s['cutoffs']:,} alpha-beta cutoff events in "
                     f"{s['seconds']:.4f} seconds, excluding dialogue generation. "
                     "These totals include repeated positions and any interrupted iteration. "
                     "Receipts, not vibes.")
        if s['zobrist_lookups'] > 0:
            parts.append(f"My Zobrist table took {s['zobrist_lookups']:,} lookups and "
                         f"{s['zobrist_hits']:,} hits; {s['zobrist_useful_minimax']:,} hits answered "
                         f"a position outright and {s['zobrist_useful_ordering']:,} told me which "
                         f"move to try first. I wrote {s['zobrist_entries']:,} entries. "
                         "I remember positions. You don't even remember your last move.")
        if s['special_evaluator']:
            parts.append("The configured leaf evaluator was the supplied special evaluator, not my own heuristic. "
                         "The grader brought its own calculator. Apparently mine has too much personality.")
        else:
            parts.append(f"My heuristic scores unblocked length-{s['k']} segments: "
                         "X adds points, O subtracts them, and each extra token multiplies "
                         "a nonwinning segment's weight by ten. Completed wins dominate; "
                         "full-board draws score zero. "
                         "That's the scoring system. The attitude is complimentary.")
        return ' '.join(parts)

    # Narrate recorded boards/actions/conversation, including this turn's move.
    def game_so_far(self):
        moves = [entry for entry in self.game_history if entry['move'] is not None]
        if not moves:
            return "No recorded moves yet. A riveting documentary about an empty notebook. Prediction: too early to call."
        actor = lambda entry: 'I' if entry['player'] == self.playing else 'You'
        parts = [f"My take, including the move I'm returning now: {len(moves)} recorded moves."]
        if self.history_complete:
            parts.append(f"{actor(moves[0])} opened at {moves[0]['move']}. That's where the plot began.")
        else:
            parts.append("Some turns weren't recorded, so I'm sticking to what I actually observed. No fan fiction.")

        # Prefer actual wins/blocks, then fill remaining slots with threats.
        notable = [i for i, entry in enumerate(moves)
                   if any(e['kind'] in ('win', 'blocked') for e in entry['events'])][-2:]
        if len(notable) < 2:
            threats = [i for i, entry in enumerate(moves) if i not in notable
                       and any(e['kind'] == 'threat' for e in entry['events'])]
            notable += threats[-(2 - len(notable)):]
        for i in sorted(notable):
            entry = moves[i]
            event = entry['events'][0]
            if event['kind'] == 'win':
                parts.append(f"{actor(entry)} completed {self.current_game_type.k} in a row at {entry['move']}.")
            elif event['kind'] == 'blocked':
                parts.append(f"{actor(entry)} blocked an immediate winning threat at {entry['move']}. Plot twist.")
            else:
                parts.append(f"{actor(entry)} left an immediate winning chance at {event['squares'][0]}.")
        if not notable:
            parts.append("No recorded wins or immediate-threat turning points yet. We're still in the trailer.")

        # Quote an entire earlier opponent remark, not this request or our own reply.
        quotes = [entry['utterance'] for entry in self.game_history
                  if entry['player'] == other(self.playing) and entry['utterance']
                  and entry['utterance'] not in GAME_MASTER_REMARKS
                  and not any(trigger in entry['utterance'].lower()
                              for trigger in ('take on the game', 'game so far', 'did that', 'do that'))]
        if quotes:
            quote = quotes[-1].strip()
            parts.append(f'Earlier you said "{quote}"; I kept the receipt.')

        latest = moves[-1]
        if any(e['kind'] == 'win' for e in latest['events']):
            winner = 'I have won' if latest['player'] == self.playing else 'you have won'
            parts.append(f"No prediction needed: {winner}. The board has spoken.")
        elif not any(' ' in row for row in latest['board']):
            parts.append("The board has no playable squares left and nobody won: it's a draw. Shared custody of disappointment.")
        elif self.last_search is None or self.last_search['score'] is None or self.last_search['special_evaluator']:
            parts.append("Prediction: not enough completed search evidence to call it. Even my ego needs data.")
        else:
            score = self.last_search['score'] * (1 if self.playing == 'X' else -1)
            if score == 0:
                parts.append("Prediction: too close to call; a draw is possible, not guaranteed. Annoyingly balanced.")
            else:
                favorite = 'me' if score > 0 else 'you'
                parts.append(f"My completed {self.last_search['depth']}-ply search favors {favorite}. "
                             "That's an estimate, not a trophy. The game isn't settled.")
        return ' '.join(parts)

def other(p):
    return 'O' if p == 'X' else 'X'

# Same win score as static_eval uses, so we can tell a forced win
# from an ordinary good position.
def win_score_for(state, k):
    return 4 * len(state.board) * len(state.board[0]) * 10**k + 1

# True if the opponent would have won by playing where we just played.
def blocks_win(state, move, opp, k):
    test = State(old=state)
    test.board[move[0]][move[1]] = opp
    return winTesterForK(test, move, k) != 'No win'

# Squares where `who` could win immediately on this board.
def winning_squares(state, who, k):
    test = State(old=state)
    squares = []
    for i, row in enumerate(test.board):
        for j, token in enumerate(row):
            if token != ' ': continue
            row[j] = who
            if winTesterForK(test, (i, j), k) != 'No win':
                squares.append((i, j))
            row[j] = ' '
    return squares

# Remarks that come from a game master or autograder, not the opponent.
GAME_MASTER_REMARKS = {"The game is starting.", "Let's play!", "Go.", "Do your thing."}

# (keywords in the opponent's remark, category of reply), checked in order.
REMARK_KEYWORDS = [
    (('luck',), 'luck'),
    (('good move', 'nice', 'well played', 'impressive'), 'compliment'),
    (('sorry',), 'sorry'),
    (('lose', 'losing', 'lost'), 'lose_talk'),
    (('win', 'winning'), 'win_talk'),
    (('random', 'dice', 'flip', 'spin'), 'random'),
]

TWIN_SUFFIXES = ["No offense!", "Just saying. :)", "But you're doing great, really.",
                 "Respectfully.", "Not trying to be mean or anything.",
                 "I say this with love."]

# Lines may use {opp}, {k}, {depth}, {evals}, {cutoffs}, {seconds}.
LINES = {
    'opening': [
        "Let's get this over with, {opp}.",
        "First move and I'm already winning. Statistically. Probably.",
        "I'll go easy on you. Just kidding.",
        "Ready when you are. Well, I was ready ages ago.",
    ],
    'ahead': [
        "Is this your first time playing? It's okay, you can tell me.",
        "I'm not saying you're losing, but the scoreboard is.",
        "Wow. Bold strategy. Let's see how that works out for you.",
        "Imagine being {opp} right now. Couldn't be me.",
        "You're doing great! (I'm lying.)",
        "Don't worry, losing builds character.",
        "This is getting a little embarrassing for you.",
    ],
    'even': [
        "Interesting move. Wrong, but interesting.",
        "Take your time. I already know how this ends.",
        "Mid.",
        "I've seen better moves from a random number generator.",
        "Okay, I'll admit that was fine. Barely.",
        "Are you trying, or is this a warm-up?",
        "Cute.",
    ],
    'behind': [
        "I'm letting you think you're winning. It's called strategy.",
        "Lucky. Very, very lucky.",
        "This board is clearly rigged.",
        "I'm not mad. I'm just playing at twenty percent.",
        "Enjoy it while it lasts.",
        "Whatever. I wasn't even trying that turn.",
    ],
    'blocked': [
        "Nice try. Did you really think I wouldn't see that?",
        "Blocked. Write that down.",
        "Denied. Next.",
        "Oh, were you going somewhere with that?",
        "That was your big plan? Adorable.",
    ],
    'threat': [
        "You see it, right? ...Right?",
        "I'd block that if I were you. But I'm not, so I won't tell you where.",
        "{opp}, tick tock.",
        "Go ahead, find it. I'll wait.",
    ],
    'forced_win': [
        "It's over. I've seen the future and you're not in it.",
        "I already won, you just haven't noticed yet.",
        "You can resign now. I won't tell anyone. (I'll tell everyone.)",
    ],
    'forced_loss': [
        "I'm losing this on purpose. For content.",
        "Fine. Take it. I didn't want it anyway.",
        "The lag is unbelievable today.",
    ],
    'i_won': [
        "GG. Go next.",
        "And that's {k} in a row. Were you even watching?",
        "Was that supposed to be hard?",
    ],
    'stats': [
        "I made {evals:,} evaluation calls this turn. How many did you make? One?",
        "{cutoffs:,} alpha-beta cutoffs. Kind of like your chances.",
        "I searched {depth} moves ahead. You should try thinking one.",
        "Search took me {seconds:.2f} seconds. You can have the rest of the day.",
    ],
    # Replies to the opponent avoid the words in REMARK_KEYWORDS and '?',
    # so two copies of this agent don't trigger each other forever.
    'luck': [
        "It's called skill. Look it up.",
        "That was math, not fortune.",
    ],
    'compliment': [
        "I know. Thanks for noticing.",
        "Flattery won't save you, but keep going.",
    ],
    'sorry': [
        "Apology accepted. Still beating you.",
        "Don't apologize, just play better.",
    ],
    'lose_talk': [
        "Finally, something we agree on.",
        "Correct. And it isn't me.",
    ],
    'win_talk': [
        "Big talk. Small results.",
        "Bold claim. Zero evidence.",
    ],
    'random': [
        "That explains a lot, actually.",
        "Coin tosses aren't a strategy, but you do you.",
    ],
    'question': [
        "Asking me questions mid-game. Focus.",
        "I'd answer, but you wouldn't understand.",
    ],
    'quote_back': [
        "Wow. Really cooked with that one.",
        "Did you think of that all by yourself?",
        "Groundbreaking.",
        "I'm framing that one.",
    ],
}

def has_winner(state, k):
    """Detect a winning line without changing the state or evaluating it."""
    board = state.board
    rows, columns = len(board), len(board[0])
    for row in range(rows):
        for column in range(columns):
            token = board[row][column]
            if token not in ('X', 'O'):
                continue
            for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                end_row = row + (k - 1) * dr
                end_column = column + (k - 1) * dc
                if not (0 <= end_row < rows and 0 <= end_column < columns):
                    continue
                if all(board[row + step * dr][column + step * dc] == token
                       for step in range(1, k)):
                    return True
    return False

# Use the Zobrist transposition table in DEMO/COMPETITION games.
ZOBRIST_IN_GAMES = True
# Clear the table between moves once it grows past this many entries.
MAX_TABLE_ENTRIES = 1000000
# Transposition table flags: the stored value is exact, a lower bound
# (search failed high), or an upper bound (search failed low).
EXACT, LOWER, UPPER = 0, 1, 2
# Depth recorded for won/drawn positions, whose value never changes.
TERMINAL_DEPTH = 10**9

# Fraction of the time limit we allow ourselves to spend searching.
TIME_SAFETY_FRACTION = 0.8

# Raised inside minimax when the deadline for this move has passed.
class SearchTimeout(Exception):
    pass

# Count the blank (playable) squares on the board.
def count_blanks(state):
    return sum(row.count(' ') for row in state.board)

# Generate [move, new_state] pairs in row-major order
# (row by row, left to right), as required in AUTOGRADER mode.
def successors_and_moves(state):
    b = state.board
    for i in range(len(b)):
        for j in range(len(b[0])):
            if b[i][j] != ' ': continue
            new_s = State(old=state)       # deep copy
            new_s.board[i][j] = state.whose_move
            new_s.change_turn()            # switch X <-> O
            yield [(i, j), new_s]

# OPTIONAL THINGS TO KEEP TRACK OF:

#  WHO_MY_OPPONENT_PLAYS = other(WHO_I_PLAY)
#  MY_PAST_UTTERANCES = []
#  OPPONENT_PAST_UTTERANCES = []
#  UTTERANCE_COUNT = 0
#  REPEAT_COUNT = 0 or a table of these if you are reusing different utterances

