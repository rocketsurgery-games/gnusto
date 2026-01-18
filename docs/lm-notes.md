# Language model implementation

The core innovation in FrotzVM is the use of a language model to parse and interpret user input; and to adapt world state to user-visible descriptions. The idea's pretty simple: there's a logical world model that maintains the state of all the world's rooms, objects, actors, and their varied relationships to one another. It interprets actions, enforces constraints, and provides structured responses and world state information that the LM interprets on behalf of the player.


    ┌──────────────────────────────────────────────────────────────────────┐
    │                                                                      │
    │           written/spoken commands                                    │
    │           structured interactions                                    │
    │                 ┌────────┐                                           │
    │              ┌─►│ Input  ├──┐                                        │
    │  ┌────────┐  │  └────────┘  │  ┌────────┐   actions    ┌─────────┐   │
    │  │        ├──┘              └─►│        ├─────────────►│         │   │
    │  │  User  │                    │   LM   │              │  World  │   │
    │  │        │◄─┐              ┌──┤        │◄─────────────┤         │   │
    │  └────────┘  │  ┌────────┐  │  └────────┘  world state └─────────┘   │
    │              └──┤ Output │◄─┘               updates                  │
    │                 └────────┘                                           │
    │              text descriptions                                       │
    │              structured data                                         │
    │              images & sounds                                         │
    │                                                                      │
    └──────────────────────────────────────────────────────────────────────┘

## The world model

Is implemented in a Lisp-family language called Grue, that we designed for the express purpose of porting old Infocom
Z-Machine games written in ZIL. It uses largely the same set of built-in concepts as ZIL did -- rooms, objects,
actors, behaviors, events, etc. But with a modern reformulation that removes a lot of the 1970s-era language design &
optimizations, as well as anything related to text parsing and generation.

Grue exists to provide a precise, statically-analyzable backbone for the game's moving parts, possible states, and the framework of the story. But unlike old-school interactive fiction, the "program" isn't responsible for parsing user input or producing text. Instead, it accepts structured Grue actions as inputs -- e.g., `(do @door :open)` or `(do @hacker :give @pc)` -- that specify the exact action the player wishes to take. The game's world model then validates these actions, applies them to the world state, and returns state objects detailing relevant updates to the world state.


## The language model



# TODO

## Result context
What do we _really_ want from effects like `(success :context (description "..."))`? Consider pulling all the context (e.g., `:context ((timer-display ...`) into explicit ui-effects that give instructions on how context should be displayed to the user.

This is best addressed when we start bolting on the LM adapter for real. This will give us a much clearer idea of what we need to solve real needs.

