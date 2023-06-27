# Odds and evens Game DApp

```
Cartesi Rollups version: 0.8.x
```

This example shows how to use the Commit-Reveal logic to implement an [Odds and evens game](https://en.wikipedia.org/wiki/Odds_and_evens_(hand_game)).
Such approach may be replicated for any other game where "simultaneous" or secret information is exchanged.

In the [Commit-Reveal scheme](https://en.wikipedia.org/wiki/Commitment_scheme), each player submits an "action commitment" either by hashing the action with a random number or encrypting the message.
After all players have sent their commitments, they reveal their actions by providing their action accompanied by the random number or encryption key previously used.

In this scheme, players cannot deny the actions they have commited to, and they cannot reveal their actions before the other players have commited their own actions.

This scheme has two potential cases that players may misbehave:

- a player fails to present enough information to reveal their action; or
- a player don't send his reveal message.

The DApp back-end is written in Python.

Known limitations of this implementation:

- A player can have only one game in progress with another player
- Commitments are done by SHA512/256 (SHA512 with 256 truncation) to avoid length extension attacks

DISCLAIMERS

This is not a final product and should not be used as one.

## Game message flow

A regular game may be represented by the following message flow:

1. First player commits: `opponent [second player pk] parity [odds or evens] commit [sha512/256 of chosen number-nonce]`
2. Second player commits: `opponent [first player pk] commit [sha512/256 of chosen number-nonce]`
3. First player reveals: `opponent [second player pk] action [chosen number] nonce [nonce]`
4. Second player reveals: `opponent [first player pk] action [chosen number] nonce [nonce]`

An alternative game flow can skip the second player commitment, as it not necessary to hide the information:

1. First player commits: `opponent [second player pk] parity [odds or evens] commit [sha512/256 of chosen number-nonce]`
2. Second player reveals: `opponent [first player pk] action [chosen number]`
3. First player reveals: `opponent [second player pk] action [chosen number] nonce [nonce]`

Alternative messages include:

- First player cancels match: `opponent [second player pk] cancel`
- First or second player aborts the match because the other player is not answering: `opponent [opponent player pk] timeout`

All accepted fields may be found in the table below:

| Field | Description | Usage constraints |
|---|---|---|
| `opponent (or o)` | Opposing player address | Mandatory for all messages |
| `parity (or p)` | Parity chosen (_odd_ or _even_) by th first player | Only for the first player commitment |
| `commit (or c)`  | Commitment of the player action given by the sha512/256 hash of the chosen pair _number-nonce_ | For the first and second player commitments |
| `action (or a)`  | Chosen number by either player | For the first and second player reveals |
| `nonce (or n)`  | Random number generated to avoid guessing the action | For the first and second player reveals |
| `cancel (or x)`  | Abort match before the other player commits their action | Only for the first player before the second player commits. It has no effect otherwise |
| `timeout (or t)` | Claim timeout when one player had already sent their reveal but the other player hasn't after a specified period of time | For the first and second players after their own reveals. It has no effect otherwise |

## Requirements

Please refer to the [rollups-examples requirements](https://github.com/cartesi/rollups-examples/tree/main/README.md#requirements).

## Building

To build the application, run the following command:

```shell
docker buildx bake -f docker-bake.hcl -f docker-bake.override.hcl --load
```

## Running

To start the application, execute the following command:

```shell
docker compose -f docker-compose.yml -f docker-compose.override.yml up
```

The application can afterwards be shut down with the following command:

```shell
docker compose -f docker-compose.yml -f docker-compose.override.yml down -v
```

## Interacting with the application

In this section we present a way to interact with the application using Linux command line tools such as `shasum` to generate the commitment hash. Optionally, you could use a online tool such as [SHA512_256](https://emn178.github.io/online-tools/sha512_256.html).

You can use the [frontend-console](https://github.com/cartesi/rollups-examples/tree/v0.14.0/frontend-console) application to interact with the DApp.
Ensure that the [application has already been built](https://github.com/cartesi/rollups-examples/tree/v0.14.0/frontend-console/README.md#building) before using it.

First, go to a separate terminal window and switch to the `frontend-console` directory:

```shell
cd frontend-console
mkdir -p odds-and-evens-data
```

Add hardhat wallet information:

```shell
echo "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266" > odds-and-evens-data/player1
echo "0x70997970C51812dc3A010C7d01b50e0d17dc79C8" > odds-and-evens-data/player2
```

Then, create the commitment for the first player as follows:

```shell
echo "$RANDOM" > odds-and-evens-data/player1-nonce
echo "5" > odds-and-evens-data/player1-action
```

After that, send the first player commitment:

```shell
yarn start input send --accountIndex 0 --payload "opponent $(cat odds-and-evens-data/player2) parity odd commit $(echo -n "$(cat odds-and-evens-data/player1-action)-$(cat odds-and-evens-data/player1-nonce)" | shasum -a 512256 | head -c 64)"
```

Do the same For the second player:

```shell
echo "$RANDOM" > odds-and-evens-data/player2-nonce
echo "8" > odds-and-evens-data/player2-action
yarn start input send --accountIndex 1 --payload "o $(cat odds-and-evens-data/player1) c $(echo -n "$(cat odds-and-evens-data/player2-action)-$(cat odds-and-evens-data/player2-nonce)" | shasum -a 512256 | head -c 64)"
```

After the commitment, send the reveal for the first player:

```shell
yarn start input send --accountIndex 0 --payload "opponent $(cat odds-and-evens-data/player2) action $(cat odds-and-evens-data/player1-action) nonce $(cat odds-and-evens-data/player1-nonce)"
```

And the reveal for the second player:

```shell
yarn start input send --accountIndex 1 --payload "o $(cat odds-and-evens-data/player1) a $(cat odds-and-evens-data/player2-action) n $(cat odds-and-evens-data/player2-nonce)"
```

In order to verify the notices generated by all inputs, run the command:

```shell
yarn start notice list
```

The response should look like this:

```json
[
    {"id":"1","epoch":0,"input":1,"notice":0,"payload":"CREATED: e7fe733917 WAITING_COMMIT 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266 (Yes - 2023-02-15T20:48:50) 0x70997970c51812dc3a010c7d01b50e0d17dc79c8 (No - Never)"},
    {"id":"2","epoch":0,"input":2,"notice":0,"payload":"COMMIT ADDED: e7fe733917 WAITING_REVEAL 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266 (No - Never) 0x70997970c51812dc3a010c7d01b50e0d17dc79c8 (No - Never)"},
    {"id":"3","epoch":0,"input":3,"notice":0,"payload":"REVEAL ADDED: e7fe733917 WAITING_REVEAL 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266 (Yes - 2023-02-15T20:49:10) 0x70997970c51812dc3a010c7d01b50e0d17dc79c8 (No - Never)"},
    {"id":"4","epoch":0,"input":4,"notice":0,"payload":"WINNER 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266 - REVEAL ADDED (normal victory): e7fe733917 FINISHED 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266 (Yes - 2023-02-15T20:49:10) 0x70997970c51812dc3a010c7d01b50e0d17dc79c8 (Yes - 2023-02-15T20:49:20)"}
]
```

## Running the back-end in host mode

When developing an application, it is often important to easily test and debug it. For that matter, it is possible to run the Cartesi Rollups environment in [host mode](https://github.com/cartesi/rollups-examples/tree/v0.14.0#host-mode), so that the DApp's back-end can be executed directly on the host machine, allowing it to be debugged using regular development tools such as an IDE.

To start the application, execute the following command:
```shell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose-host.yml up
```

The application can afterwards be shut down with the following command:
```shell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose-host.yml down -v
```

This DApp's back-end is written in Python, so to run it in your machine you need to have `python3` installed.

In order to start the back-end, run the following commands in a dedicated terminal:

```shell
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" python3 odds-and-evens.py
```

The final command will effectively run the back-end and send corresponding outputs to port `5004`.
It can optionally be configured in an IDE to allow interactive debugging using features like breakpoints.

You can also use a tool like [entr](https://eradman.com/entrproject/) to restart the back-end automatically when the code changes. For example:

```shell
ls *.py | ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" entr -r python3 odds-and-evens.py
```

After the back-end successfully starts, it should print an output like the following:

```log
INFO:__main__:HTTP rollup_server url is http://127.0.0.1:5004
INFO:__main__:Sending finish
```

After that, you can interact with the application normally [as explained above](#interacting-with-the-application).
