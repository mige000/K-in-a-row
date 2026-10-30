'''generate_final_transcript.py

Generates the final submission transcript: Kitti (our agent) vs. Smirk
(n1coleh_KInARow.py, another team's agent) on Cassini, using the real
Game Master machinery so the output file is named/formatted exactly as
it would be in a real match. n1coleh_KInARow.py is left completely
untouched -- it plays exactly as its author wrote it.

Not part of the graded submission; just the tool used to generate
Kitti-vs-Smirk-in-Cassini-round-1.html/.json/.pdf.
'''

import Game_Master_Offline as gm
import reidunt_KInARow as kitti_module
import n1coleh_KInARow as opponent_module
from game_types import Cassini

gm.set_game(Cassini)

kitti = kitti_module.OurAgent()
opponent = opponent_module.OurAgent()

gm.set_players(kitti, opponent)
gm.runGame()
