'''generate_llm_demo_transcript.py

Generates a demonstration transcript (same HTML/JSON recorders, same
auto-naming convention as a normal Game_Master_Offline.py run) of Kitti
playing Cassini against her actual twin, Bunni -- not a throwaway
scripted stand-in. Bunni plays for real (her own search, her own
defensive_bias, her own persona voice) on every turn; only her first two
utterances are overridden to literally ask the two mandatory Part II
trigger phrases ("Tell me how you did that" and "What's your take on the
game so far?"), early enough in the game that they are guaranteed to
reach Kitti before the game can end.

Not part of the graded submission; just a tool for generating a
transcript that exercises specific Part II features on demand.
'''

import Game_Master_Offline as gm
import reidunt_KInARow as kitti_module
from game_types import Cassini

TRIGGER_PHRASES = [
    "Tell me how you did that",
    "What's your take on the game so far?",
]


class ScriptedBunni(kitti_module.OurAgent):
    '''The real Bunni (twin=True): same search, same defensive bias, same
    persona voice. Only her first two utterances are overridden so the
    two mandatory trigger phrases are guaranteed to appear early in the
    game; every move she makes and every other line she says is her own,
    unscripted.'''

    def __init__(self):
        super().__init__(twin=True)

    def make_move(self, *args, **kwargs):
        result = super().make_move(*args, **kwargs)
        if self.move_number <= len(TRIGGER_PHRASES):
            result[1] = TRIGGER_PHRASES[self.move_number - 1]
        return result


gm.set_game(Cassini)

kitti = kitti_module.OurAgent()
bunni = ScriptedBunni()

gm.set_players(kitti, bunni)
gm.runGame()
