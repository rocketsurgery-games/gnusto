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

Grue exists to provide a precise, statically-analyzable backbone for the game's moving parts, possible states, and the framework of the story. But unlike old-school interactive fiction, the program isn't responsible for parsing user input or producing text. Instead, it accepts structured Grue actions as inputs -- e.g., `(do @hacker :give @pc)` -- that specify the exact action the player wishes to take. The game's world model then validates these actions, applies them to the world state, and returns objects detailing relevant updates to the world state -- e.g., `(blocked :reason not-interested)`.

The world model also provides structured information about the world to the language model. E.g., a room might be described as follows:
```grue
(room @terminal-room
  :description "Terminal Room"
  :ldesc "This is a large room crammed with computer terminals, small computers, and printers. An exit leads south.
    Banners, posters, and signs festoon the walls. Most of the tables are covered with waste paper, old pizza boxes,
    and empty Coke cans. There are usually a lot of people here, but tonight it's almost deserted."
  :properties (
    :lit true
  )
  :exits (
    (south :to @cs-2nd :via @hacker-exit-barrier)
    (out :to @cs-2nd :via @hacker-exit-barrier)
  )
  :objects (
    @player
    @hacker
    @pc
    @chair
  )
```

And an object as:
```grue
(object @pc
  :description "pc"
  :fdesc "A really whiz-bang pc"
  :properties (
    :on false
    :unplugged false
    :logged-in false
  )
  :behaviors (
    :examine
    :listen
    :take
    :put-on ?item
    :read
    :turn-on
    :turn-off
    :plug-in
    :unplug
    :sit-at
    :type ?text
    :login ?username
    :password ?password
  )
)
```

The goal is for the language model to have all the information it needs to communicate to the player what's happening
in the world. And to have sufficient information to generate text, images, and audio, and to interpret the player's
requests (whatever form they take), adapting it to the internal structures of the world model.

## The language model




# Open questions

## Result context
What do we _really_ want from effects like `(success :context (description "..."))`? Consider pulling all the context (e.g., `:context ((timer-display ...`) into explicit ui-effects that give instructions on how context should be displayed to the user.

This is best addressed when we start bolting on the LM adapter for real. This will give us a much clearer idea of what we need to solve real needs.

