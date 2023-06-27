# Copyright 2022 Cartesi Pte. Ltd.
#
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy of the
# License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from os import environ
import logging
import requests

from Cryptodome.Hash import SHA512, SHA224
from enum import Enum
from itertools import zip_longest
import datetime

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = environ["ROLLUP_HTTP_SERVER_URL"]
logger.info(f"HTTP rollup_server url is {rollup_server}")


###
# Game Functions

# Timeout to claim victory if opponent doesn't send the reveal
TIMEOUT = 1200

# Phases
Phase = Enum('Phase', 'COMMIT REVEAL FINISH ABORT')

# Global games variable
games = {}


def handle_game_logic(sender, timestamp, data):
    if not data.get("opponent"):
        raise Exception("No opponent defined")

    # Get game id based on players' identification
    #  - only a single game per player pair
    game_id = get_game_id(sender, data["opponent"])

    # standard NOP message
    message = None

    game = get_game(sender, timestamp, data, game_id)

    # Game was just created
    if game["phase"] is None:
        # Set game phase
        game["phase"] = Phase.COMMIT.name

        # Set last interaction
        game["last_interaction"] = "CREATED"

        # Set notice message
        message = get_game_status_message(game_id)

    # Game is in commit phase
    elif game["phase"] == Phase.COMMIT.name:
        if not game[sender]["commit_ts"] and (data.get("commit") or data.get("action") ):
            if data.get("commit"):
                # add commit for the second player
                add_commit(sender, timestamp, data, game)
                game["last_interaction"] = "COMMIT ADDED"
            else:
                # try to add reveal
                add_reveal(sender, timestamp, data, game)
                game["last_interaction"] = "REVEAL ADDED"

            # Set game phase and notice message
            game["phase"] = Phase.REVEAL.name
            message = get_game_status_message(game_id)

        # cancel game if opponent hasn't sent any commits yet
        elif check_cancel_game(sender, data, game):
            # Set game phase and notice message
            game["phase"] = Phase.ABORT.name
            game["last_interaction"] = "CANCELED"
            message = get_game_status_message(game_id)

    elif game["phase"] == Phase.REVEAL.name:
        # Check if there's no reveal yet and, then receive the reveal message
        if not game[sender]["reveal_ts"] and data.get("action"):
            # add reveal
            add_reveal(sender, timestamp, data, game)

            # Add reveal if it matches the player's commit
            if not check_reveal(sender, game):
                # Reveal was not successful, finished game with the opponent as
                # winner and set game phase and notice message
                game["phase"] = Phase.FINISH.name
                game["last_interaction"] = "WRONG REVEAL ADDED"
                message = get_game_status_message(game_id)
                message = f"WINNER[wrong reveal victory]({get_player_display_id(data['opponent'])}) | {get_game_status_message(game_id)}"
            else:
                # Reveal was successful
                if game[data["opponent"]]["reveal_ts"]:
                    # All players sent the reveal, get winner and finish game,
                    # then set game phase and notice message
                    winner = get_winner(game)
                    game["phase"] = Phase.FINISH.name
                    game["last_interaction"] = "REVEAL ADDED"
                    message = f"WINNER[normal victory]({get_player_display_id(winner)}) | {get_game_status_message(game_id)}"
                else:
                    # Opponent still has to send his reveal, then set game
                    # phase and notice message
                    game["phase"] = Phase.REVEAL.name
                    game["last_interaction"] = "REVEAL ADDED"
                    message = get_game_status_message(game_id)

        # Check if sender claimed timeout, and if enough time has passed,
        # finish game with sender as winner
        elif check_timeout_game(sender, timestamp, data, game):
            # Set game phase and notice message
            game["phase"] = Phase.FINISH.name
            game["last_interaction"] = "TIMEOUT"
            message = f"WINNER[W.O. victory]({get_player_display_id(sender)}) | {get_game_status_message(game_id)}"

    else:
        raise Exception("Invalid game phase")

    if game["phase"] == Phase.FINISH.name or game["phase"] == Phase.ABORT.name:
        del games[game_id]

    if message is None:
        raise Exception(
            f"Invalid action of player {get_player_display_id(sender)} for game {game_id} in {game['phase']} phase")

    # Return notice message
    return message


# Create a message to display the status a given game
def get_game_status_message(game_id):
    message = f"Game({game_id})"
    if not games.get(game_id):
        return message
    game = games[game_id]

    message = f"{message} Phase({game['phase']}) Last({game['last_interaction']} - {get_pretty_timestamp(game['last_ts'])})"
    for player in game["players"]:
        message = f"{message} | {get_player_status(game,player)}"

    return message


def get_player_status(game,p): 
    player_data = f"Player({get_player_display_id(p)}) Parity({get_player_parity(game[p])})"
    player_status_messages = []
    player_ts = f""
    if game[p].get('commit'):
        player_status_messages.append(f"Commit({game[p].get('commit')})")
        player_ts = f" Ts({get_pretty_timestamp(game[p]['commit_ts'])})"
    if game[p].get('action'):
        player_status_messages.append(f"Action({game[p].get('action')})")
        player_ts = f" Ts({get_pretty_timestamp(game[p]['reveal_ts'])})"
    if game[p].get('nonce'):
        player_status_messages.append(f"Nonce({game[p].get('nonce')})")
    player_status = ', '.join(player_status_messages) if len(player_status_messages) > 0 else "No Commit"
    return f"{player_data}{player_ts}: {player_status}"


def get_player_display_id(player):
    return f"{player[0:6]}...{player[-4:]}"


def get_player_parity(player_info):
    return f"even" if player_info["parity"] == 0 else f"odd"


def get_pretty_timestamp(ts):
    return datetime.datetime.fromtimestamp(ts).isoformat() if ts else "-"


def get_game(sender, timestamp, data, game_id):
    game = None
    # Create and start game if it doesn't exist
    if not games.get(game_id):
        # create game
        game = new_game(sender, timestamp, data)

        # add game to global game list
        games[game_id] = game
    else:
        # Get game
        game = games[game_id]
    return game


# Get list of display messages from current games
def get_current_games_states():
    open_game_states = []
    for game_id in games.keys():
        open_game_states.append(get_game_status_message(game_id))
    return str(open_game_states)


# Create a new game structure
def new_game(sender, timestamp, data):
    if not data.get("opponent"):
        raise Exception("Cannot create game: no opponent defined")
    if data["opponent"].lower() == sender.lower():
        raise Exception(
            "Cannot create game: a player cannot play against themselves")
    if not data.get("commit"):
        raise Exception("Cannot create game: no commit defined")
    if not data.get("parity"):
        raise Exception("Cannot create game: no parity defined")
    return {
        "phase": None,
        "players": [sender, data["opponent"]],
        "last_ts": timestamp,
        "last_interaction": None,
        sender: {
            "commit": data["commit"],
            "parity": data["parity"],
            "commit_ts": timestamp,
            "action": None,
            "nonce": None,
            "reveal_ts": None,
        },
        data["opponent"]: {
            "commit": None,
            "parity": 1 - data["parity"],
            "commit_ts": None,
            "action": None,
            "nonce": None,
            "reveal_ts": None,
        }
    }


# Add a commit to the game
def add_commit(sender, timestamp, data, game):
    if not data.get("commit"):
        raise Exception("Cannot add commit: no commit defined")
    game[sender]["commit"] = data["commit"]
    game[sender]["commit_ts"] = timestamp
    game["last_ts"] = timestamp


# Check and add a reveal to the game. If the reveal validates the commit,
# return true, otherwise return false
def add_reveal(sender, timestamp, data, game):
    if not data.get("action"):
        raise Exception("Cannot add reveal: no action defined")
    game[sender]["action"] = data["action"]
    if data.get("nonce"):
        game[sender]["nonce"] = data["nonce"]
    game[sender]["reveal_ts"] = timestamp
    game["last_ts"] = timestamp

def check_reveal(sender, game):
    action_nonce = f"{game[sender]['action']}-{game[sender]['nonce']}"

    h = SHA512.new(truncate="256", data=str2bytes(action_nonce))

    if h.hexdigest() != game[sender]["commit"]:
        return False
    return True


# Check if sender can cancel game
def check_cancel_game(sender, data, game):
    if not data.get("cancel"):
        return False
    if game['phase'] != Phase.COMMIT.name:
        raise Exception(f"Cannot cancel game in {game['phase']} phase")
    # check if it was the opponent who started the game
    if not game[sender]['commit_ts'] or game[data["opponent"]]["commit_ts"]:
        raise Exception(f"Cannot cancel game")
    return True


# Check if sender can claim timeout
def check_timeout_game(sender, timestamp, data, game):
    if not data.get("timeout"):
        return False
    if game["phase"] != Phase.REVEAL.name:
        raise Exception(f"Cannot claim timeout game in {game['phase']} phase")
    if not game[sender]["reveal_ts"]:
        raise Exception(f"Cannot claim timeout if didn't send reveal")
    if game[data["opponent"]]["reveal_ts"]:
        raise Exception(f"Cannot claim timeout if opponent sent reveal")
    # check timeout
    if timestamp < game["last_ts"] + TIMEOUT:
        raise Exception(
            f"Cannot claim timeout yet. Must wait until {datetime.datetime.fromtimestamp(game['last_ts'] + TIMEOUT).isoformat()}")
    return True


# get winner on a normal odds and evens game
def get_winner(game):
    parities = {}
    players_sum = 0
    for player in game["players"]:
        parities[game[player]["parity"]] = player
        players_sum = players_sum + game[player]["action"]
    return parities[players_sum % 2]


# get parity bit based on odd or even string option
def get_parity_bit(parity):
    if parity in ["o", "odd", "odds"]:
        return 1
    elif parity in ["e", "even", "evens"]:
        return 0
    else:
        raise Exception("Invalid parity")


# get game id from players' identification
def get_game_id(player_a, player_b):
    player_list = sorted([player_a.lower(), player_b.lower()])
    players_str = f"{player_list[0]}-{player_list[1]}"
    return SHA224.new(data=str2bytes(players_str)).hexdigest()[:10]


# process payload received by cartesi rollups to a key-value dict
def process_payload_to_dict(payload):
    payload_dict = {}
    for pair in zip_longest(*[iter(payload.split())] * 2):
        key = pair[0].lower()
        value = pair[1]
        if key in ["opponent", "o"]:
            if value[:2] != "0x" or len(value) != 42:
                raise Exception("Wrong opponent format")
            payload_dict["opponent"] = value.lower()
        elif key in ["parity", "p"]:
            payload_dict["parity"] = get_parity_bit(value.lower())
        elif key in ["commit", "commitment", "c"]:
            if len(value) != 64:
                raise Exception("Wrong commit format")
            payload_dict["commit"] = value.lower()
        elif key in ["action", "a"]:
            payload_dict["action"] = int(value)
        elif key in ["nonce", "n"]:
            payload_dict["nonce"] = value
        elif key in ["cancel", "x", "abort"]:
            payload_dict["cancel"] = True
        elif key in ["timeout", "t"]:
            payload_dict["timeout"] = True
        else:
            logger.warning(f"Invalid option {key}")
    return payload_dict


###
# Aux Functions

def hex2bytes(hex):
    return bytes.fromhex(hex[2:])


def hex2str(hex):
    return hex2bytes(hex).decode("utf-8")


def str2bytes(strtxt):
    return strtxt.encode("utf-8")


def str2hex(strtxt):
    return to_hex(str2bytes(strtxt))


def to_hex(value):
    return "0x" + value.hex()


def send_notice(notice):
    send_post("notice", notice)


def send_report(report):
    send_post("report", report)


def send_post(endpoint, json_data):
    response = requests.post(rollup_server + f"/{endpoint}", json=json_data)
    logger.info(
        f"/{endpoint}: Received response status {response.status_code} body {response.content}")


###
# handlers

def handle_advance(data):
    logger.info(f"Received advance request data {data}")
    status = "accept"
    payload = None
    try:
        payload = hex2str(data["payload"])

        # get processed key-value dict with the options of odds and evens game
        payload_dict = process_payload_to_dict(payload)
        logger.info(f"Processed Payload {payload_dict}")

        # handle game logic and receive message with the game state
        msg = handle_game_logic(
            data["metadata"]["msg_sender"],
            data["metadata"]["timestamp"],
            payload_dict)
        logger.info(f"Message response {msg}")

        # send notice
        send_notice({"payload": str2hex(msg)})
    except Exception as e:
        status = "reject"
        logger.error(e)
        msg = f"Error: {e}"
        send_report({"payload": str2hex(msg)})
    return status


def handle_inspect(data):
    logger.info(f"Received inspect request data {data}")

    msg = get_current_games_states()

    logger.info("Adding report")
    send_report({"payload": str2hex(msg)})
    return "accept"


handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}


###
# Main loop

finish = {"status": "accept"}
rollup_address = None

while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        data = rollup_request["data"]
        if "metadata" in data:
            metadata = data["metadata"]
            if metadata["epoch_index"] == 0 and metadata["input_index"] == 0:
                rollup_address = metadata["msg_sender"]
                logger.info(f"Captured rollup address: {rollup_address}")
                continue
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])
