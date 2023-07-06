# Odds and evens Game DApp

```
Cartesi Rollups version: 0.9.x
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

- The DApp supports multiple concurrent games, but only one running game per player pair
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

You can use the Foundry's command-line tool for performing Ethereum RPC calls [cast](https://book.getfoundry.sh/cast/) to interact with the DApp. Also, you can use [curl](https://curl.se/) to get outputs, and [jq](https://jqlang.github.io/jq/) and [xxd](https://linux.die.net/man/1/xxd) to process them.

First, go to a separate terminal window and define some variables:

```shell
# Dapp address
INPUT_BOX_ADDRESS=0x5a723220579C0DCb8C9253E6b4c62e572E379945
# Dapp address
DAPP_ADDRESS=0x142105FC8dA71191b3a13C738Ba0cF4BC33325e2
# Add wallets information (local network deployment):
PLAYER1=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
PLAYER1_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
PLAYER2=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
PLAYER2_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
# Create the commitment for the first player as follows:
PLAYER1_ACTION=5
PLAYER1_NONCE=$RANDOM
# Do the same For the second player:
PLAYER2_ACTION=0
PLAYER2_NONCE=$RANDOM
```

After that, send the first player commitment:

```shell
cast send $INPUT_BOX_ADDRESS \
    "addInput(address,bytes)" $DAPP_ADDRESS \
    $(xxd -c10000 -p <<< "opponent $PLAYER2 parity odd commit $(echo -n "$PLAYER1_ACTION-$PLAYER1_NONCE" | shasum -a 512256 | head -c 64)" ) \
    --rpc-url http://localhost:8545 --from $PLAYER1 --private-key $PLAYER1_KEY
```

Then, send the second player commitment:

```shell
cast send $INPUT_BOX_ADDRESS \
    "addInput(address,bytes)" $DAPP_ADDRESS \
    $(xxd -c10000 -p <<< "o $PLAYER1 c $(echo -n "$PLAYER2_ACTION-$PLAYER2_NONCE" | shasum -a 512256 | head -c 64)" ) \
    --rpc-url http://localhost:8545 --from $PLAYER2 --private-key $PLAYER2_KEY
```

After the commitment, send the reveal for the first player:

```shell
cast send $INPUT_BOX_ADDRESS \
    "addInput(address,bytes)" $DAPP_ADDRESS \
    $(xxd -c10000 -p <<< "opponent $PLAYER2 action $PLAYER1_ACTION nonce $PLAYER1_NONCE" ) \
    --rpc-url http://localhost:8545 --from $PLAYER1 --private-key $PLAYER1_KEY
```

And the reveal for the second player:

```shell
cast send $INPUT_BOX_ADDRESS \
    "addInput(address,bytes)" $DAPP_ADDRESS \
    $(xxd -c10000 -p <<< "o $PLAYER1 a $PLAYER2_ACTION n $PLAYER2_NONCE" ) \
    --rpc-url http://localhost:8545 --from $PLAYER2 --private-key $PLAYER2_KEY
```

In order to verify the reports generated by all inputs, run the command:

```shell
curl -s -H 'Content-Type: application/json' -X POST http://localhost:4000/graphql -d '{"query": "query { reports { edges { node { payload }}}}"}' | jq -r '.data.reports.edges[] | .node.payload,"0a0a"' | xxd -r -p
```

The response should look like this:

```
Game(e7fe733917) | Phase(COMMIT) | Last(CREATED - 2023-07-05T08:46:36) | Player(0xf39f...2266) Parity(odd) Ts(2023-07-05T08:46:36): Commit(7a7fa724fdce5a7f3408b99a73f48e565ceef6695da33f7a8f46fa61ef843ec1) | Player(0x7099...79c8) Parity(even): No Commit

Game(e7fe733917) | Phase(REVEAL) | Last(COMMIT ADDED - 2023-07-05T08:46:46) | Player(0xf39f...2266) Parity(odd) Ts(2023-07-05T08:46:36): Commit(7a7fa724fdce5a7f3408b99a73f48e565ceef6695da33f7a8f46fa61ef843ec1) | Player(0x7099...79c8) Parity(even) Ts(2023-07-05T08:46:46): Commit(ed01f128bb4157ff084ec7b5390bef2cb1b085c619d1b83a176a8f1d01ed2e03)

Game(e7fe733917) | Phase(REVEAL) | Last(REVEAL ADDED - 2023-07-05T08:46:51) | Player(0xf39f...2266) Parity(odd) Ts(2023-07-05T08:46:51): Commit(7a7fa724fdce5a7f3408b99a73f48e565ceef6695da33f7a8f46fa61ef843ec1), Action(5), Nonce(31791) | Player(0x7099...79c8) Parity(even) Ts(2023-07-05T08:46:46): Commit(ed01f128bb4157ff084ec7b5390bef2cb1b085c619d1b83a176a8f1d01ed2e03)

WINNER[normal victory](0xf39f...2266) | Game(e7fe733917) | Phase(FINISH) | Last(REVEAL ADDED - 2023-07-05T08:47:01) | Player(0xf39f...2266) Parity(odd) Ts(2023-07-05T08:46:51): Commit(7a7fa724fdce5a7f3408b99a73f48e565ceef6695da33f7a8f46fa61ef843ec1), Action(5), Nonce(31791) | Player(0x7099...79c8) Parity(even) Ts(2023-07-05T08:47:01): Commit(ed01f128bb4157ff084ec7b5390bef2cb1b085c619d1b83a176a8f1d01ed2e03), Action(0), Nonce(7633)

```

The report message has the following format: 

```
WINNER[<type>](<winner>) | Game(<id>) | Phase(<phase>) | Last(<last action - ts>) | Player(<addressA>) Parity(<parityA>) Ts(<tsA>): Commit(<commitA>), Action(<actionA>), Nonce(<nonceA>) | Player(<addressB>) Parity(<parityB>) Ts(<tsB>): Commit(<commitB>), Action(<actionB>), Nonce(<nonceB>)
```

So the obtained messages are:

| Winner | Game | Phase | Last Action | Player A | Player B |
|---|---|---|---|---|---|
| | Game(e7fe733917) | Phase(COMMIT) | Last(CREATED - 2023-07-05T08:46:36) | Player(0xf39f...2266) Parity(odd) Ts(2023-07-05T08:46:36): Commit(7a7fa724fdce5a7f3408b99a73f48e565ceef6695da33f7a8f46fa61ef843ec1) | Player(0x7099...79c8) Parity(even): No Commit
| | Game(e7fe733917) | Phase(REVEAL) | Last(COMMIT ADDED - 2023-07-05T08:46:46) | Player(0xf39f...2266) Parity(odd) Ts(2023-07-05T08:46:36): Commit(7a7fa724fdce5a7f3408b99a73f48e565ceef6695da33f7a8f46fa61ef843ec1) | Player(0x7099...79c8) Parity(even) Ts(2023-07-05T08:46:46): Commit(ed01f128bb4157ff084ec7b5390bef2cb1b085c619d1b83a176a8f1d01ed2e03)
| | Game(e7fe733917) | Phase(REVEAL) | Last(REVEAL ADDED - 2023-07-05T08:46:51) | Player(0xf39f...2266) Parity(odd) Ts(2023-07-05T08:46:51): Commit(7a7fa724fdce5a7f3408b99a73f48e565ceef6695da33f7a8f46fa61ef843ec1), Action(5), Nonce(31791) | Player(0x7099...79c8) Parity(even) Ts(2023-07-05T08:46:46): Commit(ed01f128bb4157ff084ec7b5390bef2cb1b085c619d1b83a176a8f1d01ed2e03)
| WINNER\[normal victory\]\(0xf39f...2266\) | Game(e7fe733917) | Phase(FINISH) | Last(REVEAL ADDED - 2023-07-05T08:47:01) | Player(0xf39f...2266) Parity(odd) Ts(2023-07-05T08:46:51): Commit(7a7fa724fdce5a7f3408b99a73f48e565ceef6695da33f7a8f46fa61ef843ec1), Action(5), Nonce(31791) | Player(0x7099...79c8) Parity(even) Ts(2023-07-05T08:47:01): Commit(ed01f128bb4157ff084ec7b5390bef2cb1b085c619d1b83a176a8f1d01ed2e03), Action(0), Nonce(7633)


## Extra: Using Notices in Base Layer

Unlike reports, notices are messages that once the epoch finishes, Cartesi Rollups framework create a proof so the information may be used in other contracts. The Odds and Evens DApp generates a notice once a game finishes to inform the winner. The Notice has the following

To generate the notice proof, you can advance time in the local network and force the end of the epoch with the following command:

```shell
curl -H "Content-Type: application/json"  -X POST --data '{"id":1337,"jsonrpc":"2.0","method":"evm_increaseTime","params":[864000]}' http://localhost:8545
```

Then, to get the notice with the proof, you can run:

```shell
curl -s -H 'Content-Type: application/json' -X POST http://localhost:4000/graphql -d '{"query": "query { notices { edges { node { payload proof { context validity { inputIndex outputIndex machineStateHash outputHashesRootHash noticesEpochRootHash vouchersEpochRootHash keccakInHashesSiblings outputHashesInEpochSiblings }}}}}}"}' | jq -r -c '.data.notices.edges[] | .node | .payload,.proof.validity.inputIndex,.proof.validity.outputIndex,.proof.validity.outputHashesRootHash,.proof.validity.vouchersEpochRootHash,.proof.validity.noticesEpochRootHash,.proof.validity.machineStateHash,.proof.validity.keccakInHashesSiblings,.proof.validity.outputHashesInEpochSiblings,.proof.context' | xargs printf "%s ((%s,%s,%s,%s,%s,%s,%s,%s),%s)\n"
```

Save a single result to ```NOTICE_RESULT```, so you can reference it later.

As an example that uses the notice data, you can create a simple solidity contract that receives the notice payload and proof and adds to the players' score.

```solidity
// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import {Bitmask} from "@cartesi/util/contracts/Bitmask.sol";
import "@cartesi/rollups/contracts/dapp/ICartesiDApp.sol";
import "@cartesi/rollups/contracts/library/LibOutputValidation.sol";

contract Score {
    using Bitmask for mapping(uint256 => uint256);

    mapping(uint256 => uint256) noticeBitmask;

    mapping (address => uint) public nGames;
    mapping (address => uint) public nWins;

    address dappAddress;

    constructor(address _dappAddress) {
        dappAddress = _dappAddress;
    }

    function addScore(bytes calldata _payload, Proof calldata _v) public {
        ICartesiDApp dapp = ICartesiDApp(dappAddress);

        // validate notice
        dapp.validateNotice(_payload,_v);

        // check if notice has been processed
        uint256 noticePosition = LibOutputValidation.getBitMaskPosition(_v.validity.outputIndex,_v.validity.inputIndex);
        require(!noticeBitmask.getBit(noticePosition),"notice re-processing not allowed");

        // process notice
        (address playerA, address playerB, address winner) = abi.decode(_payload,(address, address, address));
        nGames[playerA] += 1;
        nGames[playerB] += 1;
        nWins[winner] += 1;

        // mark it as processed
        noticeBitmask.setBit(noticePosition, true);
    }

    function getScore(address player) public view returns (uint) {
        if (nGames[player] == 0) return 0;
        return 100 * nWins[player] / nGames[player];
    }
}
```

After deploying the contract (and obtain the ```CONTRACT_ADDRESS```), you can interact with:

```shell
cast send $CONTRACT_ADDRESS \
    "addScore(bytes,((uint64,uint64,bytes32,bytes32,bytes32,bytes32,bytes32[],bytes32[]),bytes))" $NOTICE_RESULT \
    --rpc-url http://localhost:8545 --from $PLAYER1 --private-key $PLAYER1_KEY
```

Then you can check the scores with:

```shell
cast call $CONTRACT_ADDRESS "getScore(address)" $PLAYER1 \
    --rpc-url http://localhost:8545 \
    | xargs printf "Player ($PLAYER1) Score: %d\n"
```
