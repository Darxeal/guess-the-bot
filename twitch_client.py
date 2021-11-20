import csv
import random
import string
import json
import time
from dataclasses import dataclass
from threading import Thread, Timer
from typing import List, Dict, Set, Optional

from rlbot.matchconfig.loadout_config import LoadoutConfig
from rlbot.matchconfig.match_config import PlayerConfig
from rlbot.parsing.bot_config_bundle import BotConfigBundle
from rlbot.parsing.directory_scanner import scan_directory_for_bot_configs
from twitchio.ext import commands
from twitchio import Context
from twitchio.ext.commands.core import Command

from match_runner import run_match

BOTS_PER_TEAM = 3


@dataclass
class MysteryBot:
    name: str
    number: int
    actual_name: str
    team: int


class TwitchBot(commands.Bot):
    def __init__(self):
        with open("oauth.txt") as file:
            oauth = file.readline()
        super().__init__(irc_token=oauth, nick='Darxeal', prefix='!', initial_channels=['darxeal'])

        self.active_thread: Optional[Thread] = None
        self.bot_bundles: List[BotConfigBundle] = []
        self.items: Dict[str, List[int]] = {}
        self.load_items()

        self.votes_per_author: Set[(str, int)] = set()
        self.votes_by_bot: Dict[(str, int), str] = {}
        self.mysteries: Dict[str, MysteryBot] = {}

        self.scores: Dict[str, int] = {}

        self.ignoring_guesses = False

    async def event_ready(self):
        print(f'Ready | {self.nick}')
        self.start_round()

    @commands.command(name='skip')
    async def skip(self, ctx: Context):
        if ctx.author.is_mod:
            mystery_bot_names = ", ".join(bot.actual_name for bot in self.mysteries.values())
            await ctx.send(f"@{ctx.author.display_name} ⚠️ Skipping match. Mystery bots were: {mystery_bot_names}.")
            self.start_round()
        else:
            await ctx.send(f"@{ctx.author.display_name} ⚠️ You don't have permissions for this command.")

    @commands.command(name='guess')
    async def guess(self, ctx: Context, identifier: str, number: int):
        identifier = identifier.upper()
        vote = identifier, number
        name = ctx.author.display_name

        if name not in self.scores:
            self.scores[name] = 0

        if identifier not in self.mysteries:
            return

        if self.ignoring_guesses:
            return await ctx.send(f"@{name} ⚠️ Ignoring guess because round has ended.")

        bot = self.mysteries[identifier]
        if self.is_mystery_bot_guessed(identifier):
            return await ctx.send(f"@{name} ⚠️ This mystery bot has been guessed already.")

        if (name, identifier) in self.votes_per_author:
            return await ctx.send(f"@{name} ⚠️ You have already voted for {bot.name}.")

        if vote in self.votes_by_bot:
            return await ctx.send(f"@{name} ⚠️ This vote has already been tried.")

        if number == self.mysteries[identifier].number:
            await ctx.send(f"@{name} ✔️ Correct! {bot.name} is {bot.actual_name}")
            self.scores[name] += 1
        else:
            await ctx.send(f"@{name} ❌ Wrong guess!")

        self.votes_per_author.add((name, identifier))
        self.votes_by_bot[(identifier, number)] = name
        self.update_overlay()

        if all(self.is_mystery_bot_guessed(id) for id in self.mysteries):
            await ctx.send(f"✔️ All mystery bots guessed! Starting next match...")
            self.start_round()

    def is_mystery_bot_guessed(self, identifier: str) -> bool:
        return (identifier, self.mysteries[identifier].number) in self.votes_by_bot

    def make_bot_config(self, bundle: BotConfigBundle) -> PlayerConfig:
        bot = PlayerConfig()
        bot.config_path = bundle.config_path
        bot.bot = True
        bot.rlbot_controlled = True
        bot.loadout_config = LoadoutConfig()
        bot.loadout_config.car_id = random.choice(self.items["Body"])
        bot.loadout_config.decal_id = random.choice(self.items["Skin"])
        bot.loadout_config.boost_id = random.choice(self.items["Boost"])
        bot.loadout_config.wheels_id = random.choice(self.items["Wheels"])
        bot.loadout_config.trails_id = random.choice(self.items["SupersonicTrail"])
        bot.loadout_config.paint_finish_id = random.choice(self.items["PaintFinish"])
        bot.loadout_config.custom_finish_id = random.choice(self.items["PaintFinish"])
        bot.loadout_config.goal_explosion_id = random.choice(self.items["GoalExplosion"])
        bot.loadout_config.team_color_id = random.randint(0, 69)
        bot.loadout_config.custom_color_id = random.randint(0, 104)
        bot.loadout_config.paint_config.car_paint_id = random.randint(0, 13)
        bot.loadout_config.paint_config.decal_paint_id = random.randint(0, 13)
        bot.loadout_config.paint_config.boost_paint_id = random.randint(0, 13)
        bot.loadout_config.paint_config.wheels_paint_id = random.randint(0, 13)
        bot.loadout_config.paint_config.trails_paint_id = random.randint(0, 13)
        bot.loadout_config.paint_config.goal_explosion_paint_id = random.randint(0, 13)
        return bot

    def load_bots(self):
        self.bot_bundles = list(scan_directory_for_bot_configs("bots"))
        self.bot_bundles.sort(key=lambda bundle: bundle.name.lower())

    def load_items(self):
        with open("items.csv", "r") as file:
            for line in csv.reader(file):
                if line[1] not in self.items:
                    self.items[line[1]] = []
                self.items[line[1]].append(int(line[0]))

    @staticmethod
    def get_mystery_identifier(index: int) -> str:
        return string.ascii_uppercase[index]

    def start_match(self, bots: List[PlayerConfig]):
        if self.active_thread and self.active_thread.is_alive():
            self.active_thread.join(3.0)
        self.active_thread = Thread(target=run_match, args=(bots,), daemon=True)
        self.active_thread.start()

    def start_round(self):
        self.ignoring_guesses = True

        self.load_bots()
        numbers = list(range(len(self.bot_bundles)))
        selected_numbers = random.choices(numbers, k=BOTS_PER_TEAM * 2)
        selected_bot_bundles = [self.bot_bundles[n] for n in selected_numbers]
        print(", ".join(bot.name for bot in selected_bot_bundles))

        bots = [self.make_bot_config(bundle) for bundle in selected_bot_bundles]
        for i in range(len(bots)):
            bots[i].name = f'Mystery Bot {self.get_mystery_identifier(i)}'
            bots[i].team = 1 if i >= BOTS_PER_TEAM else 0

        self.mysteries.clear()
        for i in range(len(bots)):
            self.mysteries[self.get_mystery_identifier(i)] = MysteryBot(bots[i].name, selected_numbers[i], selected_bot_bundles[i].name, bots[i].team)
        self.votes_per_author.clear()
        self.votes_by_bot.clear()

        self.start_match(bots)

        def fn():
            self.ignoring_guesses = False
            self.update_overlay()
        Timer(5.0, fn).start()

    def vote_status(self, identifier: str, number: int) -> Optional[bool]:
        if (identifier, number) in self.votes_by_bot:
            return self.mysteries[identifier].number == number
        return None

    def update_overlay(self):
        overlay_data = {
            "votableBots": [{
                "name": self.bot_bundles[i].name,
                "command": i,
                "voteStatus": [self.vote_status(identifier, i) for identifier in self.mysteries.keys()]
            } for i in range(len(self.bot_bundles))],
            "mysteryBots": [{
                "identifier": identifier,
                "team": "orange" if bot.team == 1 else "blue",
                "actualName": bot.actual_name,
                "guessed": (identifier, bot.number) in self.votes_by_bot,
                "guessedBy": self.votes_by_bot[(identifier, bot.number)] if (identifier, bot.number) in self.votes_by_bot else None
            } for identifier, bot in self.mysteries.items()],
            "scoreboard": [{
                "name": name,
                "score": self.scores[name]
            } for name in sorted(self.scores, key=lambda name: self.scores[name], reverse=True)]
        }
        with open("overlay/data.json", "w") as file:
            json.dump(overlay_data, file, indent=4)


if __name__ == '__main__':
    bot = TwitchBot()
    bot.run()
