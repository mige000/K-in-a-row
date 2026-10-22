'''gameToJSON.py

Records a game as a JSON file that can be replayed later -- in particular by
the browser-based game master, which can play the game back move by move and
speak the agents' utterances aloud.

Why a separate format from the HTML report: a replay must reproduce exactly
what happened, without re-running anybody's agent.  So the transcript carries
the board after every move rather than just the moves, and it carries enough
about the game type that a replayer does not have to have a matching
game_types.py.  Nothing in a transcript needs the agents' code, which is also
what makes it safe to publish a replay of an agent you would not publish.

This is one of the "recorders" that Game_Master_Offline.py can write a game to;
see gameToHTML.py for the other one.  You should not need to modify this file
to do the assignment.
'''

import json
import re

FORMAT = 'kiar-transcript/1'

# Statistics an agent may keep on itself.  These are the attribute names
# declared in agent_base.KAgent, so any agent has them; an agent that does not
# measure one leaves it at -1.
STAT_ATTRS = [
    'alpha_beta_cutoffs_this_turn',
    'num_static_evals_this_turn',
    'zobrist_table_num_entries_this_turn',
    'zobrist_table_num_hits_this_turn',
]


def clean(name):
    new_name = re.sub(' ', '-', name)
    new_name = re.sub('[^a-zA-Z10-9\\-]', '', new_name)
    return new_name


def player_info(player):
    '''What a replayer needs to know about an agent: who it is and how it
    should sound.  Voice preferences are optional and agent-defined.'''
    info = {
        'nickname':  getattr(player, 'nickname', '?'),
        'long_name': getattr(player, 'long_name', '?'),
        'persona':   getattr(player, 'persona', ''),
    }
    for attr in ('voice_prefs', 'voice_info'):
        value = getattr(player, attr, None)
        if isinstance(value, dict):
            info[attr] = dict(value)
    return info


class JSONRecorder:
    '''Writes <X>-vs-<O>-in-<game>-round-<n>.json in the working directory.'''

    def __init__(self):
        self.data = None
        self.filename = None

    def start(self, game_type, x_player, o_player, round=1):
        self.filename = (clean(x_player.nickname) + '-vs-' + clean(o_player.nickname)
                         + '-in-' + clean(game_type.short_name)
                         + '-round-' + str(round) + '.json')
        initial = game_type.initial_state
        self.data = {
            'format': FORMAT,
            'round': round,
            'game': {
                'long_name':     game_type.long_name,
                'short_name':    game_type.short_name,
                'k':             game_type.k,
                'n':             game_type.n,
                'm':             game_type.m,
                'turn_limit':    game_type.turn_limit,
                'initial_board': [row[:] for row in initial.board],
                'first_move':    initial.whose_move,
            },
            'players': {'X': player_info(x_player), 'O': player_info(o_player)},
            'events': [],
        }

    def commentary(self, text):
        if self.data is None: return
        self.data['events'].append({'type': 'gm', 'text': text})

    def introduction(self, side, player, text):
        if self.data is None: return
        self.data['events'].append({'type': 'intro', 'side': side,
                                    'nickname': getattr(player, 'nickname', '?'),
                                    'text': text})

    def state(self, state, finished=False):
        pass          # boards are carried on the move events instead

    def move(self, side, player, move, state, utterance, stats=None):
        if self.data is None: return
        event = {
            'type': 'move',
            'side': side,
            'nickname': getattr(player, 'nickname', '?'),
            'move': list(move),
            'utterance': utterance,
            'board': [row[:] for row in state.board],
            'whose_move': state.whose_move,
        }
        if stats:
            event['stats'] = stats
        self.data['events'].append(event)

    def result(self, text, winner=None):
        if self.data is None: return
        self.data['events'].append({'type': 'result', 'text': text,
                                    'winner': winner})

    def end(self):
        if self.data is None: return
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=1)
        except Exception as e:
            print('Could not write ' + str(self.filename) + ': ' + str(e))
        self.data = None


def collect_stats(player, seconds, extra=None):
    '''Gather what can be known about the work an agent just did.

    `seconds` is measured by the game master, so it is always available.  The
    counters are read off the agent, which is where agent_base tells agents to
    keep them; an agent that does not measure one leaves it at -1.  `extra` is
    the statistics dictionary an agent may return as a third element of its
    move, which takes precedence when present.
    '''
    stats = {'seconds': round(seconds, 4)}
    for attr in STAT_ATTRS:
        value = getattr(player, attr, -1)
        if isinstance(value, int) and value >= 0:
            stats[attr] = value
    if isinstance(extra, dict):
        for key, value in extra.items():
            if isinstance(value, int) and value >= 0:
                stats[key] = value
    return stats
