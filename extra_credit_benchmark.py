'''extra_credit_benchmark.py

Standalone measurement script for the Part I extra credit options:

  I-A: child ordering by static evaluation
  I-B: Zobrist hashing (and using cached values for ordering too)

Runs a fixed-depth (4-ply) alpha-beta search from a Cassini mid-game-ish
position (the official initial state, which already has two handicap O's
on the board, so the candidate-restricted move generator has something to
work with from move 1) under four configurations:

  1. baseline   -- no child ordering, no Zobrist table
  2. ordering   -- static-eval child ordering, no Zobrist table
  3. zobrist    -- Zobrist table, no explicit child ordering
  4. both       -- static-eval ordering + Zobrist (hits reused for ordering)

and prints alpha-beta cutoffs, static-eval call counts, Zobrist read/write/
hit counts, and wall-clock time for each, so the numbers can be copied
straight into Section 11 of the Learning Diary.

Run with:  python3 extra_credit_benchmark.py
'''

import time
import yourID_KInARow as agent_module
import game_types
from agent_base import KAgent

DEPTH = 4
TEST_STATE = game_types.State(old=game_types.Cassini.initial_state)


def run(label, use_eval_ordering, use_zobrist):
    a = agent_module.OurAgent()
    a.set_playing_mode(KAgent.AUTOGRADER)  # fixed exact-depth search, no time cutoff
    a.prepare(game_types.Cassini, 'X', 'Benchmark')

    t0 = time.time()
    response = a.make_move(
        TEST_STATE, "go", use_alpha_beta=True,
        use_zobrist_hashing=use_zobrist, max_ply=DEPTH)
    # The AUTOGRADER-mode move-ordering switches (candidate restriction,
    # eval ordering) are forced off by make_move's autograder branch, so
    # flip them back on by hand for this experiment -- we want the exact
    # fixed-depth, no-timeout search behavior of AUTOGRADER mode, just
    # with the move-ordering feature under test.
    a._use_candidate_restriction = True
    a._use_eval_ordering = use_eval_ordering
    a._check_wins = True
    a.alpha_beta_cutoffs_this_turn = 0
    a.num_static_evals_this_turn = 0
    a.num_leaf_evals_this_turn = 0
    a.num_ordering_evals_this_turn = 0
    a.num_nodes_visited_this_turn = 0
    a.zobrist_table_num_entries_this_turn = 0 if use_zobrist else -1
    a.zobrist_table_num_reads_this_turn = 0 if use_zobrist else -1
    a.zobrist_table_num_hits_this_turn = 0 if use_zobrist else -1
    a.zobrist_num_useful_hits_for_minimax = 0 if use_zobrist else -1
    a.zobrist_num_useful_hits_for_ordering = 0 if use_zobrist else -1
    a._tt = {} if use_zobrist else None

    t0 = time.time()
    score, move, new_state = a.minimax(
        TEST_STATE, DEPTH, pruning=True, alpha=float('-inf'), beta=float('inf'))
    elapsed = time.time() - t0

    nodes = a.num_nodes_visited_this_turn
    cutoff_rate = (100.0 * a.alpha_beta_cutoffs_this_turn / nodes) if nodes else 0.0
    print("{:10s} move={!s:8s} nodes={:6d} cutoffs={:5d} ({:5.1f}%) leaf_evals={:6d} "
          "ord_evals={:6d}  tt_w={:4}  tt_r={:4}  tt_hit={:4}  time={:.4f}s".format(
              label, move, nodes,
              a.alpha_beta_cutoffs_this_turn, cutoff_rate,
              a.num_leaf_evals_this_turn,
              a.num_ordering_evals_this_turn,
              a.zobrist_table_num_entries_this_turn,
              a.zobrist_table_num_reads_this_turn,
              a.zobrist_table_num_hits_this_turn,
              elapsed))


if __name__ == "__main__":
    print("Fixed-depth ({} ply) alpha-beta search from the Cassini initial "
          "state.\n".format(DEPTH))
    run("baseline", use_eval_ordering=False, use_zobrist=False)
    run("ordering", use_eval_ordering=True,  use_zobrist=False)
    run("zobrist",  use_eval_ordering=False, use_zobrist=True)
    run("both",     use_eval_ordering=True,  use_zobrist=True)
