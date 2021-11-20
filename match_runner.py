import random
from dataclasses import dataclass
from typing import Dict, Optional, List

from rlbot.matchconfig.loadout_config import LoadoutConfig
from rlbot.matchconfig.match_config import PlayerConfig, MatchConfig, MutatorConfig, ScriptConfig
from rlbot.parsing.incrementing_integer import IncrementingInteger
from rlbot.setup_manager import SetupManager, setup_manager_context

STANDARD_MAPS = [
    "DFHStadium",
    "Mannfield",
    "ChampionsField",
    "UrbanCentral",
    "BeckwithPark",
    "UtopiaColiseum",
    "Wasteland",
    "NeoTokyo",
    "AquaDome",
    "StarbaseArc",
    "Farmstead",
    "SaltyShores",
    "DFHStadium_Stormy",
    "DFHStadium_Day",
    "Mannfield_Stormy",
    "Mannfield_Night",
    "ChampionsField_Day",
    "BeckwithPark_Stormy",
    "BeckwithPark_Midnight",
    "UrbanCentral_Night",
    "UrbanCentral_Dawn",
    "UtopiaColiseum_Dusk",
    "DFHStadium_Snowy",
    "Mannfield_Snowy",
    "UtopiaColiseum_Snowy",
    "ForbiddenTemple",
    "RivalsArena",
    "Farmstead_Night",
    "SaltyShores_Night",
    "NeonFields",
    "DFHStadium_Circuit",
    "DeadeyeCanyon",
]


def get_random_standard_map() -> str:
    return random.choice(STANDARD_MAPS)


sm: Optional[SetupManager] = None


def get_fresh_setup_manager():
    global sm
    if sm is not None:
        try:
            sm.shut_down()
        except Exception as e:
            print(e)
    sm = SetupManager()
    return sm


def run_match(bot_configs: List[PlayerConfig]):
    match_config = MatchConfig()
    match_config.game_mode = 'Soccer'
    match_config.game_map = get_random_standard_map()
    match_config.enable_state_setting = True

    match_config.player_configs = bot_configs
    match_config.mutators = MutatorConfig()
    match_config.mutators.match_length = 'Unlimited'

    sm = get_fresh_setup_manager()
    sm.early_start_seconds = 5
    sm.connect_to_game()
    sm.load_match_config(match_config)
    sm.launch_early_start_bot_processes()
    sm.start_match()
    sm.launch_bot_processes()
    sm.infinite_loop()
