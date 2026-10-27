'''generate_llm_demo_transcript.py

Generates a demonstration transcript (same HTML/JSON recorders, same
auto-naming convention as a normal Game_Master_Offline.py run) of Kitti
playing Tic-Tac-Toe against a scripted opponent that asks the two
mandatory Part II trigger phrases ("Tell me how you did that" and
"What's your take on the game so far?") early enough to be guaranteed to
land before the game can end.

Temporarily raises Kitti's LLM call timeout (normally 2.5s, safe for
competitive play) ONLY on this one agent instance, so genuine
Gemini-generated lines make it into the transcript even while Google's
live service is responding slowly. This does not change the committed
default in reidunt_KInARow.py.

Not part of the graded submission.
'''

import Game_Master_Offline as gm
import ScriptedChatOpponent
import reidunt_KInARow as kitti_module
from game_types import TTT

gm.set_game(TTT)

kitti = kitti_module.OurAgent()
kitti.LLM_CALL_TIMEOUT_SECONDS = 150  # instance override; see module docstring.
opponent = ScriptedChatOpponent.OurAgent()

gm.set_players(kitti, opponent)
gm.runGame()
