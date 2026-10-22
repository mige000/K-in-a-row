'''gameToHTML.py

Records a game as an HTML page, with a picture of the board after every move
and the agents' utterances alongside.

This is one of the "recorders" that Game_Master_Offline.py can write a game to;
see gameToJSON.py for the other one.  A recorder just receives the events of a
game as they happen and writes them out however it likes.  You should not need
to modify this file to do the assignment.
'''

import re


def clean(name):
    '''Make a nickname safe to put in a filename.'''
    new_name = re.sub(' ', '-', name)
    new_name = re.sub('[^a-zA-Z10-9\\-]', '', new_name)
    return new_name


TOKEN_IMAGES = {'X': 'X32.png', 'O': 'O32.png',
                ' ': 'gray32.png', '-': 'black32.png'}


class HTMLRecorder:
    '''Writes <X>-vs-<O>-in-<game>-round-<n>.html in the working directory.'''

    def __init__(self):
        self.f = None

    def start(self, game_type, x_player, o_player, round=1):
        fn = (clean(x_player.nickname) + '-vs-' + clean(o_player.nickname)
              + '-in-' + clean(game_type.short_name) + '-round-' + str(round)
              + '.html')
        try:
            self.f = open(fn, 'w')
        except Exception as e:
            print("Could not open " + fn + " for the game's HTML page: " + str(e))
            return
        self.filename = fn
        self.f.write('<html><head><title>K-in-a-Row game</title></head>\n<body>\n')
        self.f.write('<h1>Game Report: ' + x_player.nickname + ' versus '
                     + o_player.nickname + ' in ' + game_type.short_name
                     + ', round ' + str(round) + '</h1>\n')

    def commentary(self, text):
        pass          # console narration is not part of the HTML report

    def introduction(self, side, player, text):
        if not self.f: return
        self.f.write('<h2>' + player.nickname + ' (playing ' + side
                     + ') says: ' + text + '</h2>\n')

    def state(self, state, finished=False):
        if not self.f: return
        html = '<table>\n'
        for row in state.board:
            html += '<tr>'
            for token in row:
                html += ('<td><img src=' + TOKEN_IMAGES.get(token, 'gray32.png')
                         + '></td>')
            html += '</tr>\n'
        html += '</table><br>\n'
        if not finished:
            html += '<h3>' + state.whose_move + ' to move.</h3>\n'
        self.f.write(html)

    def move(self, side, player, move, state, utterance, stats=None):
        if not self.f: return
        self.f.write('<h2>Move is by ' + side + ' to ' + str(move) + '</h2>\n')
        self.f.write('<h2>' + player.nickname + ' says: ' + utterance + '</h2>\n')

    def result(self, text, winner=None):
        if not self.f: return
        self.f.write('<h2>' + text + '</h2>\n')

    def end(self):
        if not self.f: return
        self.f.write('</body></html>\n')
        self.f.close()
        self.f = None
