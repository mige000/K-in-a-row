'''
<yourID>_KInARow.py
Authors: <TODO: your name(s) here, lastname first and partners separated by ";">
  Example:
    Authors: Smith, Jane; Lee, Laura

An agent for playing "K-in-a-Row with Forbidden Squares" and related games.

Search strategy: iterative-deepening negamax-style minimax with alpha-beta
pruning, a Zobrist-hashed transposition table (optional), and a line-window
static evaluator.  Move generation is restricted to squares near existing
play (a standard technique for keeping the branching factor small on large
boards) in DEMO/COMPETITION modes; AUTOGRADER mode always uses the full,
unrestricted, row-major move order so that grading leaf counts match the
reference implementation exactly.
'''

from agent_base import KAgent
from game_types import State, Game_Type
from winTesterForK import winTesterForK

AUTHORS = 'LastName, FirstName'   # TODO: fill in. First ID must match the
STUDENT_IDS = ['your_student_id']  # filename, e.g. jsmith99_KInARow.py.

import time
import random

WIN_SCORE = 1.0e9


class _SearchTimeout(Exception):
    '''Raised internally to unwind the search when the time budget runs out.'''
    pass


class OurAgent(KAgent):  # Keep the class name "OurAgent" so a game master
    # knows how to instantiate your agent class.

    def __init__(self, twin=False):
        self.twin = twin
        self.nickname = 'Vector'
        if twin:
            self.nickname = 'Covector'
        self.long_name = 'Alpha Vector'
        if twin:
            self.long_name += ' (Twin)'
        self.persona = 'confident, terse strategist'
        self.voice_info = {'Chrome': 10, 'Firefox': 2, 'other': 0}
        self.playing = "don't know yet"  # e.g., "X" or "O".
        self.opponent_nickname = None
        self.expected_time_per_move = 0.1
        self.utterances_matter = True
        self.current_game_type = None
        self.playing_mode = KAgent.DEMO

        # Per-turn statistics (reset at the top of every make_move call).
        self.alpha_beta_cutoffs_this_turn = -1
        self.num_static_evals_this_turn = -1
        self.zobrist_table_num_entries_this_turn = -1
        self.zobrist_table_num_hits_this_turn = -1
        self.zobrist_num_useful_hits_for_minimax = -1
        self.zobrist_num_useful_hits_for_ordering = -1

        # Internal search configuration, set up per make_move call but given
        # safe defaults here so minimax() also works if called standalone.
        self._k = None
        self._eval_fn = None
        self._use_candidate_restriction = False
        self._use_zobrist = False
        self._tt = None
        self._zobrist_table = None
        self._zobrist_side = None
        self._deadline = None
        self._dir_ranges_cache = {}
        self._utt_counter = 0
        # Win-shortcut during search: a huge win for real play (prunes dead
        # subtrees and values forced wins correctly), but it must be OFF in
        # AUTOGRADER mode since the reference leaf counts assume every node
        # is expanded to the literal depth limit with no early termination.
        self._check_wins = True

    def introduce(self):
        name_line = ("My name is " + self.long_name + " (call me " +
                     self.nickname + ").")
        author_line = ("I was built by " + AUTHORS + " (" +
                       ", ".join(STUDENT_IDS) + ").")
        style_line = ("I search with iterative-deepening alpha-beta pruning "
                      "and a line-window heuristic. Good luck.")
        lines = [name_line, author_line, style_line]
        if self.twin:
            lines.append("I'm the twin instance -- same brain, fresh state.")
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
        self._utt_counter = 0
        self._dir_ranges_cache = {}
        self._init_zobrist(game_type.n, game_type.m)

        # utterances_matter == False means no LLM/API usage is allowed; this
        # agent never imports one, so there is nothing further to disable.
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
        self._check_wins = not autograder_mode
        self._use_zobrist = bool(use_zobrist_hashing)
        self._tt = {} if self._use_zobrist else None

        self.alpha_beta_cutoffs_this_turn = 0
        self.num_static_evals_this_turn = 0
        self.zobrist_table_num_entries_this_turn = 0 if self._use_zobrist else -1
        self.zobrist_table_num_hits_this_turn = 0 if self._use_zobrist else -1
        self.zobrist_num_useful_hits_for_minimax = 0 if self._use_zobrist else -1
        self.zobrist_num_useful_hits_for_ordering = 0 if self._use_zobrist else -1

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

        utterance = self._make_utterance(score)

        if autograder_mode:
            stats = {
                'alpha_beta_cutoffs_this_turn': self.alpha_beta_cutoffs_this_turn,
                'num_static_evals_this_turn': self.num_static_evals_this_turn,
                'zobrist_table_num_entries_this_turn': self.zobrist_table_num_entries_this_turn,
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
        depth = 1
        while True:
            try:
                alpha = float('-inf') if use_alpha_beta else None
                beta = float('inf') if use_alpha_beta else None
                score, move, new_state = self.minimax(
                    state, depth, pruning=use_alpha_beta, alpha=alpha, beta=beta)
            except _SearchTimeout:
                break
            if move is not None:
                best_move, best_state, best_score = move, new_state, score
            if abs(best_score) >= WIN_SCORE:
                break  # Found a forced win/loss; deeper search won't help.
            if max_ply is not None and depth >= max_ply:
                break
            depth += 1
            if self._deadline is not None and time.time() >= self._deadline:
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
            return [self._eval_fn(state), None, state]

        tt_key = None
        hint_move = None
        if self._use_zobrist:
            if self._tt is None:
                self._tt = {}
            tt_key = self._zobrist_hash(state)
            entry = self._tt.get(tt_key)
            if entry is not None:
                e_depth, e_val, e_move, e_state = entry
                self.zobrist_table_num_hits_this_turn += 1
                hint_move = e_move
                if e_depth >= depth_remaining:
                    if not pruning:
                        self.zobrist_num_useful_hits_for_minimax += 1
                        return [e_val, e_move, e_state]
                    else:
                        self.zobrist_num_useful_hits_for_ordering += 1
                else:
                    self.zobrist_num_useful_hits_for_ordering += 1

        moves = self._generate_moves(state)
        if not moves:
            return [0.0, None, state]

        if hint_move is not None:
            moves = self._reorder_with_hint(moves, hint_move)

        is_max = (state.whose_move == 'X')
        best_val = float('-inf') if is_max else float('inf')
        best_move = None
        best_state = None

        for move, new_state in moves:
            win_result = (winTesterForK(new_state, move, self._k)
                         if self._check_wins else "No win")
            if win_result != "No win":
                child_val = (WIN_SCORE + depth_remaining) if is_max else -(WIN_SCORE + depth_remaining)
            elif depth_remaining - 1 == 0:
                self.num_static_evals_this_turn += 1
                child_val = self._eval_fn(new_state)
            else:
                child_val = self.minimax(
                    new_state, depth_remaining - 1, pruning, alpha, beta)[0]

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
            if tt_key not in self._tt:
                self.zobrist_table_num_entries_this_turn += 1
            self._tt[tt_key] = (depth_remaining, best_val, best_move, best_state)

        return [best_val, best_move, best_state]

    def _reorder_with_hint(self, moves, hint_move):
        for idx, (move, _) in enumerate(moves):
            if move == hint_move:
                if idx != 0:
                    moves = [moves[idx]] + moves[:idx] + moves[idx + 1:]
                break
        return moves

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

    def _order_score(self, board, i, j, mover, opp, n, m, cn, cm):
        score = 0.0
        for di in range(-2, 3):
            for dj in range(-2, 3):
                if di == 0 and dj == 0:
                    continue
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < m:
                    c = board[ni][nj]
                    if c == ' ' or c == '-':
                        continue
                    dist = max(abs(di), abs(dj))
                    w = 1.0 / dist
                    score += (2.0 * w) if c == mover else (1.5 * w)
        score -= 0.05 * (abs(i - cn) + abs(j - cm))
        return score

    def _generate_moves_ordered(self, state):
        board = state.board
        n = len(board)
        m = len(board[0])
        mover = state.whose_move
        opp = 'O' if mover == 'X' else 'X'
        candidates = self._candidate_cells(board, n, m)
        cn = (n - 1) / 2.0
        cm = (m - 1) / 2.0
        scored = []
        for (i, j) in candidates:
            sc = self._order_score(board, i, j, mover, opp, n, m, cn, cm)
            scored.append((sc, i, j))
        scored.sort(key=lambda t: -t[0])
        return [((i, j), self._do_move(state, i, j)) for (sc, i, j) in scored]

    # ------------------------------------------------------------------
    # Zobrist hashing (optional transposition table)
    # ------------------------------------------------------------------
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
                        total += base ** x_count
                    elif o_count:
                        total -= base ** o_count

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
    # Utterances (no LLM / external API required)
    # ------------------------------------------------------------------
    OPENING_LINES = [
        "Claiming the center and the initiative.",
        "Opening moves set the tone.",
        "Let's see how you respond to this.",
    ]
    WINNING_LINES = [
        "I see the win from here.",
        "This line closes it out.",
        "Forced sequence -- and it ends well for me.",
    ]
    LOSING_LINES = [
        "Tough spot, but I'm not done yet.",
        "Not my favorite position. I'll make you work for it.",
    ]
    BUILDING_LINES = [
        "Building another threat.",
        "Stacking the odds in my favor.",
        "That opens up more lines for me.",
    ]
    BLOCKING_LINES = [
        "Not on my watch -- blocking that.",
        "I see what you're building. Denied.",
        "That line stops here.",
    ]
    NEUTRAL_LINES = [
        "A solid, quiet move.",
        "Keeping my options open.",
        "Patience. The board will tell me more soon.",
    ]

    def _make_utterance(self, score):
        if not self.utterances_matter:
            return "Noted."
        mine = self.playing if self.playing in ('X', 'O') else 'X'
        rel = score if mine == 'X' else -score
        if rel >= WIN_SCORE:
            bucket = self.WINNING_LINES
        elif rel <= -WIN_SCORE:
            bucket = self.LOSING_LINES
        elif rel > 40:
            bucket = self.BUILDING_LINES
        elif rel < -40:
            bucket = self.BLOCKING_LINES
        else:
            bucket = self.NEUTRAL_LINES
        line = bucket[self._utt_counter % len(bucket)]
        self._utt_counter += 1
        return line
