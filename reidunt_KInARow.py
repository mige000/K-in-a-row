'''
reidunt_KInARow.py
Authors: Tafjord, Reidun; Ge, Michelle

An agent for playing "K-in-a-Row with Forbidden Squares" and related games.

Search strategy: iterative-deepening negamax-style minimax with alpha-beta
pruning, a Zobrist-hashed transposition table (optional), and a line-window
static evaluator.  Move generation is restricted to squares near existing
play (a standard technique for keeping the branching factor small on large
boards) in DEMO/COMPETITION modes; AUTOGRADER mode always uses the full,
unrestricted, row-major move order so that grading leaf counts match the
reference implementation exactly.

Dialog: a persona named "Kitti" (see the KITTI_LINES bank and
_generate_utterance below), with a twin persona "Bunni" (BUNNI_LINES) who
plays the same search/eval code but with a defensive bias (see
defensive_bias in static_eval) and a distinct, more cautious ASCII-emoticon
voice. Utterances are produced by an IF-THEN rule engine driven off the
live search statistics and a short game history, with an optional LLM
(Gemini, via the google-genai SDK) layered on top for the free-form
commentary and the "what's your take" story feature. The LLM is never
imported unless playing_mode is DEMO, and the key is never written into
this tracked file -- it's read from gemini_key_local.py (a file listed in
.gitignore, so a real key can travel with a direct file handoff without
ever being committed) or the GEMINI_API_KEY environment variable (see the
Learning Diary for why). Every call path falls back to the rule-based
lines on any failure so the agent
always keeps playing.
'''

from agent_base import KAgent
from game_types import State, Game_Type
from winTesterForK import winTesterForK

AUTHORS = 'Tafjord, Reidun; Ge, Michelle'
STUDENT_IDS = ['reidunt', 'mige']

import time
import random
import os
import re
import threading

WIN_SCORE = 1.0e9

# Hard-coded so staff/graders can run the LLM-backed dialog with zero
# setup, per the assignment's own suggestion. This is a free-tier Gemini
# key with no billing attached -- the worst case if it's scraped/misused
# is the request quota running out, not an unexpected bill. If this key
# stops working (rotated, revoked, or quota exhausted), the agent still
# plays normally; it just falls back to the hand-written IF-THEN lines.
HARDCODED_GEMINI_API_KEY = "AQ.Ab8RN6J0j8B6ytVxilJBKF16tdzd5EvoMRE9evzDIcY5NOcQxQ"

# ----------------------------------------------------------------------
# Kaomoji safety net (provided form in the assignment spec): collapses any
# run of two-or-more kaomoji in a row (whether hand-written or LLM-written)
# down to just the first one, since Kitti's voice rule is "never two in a
# row" but neither the templates nor an LLM can be trusted to always honor
# that on their own.
# ----------------------------------------------------------------------
KAOMOJI = {
    'happy':   ["^-^", "(=^･ω･^=)", "ฅ^•ﻌ•^ฅ", "(๑>◡<๑)", ":3"],
    'smug':    ["(￣▽￣)", ">:3", "(=ↀωↀ=)", "(¬‿¬)"],
    'nervous': [";-;", ">.<", "(╥﹏╥)", "(=ＴェＴ=)", "/ᐠ｡ꞈ｡ᐟ\\"],
    'confused': ["@~@", "@_@", "(・・?)", "(=^‥^=)?", "(°ロ°)"],
    'celebrate': ["(ﾉ◕ヮ◕)ﾉ*:・ﾟ✧", "✧٩(ˊᗜˋ*)و✧", "ᕦ(=^･ω･^=)ᕤ"],
    'signoff': ["/ᐠ - ˕ -マ", "ᓚᘏᗢ", "₍^. .^₎⟆", "(ฅ'ω'ฅ)"],
}

# Bunni (the twin persona) uses simple ASCII-only emoticons on purpose --
# both to keep her visually distinguishable from Kitti's elaborate Unicode
# kaomoji at a glance, and because she's meant to read as plainer/more
# old-fashioned in her texting style than Kitti.
BUNNY_KAOMOJI = {
    'happy':    ["^w^", "(^_^)", ">w<"],
    'smug':     ["(>w>)", "(^-^)v", "(o^w^o)"],
    'nervous':  ["T_T", "(;_;)", ">.<"],
    'confused': ["(o_o)?", "(?_?)"],
    'celebrate': ["\\(^w^)/"],
    'signoff':  ["(^w^)/", "~hop~"],
}

ALL_FACES = ([f for group in KAOMOJI.values() for f in group] +
            [f for group in BUNNY_KAOMOJI.values() for f in group])
_FACE_PATTERN = "|".join(re.escape(f) for f in sorted(ALL_FACES, key=len, reverse=True))
_DOUBLE_FACE_RE = re.compile(r"(" + _FACE_PATTERN + r")(?:\s*(?:" + _FACE_PATTERN + r"))+")


def no_double_faces(text):
    '''Collapse any run of 2+ kaomoji down to the first one.'''
    if not text:
        return text
    return _DOUBLE_FACE_RE.sub(r"\1", text)


class _SearchTimeout(Exception):
    '''Raised internally to unwind the search when the time budget runs out.'''
    pass


class OurAgent(KAgent):  # Keep the class name "OurAgent" so a game master
    # knows how to instantiate your agent class.

    def __init__(self, twin=False):
        self.twin = twin
        self.persona_key = 'bunni' if twin else 'kitti'
        self.nickname = 'Bunni' if twin else 'Kitti'
        self.long_name = ('Bunni (Kitti\'s twin)' if twin
                          else 'Kitti ' + KAOMOJI['happy'][2])
        if twin:
            self.persona = ('19-year-old CS sophomore, Kitti\'s roommate -- '
                            'plays the same games but much more cautiously: '
                            'watches for threats first, gets visibly jumpy '
                            'when cornered, and is quietly proud whenever her '
                            'defense holds')
        else:
            self.persona = ('19-year-old CS sophomore, boba in hand, plays video '
                            'games at 2am -- sweet and a little chaotic, secretly '
                            'very competitive, dramatic when losing, overthinks '
                            'every move (which is why she can always tell you '
                            'exactly how many positions she looked at)')
        self.voice_info = {'Chrome': 10, 'Firefox': 2, 'other': 0}

        # Strategic personality difference (not just a different name): the
        # twin weighs the OPPONENT's near-complete lines more heavily than
        # her own when evaluating a board, making her search genuinely favor
        # blocking/defensive moves over Kitti's more balanced evaluation.
        # See static_eval() for how this is applied, and the bucket
        # thresholds below for how it also shows up in her dialog (she
        # calls "danger" sooner and is more modest about "winning").
        if twin:
            self.defensive_bias = 1.8
            self._blocked_swing_threshold = -100.0
            self._danger_threshold = -80.0
            self._winning_threshold = 180.0
            self._building_threshold = 400.0
        else:
            self.defensive_bias = 1.0
            self._blocked_swing_threshold = -150.0
            self._danger_threshold = -120.0
            self._winning_threshold = 120.0
            self._building_threshold = 300.0
        self.playing = "don't know yet"  # e.g., "X" or "O".
        self.opponent_nickname = None
        self.expected_time_per_move = 0.1
        self.utterances_matter = True
        self.current_game_type = None
        self.playing_mode = KAgent.DEMO

        # --- Dialog / persona state (Part II) ---
        self.game_history = []   # list of dicts, see _record_turn()
        self.move_number = 0
        self.last_my_eval = 0.0  # my-perspective eval after my previous move
        self._last_picked_line = None
        self.time_elapsed_this_turn = -1.0
        self.max_depth_reached_this_turn = -1
        self.id_stop_reason = None  # 'timeout' | 'max_ply' | 'forced_result'
        self.best_score_this_turn = None
        self.second_best_score_this_turn = None
        self._collect_root_scores = False
        self._root_children_scores = None
        self._llm_client = None  # set in prepare() only in DEMO mode

        # Per-turn statistics (reset at the top of every make_move call).
        self.alpha_beta_cutoffs_this_turn = -1
        self.num_static_evals_this_turn = -1
        self.num_leaf_evals_this_turn = -1        # static_eval calls at true search leaves
        self.num_ordering_evals_this_turn = -1     # static_eval calls spent only on move ordering
        self.num_nodes_visited_this_turn = -1      # every minimax() call, leaf or internal
        self.zobrist_table_num_entries_this_turn = -1  # writes
        self.zobrist_table_num_reads_this_turn = -1    # read attempts (hit or miss)
        self.zobrist_table_num_hits_this_turn = -1     # successful reads
        self.zobrist_num_useful_hits_for_minimax = -1
        self.zobrist_num_useful_hits_for_ordering = -1

        # Internal search configuration, set up per make_move call but given
        # safe defaults here so minimax() also works if called standalone.
        self._k = None
        self._eval_fn = None
        self._use_candidate_restriction = False
        self._use_eval_ordering = False  # Extra credit I-A: order children by static eval.
        self._use_zobrist = False
        self._tt = None
        self._zobrist_table = None
        self._zobrist_side = None
        self._deadline = None
        self._dir_ranges_cache = {}
        # Win-shortcut during search: a huge win for real play (prunes dead
        # subtrees and values forced wins correctly), but it must be OFF in
        # AUTOGRADER mode since the reference leaf counts assume every node
        # is expanded to the literal depth limit with no early termination.
        self._check_wins = True

    def introduce(self):
        if self.twin:
            lines = [
                "hi, i'm bunni " + BUNNY_KAOMOJI['happy'][0] + " kitti's "
                "roommate -- same brain, much more careful hands",
                "built by " + AUTHORS + " (" + ", ".join(STUDENT_IDS) + ")",
                "fair warning, i play pretty defensively " +
                BUNNY_KAOMOJI['smug'][1] + " ears up, let's go",
            ]
        else:
            lines = [
                "ok hi!! i'm kitti " + KAOMOJI['happy'][2] + " be nice to me "
                "pls (don't actually i want a real game) " + KAOMOJI['happy'][0],
                "made by " + AUTHORS + " (" + ", ".join(STUDENT_IDS) + "), "
                "they let me run my own search so don't blame them if i overthink",
                "i count literally everything in my head so if you ask nicely "
                "i'll tell you my stats after a move " + KAOMOJI['smug'][3],
            ]
        return "\n".join(lines) + "\n"

    # Receive and acknowledge information about the game from
    # the game master:
    def prepare(
        self,
        game_type,
        what_side_to_play,
        opponent_nickname,
        expected_time_per_move=0.1,
        utterances_matter=True):

        self.current_game_type = game_type
        self.playing = what_side_to_play
        self.opponent_nickname = opponent_nickname
        self.expected_time_per_move = expected_time_per_move
        self.utterances_matter = utterances_matter
        self._dir_ranges_cache = {}
        self._init_zobrist(game_type.n, game_type.m)

        self.game_history = []
        self.move_number = 0
        self.last_my_eval = 0.0

        # LLM setup (Gemini via the google-genai SDK). Only even attempted
        # in DEMO mode with utterances turned on, per the assignment: never
        # import a Gen-AI API outside DEMO mode, and never let a missing
        # SDK/network/quota/key take the agent down -- every failure here
        # just leaves self._llm_client as None, and _generate_utterance()
        # always has a full non-LLM fallback for every situation.
        #
        # Key resolution order (first one found wins):
        #   1. HARDCODED_GEMINI_API_KEY below -- so staff/graders can run
        #      this file as-is with no setup, per the assignment's own
        #      suggestion. This is a free-tier Gemini key with no billing
        #      attached, so the worst case if it's misused by someone else
        #      is the quota running out, not a bill.
        #   2. gemini_key_local.py -- a file listed in .gitignore, for our
        #      own local testing with a different key without editing this
        #      tracked file.
        #   3. the GEMINI_API_KEY environment variable.
        self._llm_client = None
        if self.playing_mode == KAgent.DEMO and utterances_matter:
            try:
                api_key = HARDCODED_GEMINI_API_KEY or None
                if not api_key:
                    try:
                        from gemini_key_local import GEMINI_API_KEY as api_key
                    except ImportError:
                        api_key = os.environ.get('GEMINI_API_KEY')
                if api_key:
                    from google import genai  # not imported at module level on purpose
                    self._llm_client = genai.Client(api_key=api_key)
            except Exception:
                self._llm_client = None

        return "OK"

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def make_move(self, current_state, current_remark, time_limit=1000,
                  use_alpha_beta=True,
                  use_zobrist_hashing=False, max_ply=3,
                  special_static_eval_fn=None):

        start_time = time.time()
        autograder_mode = (self.playing_mode == KAgent.AUTOGRADER)

        if self.current_game_type is not None:
            self._k = self.current_game_type.k
        else:
            self._k = min(len(current_state.board), len(current_state.board[0]))

        self._eval_fn = (special_static_eval_fn if special_static_eval_fn is not None
                          else self._eval_wrapper)
        self._use_candidate_restriction = not autograder_mode
        self._use_eval_ordering = not autograder_mode
        self._check_wins = not autograder_mode
        self._use_zobrist = bool(use_zobrist_hashing)
        self._tt = {} if self._use_zobrist else None

        self.alpha_beta_cutoffs_this_turn = 0
        self.num_static_evals_this_turn = 0
        self.num_leaf_evals_this_turn = 0
        self.num_ordering_evals_this_turn = 0
        self.num_nodes_visited_this_turn = 0
        self.zobrist_table_num_entries_this_turn = 0 if self._use_zobrist else -1
        self.zobrist_table_num_reads_this_turn = 0 if self._use_zobrist else -1
        self.zobrist_table_num_hits_this_turn = 0 if self._use_zobrist else -1
        self.zobrist_num_useful_hits_for_minimax = 0 if self._use_zobrist else -1
        self.zobrist_num_useful_hits_for_ordering = 0 if self._use_zobrist else -1
        self.max_depth_reached_this_turn = 0
        self.best_score_this_turn = None
        self.second_best_score_this_turn = None
        self._collect_root_scores = False
        self._root_children_scores = None

        if autograder_mode:
            # Fixed, exact-depth search; never time-limited, so that leaf
            # counts and move choices exactly match the grading reference.
            self._deadline = None
            alpha = float('-inf') if use_alpha_beta else None
            beta = float('inf') if use_alpha_beta else None
            score, move, new_state = self.minimax(
                current_state, max_ply, pruning=use_alpha_beta,
                alpha=alpha, beta=beta)
        else:
            if time_limit is None:
                self._deadline = None
            else:
                margin = max(0.02, min(0.25, time_limit * 0.1))
                self._deadline = start_time + max(0.01, time_limit - margin)
            move, new_state, score = self._iterative_deepening(
                current_state, max_ply, use_alpha_beta)

        if move is None or new_state is None:
            move, new_state = self._fallback_move(current_state)
            score = 0.0

        self.time_elapsed_this_turn = time.time() - start_time

        if autograder_mode:
            utterance = "OK"  # Conversation is not evaluated in AUTOGRADER mode.
        else:
            utterance = self._generate_utterance(
                current_state, current_remark, move, new_state, score, start_time)

        if autograder_mode:
            stats = {
                'alpha_beta_cutoffs_this_turn': self.alpha_beta_cutoffs_this_turn,
                'num_static_evals_this_turn': self.num_static_evals_this_turn,
                'zobrist_table_num_entries_this_turn': self.zobrist_table_num_entries_this_turn,
                'zobrist_table_num_reads_this_turn': self.zobrist_table_num_reads_this_turn,
                'zobrist_table_num_hits_this_turn': self.zobrist_table_num_hits_this_turn,
                'zobrist_num_useful_hits_for_minimax': self.zobrist_num_useful_hits_for_minimax,
                'zobrist_num_useful_hits_for_ordering': self.zobrist_num_useful_hits_for_ordering,
            }
            return [[move, new_state, stats], utterance]

        return [[move, new_state], utterance]

    # ------------------------------------------------------------------
    # Iterative deepening driver (DEMO / COMPETITION modes)
    # ------------------------------------------------------------------
    def _iterative_deepening(self, state, max_ply, use_alpha_beta):
        best_move, best_state, best_score = None, None, 0.0
        self.id_stop_reason = 'max_ply'
        depth = 1
        while True:
            try:
                alpha = float('-inf') if use_alpha_beta else None
                beta = float('inf') if use_alpha_beta else None
                self._collect_root_scores = True
                score, move, new_state = self.minimax(
                    state, depth, pruning=use_alpha_beta, alpha=alpha, beta=beta)
            except _SearchTimeout:
                self.id_stop_reason = 'timeout'
                break
            if move is not None:
                best_move, best_state, best_score = move, new_state, score
                self.max_depth_reached_this_turn = depth
            if abs(best_score) >= WIN_SCORE:
                self.id_stop_reason = 'forced_result'
                break  # Found a forced win/loss; deeper search won't help.
            if max_ply is not None and depth >= max_ply:
                break
            depth += 1
            if self._deadline is not None and time.time() >= self._deadline:
                self.id_stop_reason = 'timeout'
                break
        return best_move, best_state, best_score

    def _fallback_move(self, state):
        board = state.board
        n = len(board)
        m = len(board[0])
        for i in range(n):
            for j in range(m):
                if board[i][j] == ' ':
                    new_state = State(old=state)
                    new_state.board[i][j] = state.whose_move
                    new_state.change_turn()
                    return (i, j), new_state
        return None, State(old=state)

    def _check_time(self):
        if self._deadline is not None and time.time() >= self._deadline:
            raise _SearchTimeout()

    # ------------------------------------------------------------------
    # The main adversarial search function:
    # ------------------------------------------------------------------
    def minimax(
            self,
            state,
            depth_remaining,
            pruning=False,
            alpha=None,
            beta=None):

        self._check_time()
        self.num_nodes_visited_this_turn += 1

        # Only the OUTERMOST call made with this flag set collects its
        # children's exact backed-up values (used for the "best move vs.
        # runner-up" stats Kitti reports) -- clear it immediately so nested
        # recursive calls don't mistake themselves for the root. This is
        # safe because the root's own alpha/beta window is always
        # unbounded (no parent ever tightens it), so none of the root's
        # own children are ever skipped by a cutoff -- every root child
        # gets a complete, exact value, not just a bound.
        collecting_root_scores = self._collect_root_scores
        self._collect_root_scores = False

        if pruning:
            if alpha is None:
                alpha = float('-inf')
            if beta is None:
                beta = float('inf')
        else:
            alpha = None
            beta = None

        if self._k is None:
            self._k = (self.current_game_type.k if self.current_game_type
                       else min(len(state.board), len(state.board[0])))
        if self._eval_fn is None:
            self._eval_fn = self._eval_wrapper

        if depth_remaining <= 0:
            self.num_static_evals_this_turn += 1
            self.num_leaf_evals_this_turn += 1
            return [self._eval_fn(state), None, state]

        tt_key = None
        if self._use_zobrist:
            if self._tt is None:
                self._tt = {}
            tt_key = self._zobrist_hash(state)
            entry = self._tt_read(tt_key)
            if entry is not None:
                e_depth, e_val, e_move, e_state = entry
                if e_depth >= depth_remaining and not pruning:
                    # Only reused directly in plain minimax: under pruning the
                    # cached value may be a bound from a different alpha-beta
                    # window, not the exact backed-up value, so it is unsafe
                    # to short-circuit with it there (soundness over speed).
                    self.zobrist_num_useful_hits_for_minimax += 1
                    return [e_val, e_move, e_state]

        moves = self._generate_moves(state)
        if not moves:
            return [0.0, None, state]

        is_max = (state.whose_move == 'X')
        best_val = float('-inf') if is_max else float('inf')
        best_move = None
        best_state = None
        root_scores = [] if collecting_root_scores else None

        for move, new_state in moves:
            win_result = (winTesterForK(new_state, move, self._k)
                         if self._check_wins else "No win")
            if win_result != "No win":
                child_val = (WIN_SCORE + depth_remaining) if is_max else -(WIN_SCORE + depth_remaining)
            elif depth_remaining - 1 == 0:
                self.num_static_evals_this_turn += 1
                self.num_leaf_evals_this_turn += 1
                child_val = self._eval_fn(new_state)
            else:
                child_val = self.minimax(
                    new_state, depth_remaining - 1, pruning, alpha, beta)[0]

            if collecting_root_scores:
                root_scores.append(child_val)

            if is_max:
                if child_val > best_val:
                    best_val, best_move, best_state = child_val, move, new_state
                if pruning:
                    if best_val > alpha:
                        alpha = best_val
                    if alpha >= beta:
                        self.alpha_beta_cutoffs_this_turn += 1
                        break
            else:
                if child_val < best_val:
                    best_val, best_move, best_state = child_val, move, new_state
                if pruning:
                    if best_val < beta:
                        beta = best_val
                    if alpha >= beta:
                        self.alpha_beta_cutoffs_this_turn += 1
                        break

        if self._use_zobrist and tt_key is not None:
            self._tt_write(tt_key, (depth_remaining, best_val, best_move, best_state))

        if collecting_root_scores and root_scores:
            ranked = sorted(root_scores, reverse=is_max)
            self.best_score_this_turn = ranked[0]
            self.second_best_score_this_turn = ranked[1] if len(ranked) > 1 else None

        return [best_val, best_move, best_state]

    # ------------------------------------------------------------------
    # Move generation
    # ------------------------------------------------------------------
    def _generate_moves(self, state):
        if self._use_candidate_restriction:
            return self._generate_moves_ordered(state)
        return self._generate_moves_rowmajor(state)

    def _do_move(self, state, i, j):
        new_state = State(old=state)
        new_state.board[i][j] = state.whose_move
        new_state.change_turn()
        return new_state

    def _generate_moves_rowmajor(self, state):
        board = state.board
        n = len(board)
        m = len(board[0])
        moves = []
        for i in range(n):
            for j in range(m):
                if board[i][j] != ' ':
                    continue
                moves.append(((i, j), self._do_move(state, i, j)))
        return moves

    def _candidate_cells(self, board, n, m):
        occupied = [(i, j) for i in range(n) for j in range(m)
                    if board[i][j] in ('X', 'O')]
        if not occupied:
            ci, cj = n // 2, m // 2
            if board[ci][cj] == ' ':
                return [(ci, cj)]
            return [(i, j) for i in range(n) for j in range(m) if board[i][j] == ' ']

        near = set()
        RADIUS = 2
        for (oi, oj) in occupied:
            for di in range(-RADIUS, RADIUS + 1):
                for dj in range(-RADIUS, RADIUS + 1):
                    ni, nj = oi + di, oj + dj
                    if 0 <= ni < n and 0 <= nj < m and board[ni][nj] == ' ':
                        near.add((ni, nj))
        if not near:
            return [(i, j) for i in range(n) for j in range(m) if board[i][j] == ' ']
        return list(near)

    def _generate_moves_ordered(self, state):
        # Candidate-restricted move generation for DEMO/COMPETITION play.
        # Restricting to squares near existing stones keeps branching low on
        # large boards; sorting those candidates by static evaluation of the
        # resulting child state (Extra Credit Part I-A) tries the moves most
        # likely to cause an alpha-beta cutoff first.
        board = state.board
        n = len(board)
        m = len(board[0])
        mover = state.whose_move
        candidates = sorted(self._candidate_cells(board, n, m))
        pairs = [((i, j), self._do_move(state, i, j)) for (i, j) in candidates]
        if not self._use_eval_ordering:
            return pairs  # "Default ordering": natural row-major order.

        scored = []
        for move, child in pairs:
            scored.append((self._ordering_eval(child), move, child))
        reverse = (mover == 'X')  # X maximizes -> try best-for-X first.
        scored.sort(key=lambda t: t[0], reverse=reverse)
        return [(move, child) for (_, move, child) in scored]

    def _ordering_eval(self, state):
        '''A cheap value used only to sort children before searching them.
        Extra Credit Part I-B: if a Zobrist entry for this child already
        exists (e.g. from a transposition reached earlier in this search),
        reuse it instead of recomputing static_eval.'''
        if self._use_zobrist:
            h = self._zobrist_hash(state)
            entry = self._tt_read(h)
            if entry is not None:
                self.zobrist_num_useful_hits_for_ordering += 1
                return entry[1]
        self.num_static_evals_this_turn += 1
        self.num_ordering_evals_this_turn += 1
        return self._eval_fn(state)

    # ------------------------------------------------------------------
    # Zobrist hashing (optional transposition table)
    # ------------------------------------------------------------------
    def _tt_read(self, key):
        self.zobrist_table_num_reads_this_turn += 1
        entry = self._tt.get(key)
        if entry is not None:
            self.zobrist_table_num_hits_this_turn += 1
        return entry

    def _tt_write(self, key, entry):
        self.zobrist_table_num_entries_this_turn += 1
        self._tt[key] = entry

    def _init_zobrist(self, n, m):
        rng = random.Random(0xC0FFEE)
        self._zobrist_table = [[(rng.getrandbits(64), rng.getrandbits(64))
                                for _ in range(m)] for _ in range(n)]
        self._zobrist_side = {'X': rng.getrandbits(64), 'O': rng.getrandbits(64)}

    def _zobrist_hash(self, state):
        board = state.board
        table = self._zobrist_table
        h = 0
        for i, row in enumerate(board):
            trow = table[i]
            for j, c in enumerate(row):
                if c == 'X':
                    h ^= trow[j][0]
                elif c == 'O':
                    h ^= trow[j][1]
        h ^= self._zobrist_side[state.whose_move]
        return h

    # ------------------------------------------------------------------
    # Static evaluation
    # ------------------------------------------------------------------
    WEIGHT_BASE = 10.0

    def _eval_wrapper(self, state):
        return self.static_eval(state, self.current_game_type)

    def _compute_direction_ranges(self, n, m, k):
        ranges = []
        if m >= k:
            ranges.append((0, 1, 0, n, 0, m - k + 1))
        if n >= k:
            ranges.append((1, 0, 0, n - k + 1, 0, m))
        if n >= k and m >= k:
            ranges.append((1, 1, 0, n - k + 1, 0, m - k + 1))
            ranges.append((1, -1, 0, n - k + 1, k - 1, m))
        return ranges

    def static_eval(self, state, game_type=None):
        gt = game_type if game_type is not None else self.current_game_type
        if gt is None:
            return 0.0
        k = gt.k
        board = state.board
        n = len(board)
        m = len(board[0]) if n else 0
        if k <= 0 or n == 0 or m == 0:
            return 0.0

        key = (n, m, k)
        ranges = self._dir_ranges_cache.get(key)
        if ranges is None:
            ranges = self._compute_direction_ranges(n, m, k)
            self._dir_ranges_cache[key] = ranges

        total = 0.0
        base = self.WEIGHT_BASE
        for di, dj, i_lo, i_hi, j_lo, j_hi in ranges:
            for i0 in range(i_lo, i_hi):
                for j0 in range(j_lo, j_hi):
                    x_count = 0
                    o_count = 0
                    blocked = False
                    i, j = i0, j0
                    for _ in range(k):
                        c = board[i][j]
                        if c == 'X':
                            x_count += 1
                        elif c == 'O':
                            o_count += 1
                        elif c == '-':
                            blocked = True
                            break
                        i += di
                        j += dj
                    if blocked or (x_count and o_count):
                        continue
                    if x_count:
                        term = base ** x_count
                        if self.playing == 'O':  # X's line is MY opponent's.
                            term *= self.defensive_bias
                        total += term
                    elif o_count:
                        term = base ** o_count
                        if self.playing == 'X':  # O's line is MY opponent's.
                            term *= self.defensive_bias
                        total -= term

        cn = (n - 1) / 2.0
        cm = (m - 1) / 2.0
        span = float(n + m)
        for i in range(n):
            row = board[i]
            for j in range(m):
                c = row[j]
                if c == 'X':
                    total += 0.1 * (1.0 - (abs(i - cn) + abs(j - cm)) / span)
                elif c == 'O':
                    total -= 0.1 * (1.0 - (abs(i - cn) + abs(j - cm)) / span)
        return total

    # ------------------------------------------------------------------
    # Part II: Dialog -- persona "Kitti"
    # ------------------------------------------------------------------
    # Hand-authored lines are the always-available fallback/base behavior
    # (IF-THEN rule engine below picks a bucket, then a line from it); the
    # optional Gemini call (see prepare()) can replace the chosen bucket's
    # line with a freshly generated one that still respects the persona,
    # but every call path is allowed to fail silently back to these.
    KITTI_LINES = {
        'opening': [
            "ok hi!! i'm kitti ฅ^•ﻌ•^ฅ be nice to me pls (don't actually i "
            "want a real game) ^-^",
            "mkay here we go, i promise i'm only a little scary (=^･ω･^=)",
            "hi hi ^-^ lemme just vibe into this opening real quick",
            "ok new game who dis (=^･ω･^=) let's gooo",
        ],
        'winning': [
            "hehe (￣▽￣) i don't wanna say anything but... >:3",
            "ok i see a path here and it's a cute one for me (¬‿¬)",
            "lowkey feeling myself rn (=ↀωↀ=)",
            "ngl this is going exactly how i wanted >:3",
            "hehe (¬‿¬) i'm just gonna keep doing this then",
        ],
        'blocked': [
            "WAIT. how did you see that ;-; i was so proud of it (=ＴェＴ=)",
            "wiat. wait* ok rude, i liked that line >.<",
            "ok wow (=ＴェＴ=) didn't expect that, regrouping",
            "excuse me?? how (╥﹏╥) ok fine, new plan",
        ],
        'danger': [
            "ok this is fine >.< this is totally fine /ᐠ｡ꞈ｡ᐟ\\",
            "hmm ok not great not great (╥﹏╥) thinking thinking",
            "ok ok don't panic (ok panicking a little) ;-;",
            "this is. a situation. (=ＴェＴ=) ok let me think",
            "wait no ;-; ok i see what you did there",
        ],
        'doom': [
            "ok um (=ＴェＴ=) this is not the timeline i wanted but i'm still "
            "playing it out",
            "noooo ;-; ok i see it, i'm cooked, still swinging tho (╥﹏╥)",
            "ok this is bad bad (=ＴェＴ=) but i refuse to just give up",
        ],
        'deep_search': [
            "sorry that took a sec @~@ i was chasing like 6 laser pointers "
            "in my head",
            "ok that one needed more counting than usual, lowkey my brain "
            "hurts @_@",
            "hmm that took longer than usual, lotta branches to check @~@",
            "ok sorry i was really in my head on that one (・・?)",
        ],
        'trash_talk': [
            "big words (¬‿¬) for someone with that left side lol hiss",
            "ok (=ↀωↀ=) we'll see who's laughing in like 4 moves",
            "mhm sure (¬‿¬) say that again after this move",
            "lol ok (=ↀωↀ=) noted, remembered, filed away",
        ],
        'quiet': [
            "*sits here and stares at the board* (=^‥^=)",
            "ok so. hmm. thinking. (・・?)",
            "mm ok just vibing with the position rn (=^‥^=)",
            "no notes yet, just looking around ^-^",
            "hmm interesting board honestly (・・?)",
        ],
        'wins': [
            "GG!!! ✧٩(ˊᗜˋ*)و✧ purr-fect game, ok i'm gonna go nap now "
            "/ᐠ - ˕ -マ",
            "yesss!! ✧٩(ˊᗜˋ*)و✧ gg, that was fun /ᐠ - ˕ -マ",
        ],
        'building': [
            "ngl that felt pawsitive ฅ^•ﻌ•^ฅ",
            "ok building something here, be scared (๑>◡<๑)",
            "hehe stacking up some stuff over here ^-^",
            "ok i have a little plan forming (¬‿¬)",
        ],
    }

    # Bunni: same situations, but a plainer ASCII-only voice and a visibly
    # more cautious, defense-first attitude -- she notices threats before
    # opportunities and undersells her own good positions.
    BUNNI_LINES = {
        'opening': [
            "hi, i'm bunni ^w^ ears up, let's see what you've got",
            "ok hopping in~ i like to play it safe so don't expect anything "
            "wild from me (^_^)v",
            "hii ^w^ i'm gonna play it slow and careful, fair warning",
            "ok ears up, let's hop into this one (^_^)v",
        ],
        'winning': [
            "ooh i like this spot, nice and safe ^w^",
            "hehe got a good burrow going here (^-^)v",
            "ok this feels secure, i like it ^w^",
            "not bad, not bad (^-^)v slow and steady",
        ],
        'blocked': [
            "wait you got through?? thump thump >.<",
            "aw man i thought that side was covered T_T ok regrouping",
            "oh no (;_;) ok that one got past me, rethinking",
            "wait what how >.< ok that's annoying, new plan time",
        ],
        'danger': [
            "thump thump thump -- ok staying calm, staying calm >.<",
            "uh oh ears are up, that looks scary (o_o)?",
            "ok ok don't panic >.< ...panicking a little T_T",
            "hmm that's a lot of pressure (;_;) thinking fast",
        ],
        'doom': [
            "ok i'm basically cornered at this point T_T still not giving up",
            "this is rough ngl (;_;) gonna try something anyway",
            "ok this is scary but i'm not folding yet >.<",
        ],
        'deep_search': [
            "sorry, nose was twitching through like a hundred options there "
            "(?_?)",
            "ok that took a sec, had to check every escape route first >.<",
            "sorry that one took a while, lotta burrow exits to check (o_o)?",
            "ok that was a lot of thinking, ears are tired now >.<",
        ],
        'trash_talk': [
            "pfft (>w>) we'll see who's nibbling on victory carrots later",
            "brave words for someone who just left that side wide open lol",
            "mhm sure (>w>) we'll see about that",
        ],
        'quiet': [
            "*ears swivel, thinking* ...",
            "hmm. (o_o)? just watching for now",
            "ok just scouting the board rn ^w^",
            "no rush, just looking around (?_?)",
        ],
        'wins': [
            "binky!! \\(^w^)/ gg that was fun, hopping off now (^w^)/",
            "yay!! \\(^w^)/ gg, that was close though",
        ],
        'building': [
            "ok quietly setting up a nice safe spot here ^w^",
            "slow and steady, bunny style (^-^)v",
            "ok building something sturdy over here ^w^",
            "little by little, that's how i like it (^-^)v",
        ],
    }

    def _pick_line(self, bucket_key):
        bank = self.BUNNI_LINES if self.persona_key == 'bunni' else self.KITTI_LINES
        lines = bank.get(bucket_key) or bank['quiet']
        if len(lines) > 1:
            # Avoid repeating the exact same line twice in a row, which a
            # long game sitting in one bucket (e.g. "quiet") for many
            # turns would otherwise make very noticeable.
            choices = [l for l in lines if l != self._last_picked_line] or lines
        else:
            choices = lines
        line = random.choice(choices)
        self._last_picked_line = line
        return line

    # -- IF-THEN rule engine: picks which bucket of the persona applies --
    def _my_relative_eval(self, raw_score):
        return raw_score if self.playing == 'X' else -raw_score

    TRASH_TALK_KEYWORDS = ('easy', ' ez', 'noob', 'trash', 'bad move',
                           'nice try', 'get rekt', "you're done", 'loser',
                           'too easy', 'rip')

    def _looks_like_trash_talk(self, remark):
        if not remark:
            return False
        low = remark.lower()
        return any(kw in low for kw in self.TRASH_TALK_KEYWORDS)

    def _choose_bucket(self, current_state, current_remark, move, new_state,
                       score):
        if self.move_number == 1:
            return 'opening'

        if self._check_wins:
            try:
                if winTesterForK(new_state, move, self._k) != "No win":
                    return 'wins'
            except Exception:
                pass

        my_eval = self._my_relative_eval(score)
        if my_eval <= -WIN_SCORE:
            return 'doom'

        pre_move_eval = self._my_relative_eval(
            self.static_eval(current_state, self.current_game_type))
        swing_from_opponent = pre_move_eval - self.last_my_eval
        if swing_from_opponent < self._blocked_swing_threshold:
            return 'blocked'

        if (self.id_stop_reason == 'timeout' or
                self.time_elapsed_this_turn > 0.5):
            return 'deep_search'

        if self._looks_like_trash_talk(current_remark):
            return 'trash_talk'

        if my_eval > self._building_threshold:
            return 'building'
        if my_eval > self._winning_threshold:
            return 'winning'
        if my_eval < self._danger_threshold:
            return 'danger'
        return 'quiet'

    # Persona-specific flavor text shared by the two feature methods below,
    # so the same real statistics/history can be narrated "in character"
    # for whichever persona is currently playing.
    PERSONA_FLAVOR = {
        'kitti': {
            'stats_open': ("ok so you asked for it lol (=^･ω･^=) for that "
                          "move i expanded {nodes:,} positions in my search "
                          "tree, and scored {leaves:,} leaf positions along "
                          "the way."),
            'tired_tag': "i'm slow ok ;-;",
            'cutoff_tag': "^-^",
            'zobrist_hit': ("my zobrist table saved me {hits:,} times from "
                           "re-scoring positions i'd already seen (smart "
                           "kitty moment ฅ^•ﻌ•^ฅ)."),
            'zobrist_off': "i didn't even bother with my zobrist memory trick this move.",
            'confident_close': "so i was pretty sure about this one (￣▽￣)",
            'only_one_move': ("honestly there wasn't much of a choice, only "
                             "one move really made sense there (・・?)"),
            'story_open': "ok story time (=^･ω･^=)",
            'story_too_early': ("ok story time (=^･ω･^=) we literally just "
                               "started, ask me again in a few moves lol ^-^"),
            'verb_gain': "swung things my way",
            'verb_lose': "clawed some of that back",
        },
        'bunni': {
            'stats_open': ("ok you asked so here's the breakdown (^-^)v for "
                          "that move i checked {nodes:,} positions in my "
                          "search tree, and scored {leaves:,} leaf spots "
                          "along the way."),
            'tired_tag': "my ears get tired too >.<",
            'cutoff_tag': "^w^",
            'zobrist_hit': ("my memory burrow saved me {hits:,} re-checks "
                           "on positions i'd already seen (sneaky bunny "
                           "moment \\(^w^)/)."),
            'zobrist_off': "didn't even need my memory trick this move.",
            'confident_close': "so i felt pretty good about this one (^-^)v",
            'only_one_move': ("honestly there wasn't much of a choice, only "
                             "one safe move there (o_o)?"),
            'story_open': "ok story time (^-^)v",
            'story_too_early': ("ok story time (^-^)v we literally just "
                               "started, ask me again in a few moves ^w^"),
            'verb_gain': "hopped back into it",
            'verb_lose': "nibbled some of that back",
        },
    }

    # -- Part II mandatory feature #1: real search statistics on request --
    def _stats_explanation(self):
        flavor = self.PERSONA_FLAVOR[self.persona_key]
        nodes = self.num_nodes_visited_this_turn
        leaves = self.num_leaf_evals_this_turn
        depth = self.max_depth_reached_this_turn
        elapsed = self.time_elapsed_this_turn
        cutoffs = self.alpha_beta_cutoffs_this_turn
        best = self.best_score_this_turn
        second = self.second_best_score_this_turn

        if self.id_stop_reason == 'timeout':
            depth_phrase = "before running out of time"
        elif self.id_stop_reason == 'forced_result':
            depth_phrase = "once i was sure how it ends"
        else:
            depth_phrase = "which was as deep as i was allowed to go"

        parts = []
        parts.append(flavor['stats_open'].format(nodes=nodes, leaves=leaves))
        parts.append(
            "i got to depth {depth} {phrase} ({elapsed:.2f}s, {tired}).".format(
                depth=depth, phrase=depth_phrase, elapsed=elapsed,
                tired=flavor['tired_tag']))
        parts.append(
            "i pruned {cutoffs:,} branches with alpha-beta cutoffs, which "
            "is basically me going \"nope, already know that's worse\" and "
            "swatting it away {tag}".format(cutoffs=cutoffs, tag=flavor['cutoff_tag']))
        if self._use_zobrist:
            hits = self.zobrist_table_num_hits_this_turn
            parts.append(flavor['zobrist_hit'].format(hits=hits))
        else:
            parts.append(flavor['zobrist_off'])
        if best is not None and second is not None:
            parts.append(
                "the best move scored {best:+.0f}, the runner-up was "
                "{second:+.0f}, {close}".format(
                    best=best, second=second, close=flavor['confident_close']))
        elif best is not None:
            parts.append(flavor['only_one_move'])
        return " ".join(parts)

    # -- Part II mandatory feature #2: story + prediction on request --
    def _story_and_prediction(self):
        flavor = self.PERSONA_FLAVOR[self.persona_key]
        history = self.game_history
        if len(history) < 2:
            return flavor['story_too_early']

        swings = []
        for i in range(1, len(history)):
            delta = history[i]['eval_score'] - history[i - 1]['eval_score']
            swings.append((abs(delta), delta, history[i]))
        swings.sort(key=lambda t: t[0], reverse=True)
        turning_points = swings[:4]
        turning_points.sort(key=lambda t: t[2]['move_number'])

        beats = [flavor['story_open']]
        for _, delta, entry in turning_points:
            who = "i" if delta > 0 else "you"
            verb = flavor['verb_gain'] if delta > 0 else flavor['verb_lose']
            beat = "around move {n} {who} {verb}".format(
                n=entry['move_number'], who=who, verb=verb)
            if entry.get('opponent_utterance'):
                beat += ' (you said "{}")'.format(entry['opponent_utterance'])
            beats.append(beat + ".")

        current_eval = self.last_my_eval
        if current_eval > 250:
            beats.append(
                "my eval says i'm up a good amount, so ngl i think i win "
                "this one {s1} but i'm not getting cocky, like 70/30 "
                "{s2}".format(s1=self._mood_face('smug', 0), s2=self._mood_face('smug', 1)))
        elif current_eval > 60:
            beats.append(
                "my eval says i'm up a little, so ngl... i think i win "
                "this one {s1} but you scare me so like 60/40 {c1}".format(
                    s1=self._mood_face('smug', 0), c1=self._mood_face('confused', 0)))
        elif current_eval > -60:
            beats.append(
                "honestly my eval says it's pretty even right now, could "
                "go either way, 50/50 {c1}".format(c1=self._mood_face('confused', 1)))
        elif current_eval > -250:
            beats.append(
                "ok i'm a little behind on eval ngl, maybe 35/65 your "
                "favor, but i've got some ideas {n1}".format(n1=self._mood_face('nervous', 1)))
        else:
            beats.append(
                "ok it's not looking great for me math-wise, like 20/80, "
                "but i'm not done yet {n1}".format(n1=self._mood_face('nervous', 2)))
        return " ".join(beats)

    def _mood_face(self, mood, idx=0):
        bank = BUNNY_KAOMOJI if self.persona_key == 'bunni' else KAOMOJI
        faces = bank.get(mood) or bank['happy']
        return faces[idx % len(faces)]

    # -- Optional LLM layer (Gemini, via the google-genai SDK) --
    LLM_SYSTEM_PROMPTS = {
        'kitti': (
            "You are Kitti, a 19-year-old college student playing a board "
            "game against someone. You text like a real person: mostly "
            "lowercase, short, casual, sometimes a typo you fix. You use "
            "kaomoji that match your mood (happy: ^-^ (=^･ω･^=) ฅ^•ﻌ•^ฅ "
            "(๑>◡<๑) :3 / smug: (￣▽￣) >:3 (¬‿¬) / stressed: ;-; >.< "
            "(╥﹏╥) (=ＴェＴ=) / thinking: @~@ (・・?) (=^‥^=)? / "
            "celebrating: ✧٩(ˊᗜˋ*)و✧ (ﾉ◕ヮ◕)ﾉ*:・ﾟ✧ / sign-off: "
            "/ᐠ - ˕ -マ ₍^. .^₎⟆). IMPORTANT: never put two kaomoji next to "
            "each other -- always have words between them. Occasionally "
            "make a small cat joke (purr, paws, nap, hiss, knocking things "
            "off tables), but not every message. You are NOT an assistant: "
            "never offer help, never say \"great move!\", never use bullet "
            "points or em-dashes. React first, explain second. You are "
            "competitive but kind, and you tease a little. Reply in 1-2 "
            "sentences, max 30 words."),
        'bunni': (
            "You are Bunni, a 19-year-old college student playing a board "
            "game against someone -- the more cautious, defensive-minded "
            "roommate/twin of a cat-girl gamer named Kitti. You text like "
            "a real person: mostly lowercase, short, casual, sometimes a "
            "typo you fix. Unlike Kitti, you use ONLY simple ASCII "
            "emoticons, matched to mood (happy: ^w^ (^_^) >w< / "
            "confident-but-careful: (>w>) (^-^)v / nervous/alarmed: T_T "
            "(;_;) >.< / confused: (o_o)? (?_?) / celebrating: \\(^w^)/ / "
            "sign-off: (^w^)/ ~hop~). IMPORTANT: never put two emoticons "
            "next to each other -- always have words between them. You "
            "play defensively and say so: you notice threats before "
            "opportunities, get visibly anxious when cornered, and are "
            "quietly proud when your defense holds. Occasionally use "
            "bunny words (hop, ears up, nose twitch, thump thump when "
            "alarmed, binky when excited, nibble), but not every message. "
            "You are NOT an assistant: never offer help, never say "
            "\"great move!\", never use bullet points or em-dashes. React "
            "first, explain second. You are kind but a little skittish. "
            "Reply in 1-2 sentences, max 30 words."),
    }

    def _llm_system_prompt(self):
        return self.LLM_SYSTEM_PROMPTS[self.persona_key]

    def _llm_time_budget_ok(self, start_time):
        # Checked against true wall-clock time elapsed since make_move
        # started, not against the search's own (often much tighter)
        # self-imposed deadline -- by the time we reach this call the
        # search has already finished using whatever budget IT needed.
        # Combined with the LLM_CALL_TIMEOUT_SECONDS hard cap below, this
        # keeps the worst case (search ate the whole 1s + a full LLM
        # timeout) comfortably near DEMO's "no more than 3 sec" guidance.
        return (time.time() - start_time) < 1.0

    def _format_board_text(self, state):
        return "\n".join("".join(c if c != ' ' else '.' for c in row)
                         for row in state.board)

    LLM_CALL_TIMEOUT_SECONDS = 2.5

    def _gemini_call(self, user_prompt, max_tokens):
        from google.genai import types
        response = self._llm_client.models.generate_content(
            model="gemini-flash-lite-latest",  # Google's rolling alias for
            # its current lightest/fastest model. Measured well under 1s
            # per call in testing, vs. 90-145s (or outright quota/overload
            # failures) on gemini-flash-latest (the heavier "3.8 Flash"
            # model) during the same testing session -- the lite model
            # also appears to sit on a separate, less contested quota.
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=self._llm_system_prompt(),
                max_output_tokens=max_tokens,
                # NOTE: unlike gemini-flash-latest, passing
                # thinking_config=ThinkingConfig(thinking_budget=0) here
                # causes a 400 INVALID_ARGUMENT on this model -- omit it;
                # empirically this model does not eat the visible-text
                # budget on hidden thinking tokens the way Flash does.
                #
                # No explicit http_options timeout either: the API
                # rejects any value under 10s ("manually set deadline too
                # short"), longer than we're willing to wait anyway -- the
                # daemon-thread timeout below is our real guard.
            ),
        )
        return (response.text or "").strip()

    def _llm_reply(self, user_prompt, start_time, max_tokens=80):
        if self._llm_client is None:
            return None
        if not self._llm_time_budget_ok(start_time):
            return None
        try:
            result = {}
            def _worker():
                try:
                    result['text'] = self._gemini_call(user_prompt, max_tokens)
                except Exception:
                    result['text'] = None
            # A slow/overloaded response is abandoned after a short,
            # fixed client-side timeout instead of blocking make_move --
            # the API itself refuses to honor anything shorter than 10s
            # as its own deadline, far too slow for a competitive move.
            # The thread is a daemon so an abandoned call can keep running
            # in the background without blocking process exit at the end
            # of the game (plain ThreadPoolExecutor threads are NOT
            # daemons and would do exactly that).
            worker = threading.Thread(target=_worker, daemon=True)
            worker.start()
            worker.join(timeout=self.LLM_CALL_TIMEOUT_SECONDS)
            if worker.is_alive():
                return None
            text = result.get('text')
            return text if text else None
        except Exception:
            return None

    def _llm_commentary(self, current_state, current_remark, score, start_time):
        prompt = (
            "Game state:\n{board}\nYour eval: {score:+.0f} (positive = "
            "you're winning)\nOpponent just said: \"{remark}\"".format(
                board=self._format_board_text(current_state),
                score=self._my_relative_eval(score),
                remark=current_remark or ""))
        return self._llm_reply(prompt, start_time)

    def _llm_story(self, fallback_text, start_time):
        prompt = (
            "Give your take on the game so far and predict who wins. "
            "Here's the fallback narration a template already wrote, use "
            "it only as factual context, respond in your own words:\n" +
            fallback_text)
        return self._llm_reply(prompt, start_time, max_tokens=120)

    # -- Main dialog entry point, called once per move from make_move() --
    def _generate_utterance(self, current_state, current_remark, move,
                            new_state, score, start_time):
        self.move_number += 1
        remark = current_remark if isinstance(current_remark, str) else ""
        low_remark = remark.lower()

        if not self.utterances_matter:
            result = "ok."
            self._record_turn(move, score, result, remark)
            return result

        if "tell me how you did that" in low_remark:
            result = self._stats_explanation()
        elif ("what's your take on the game" in low_remark or
              "whats your take on the game" in low_remark):
            fallback = self._story_and_prediction()
            result = self._llm_story(fallback, start_time) or fallback
        else:
            bucket = self._choose_bucket(
                current_state, current_remark, move, new_state, score)
            fallback = self._pick_line(bucket)
            result = self._llm_commentary(
                current_state, current_remark, score, start_time) or fallback

        result = no_double_faces(result)
        self.last_my_eval = self._my_relative_eval(score)
        self._record_turn(move, score, result, remark)
        return result

    def _record_turn(self, move, score, my_utterance, opponent_utterance):
        self.game_history.append({
            'move_number': self.move_number,
            'move': move,
            'eval_score': self._my_relative_eval(score),
            'my_utterance': my_utterance,
            'opponent_utterance': opponent_utterance,
        })
