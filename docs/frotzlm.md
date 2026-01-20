The core innovation in FrotzLM is the use of a language model to parse and interpret user input; and to adapt world state to user-visible descriptions. The idea's pretty simple: there's a logical world model that maintains the state of all the world's rooms, objects, actors, and their varied relationships to one another. It interprets actions, enforces constraints, and provides structured responses and world state information that the agent interprets on behalf of the player.


```
           written/spoken commands
           structured interactions
                 ┌────────┐
              ┌─►│ Input  ├──┐
  ┌────────┐  │  └────────┘  │  ┌────────┐   actions    ┌─────────┐
  │        ├──┘              └─►│        ├─────────────►│         │
  │  User  │                    │ Agent  │              │  World  │
  │        │◄─┐              ┌──┤        │◄─────────────┤         │
  └────────┘  │  ┌────────┐  │  └────────┘  world state └─────────┘
              └──┤ Output │◄─┘               updates
                 └────────┘
              text descriptions
              structured data
              images & sounds
```

# The world model

Is implemented in a Lisp-family language called Grue, that we designed for the express purpose of porting old Infocom Z-Machine games written in ZIL. It uses largely the same set of built-in concepts as ZIL did -- rooms, objects, actors, behaviors, events, etc. But with a modern reformulation that removes a lot of the 1970s-era language design & optimizations, as well as anything related to text parsing and generation.

Grue exists to provide a precise, statically-analyzable backbone for the game's moving parts, possible states, and the framework of the story. But unlike old-school interactive fiction, the program isn't responsible for parsing user input or producing text. Instead, it accepts structured Grue actions as inputs -- e.g., `(do @hacker :give @pc)` -- that specify the exact action the player wishes to take. The game's world model then validates these actions, applies them to the world state, and returns objects detailing relevant updates to the world state -- e.g., `(blocked :reason not-interested)`.

The world model also provides structured information about the world to the agent. E.g., a room might be described as follows:
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

The goal is for the agent to have all the information it needs to communicate to the player what's happening in the world. And to have sufficient information to generate text, images, and audio, and to interpret the player's requests (whatever form they take), adapting it to the internal structures of the world model.

# The LLM Agent

The agent's job is to make sense of the world model for the player, describe it using the tools at its disposal (e.g., text, images, sounds, etc), and help the player take actions. In its simplest manifestation, this could be nothing more than a replacement for the text parser and generator in the original Infocom games. But it can be much more than this.

In the original Infocom games, wrestling with the text parser and identifying possible actions could be extraordinarily frustrating. This was an unavoidable consequence of using hand-written text parsers on the simple micros of the era. But a modern language model is capable of parsing arbitrary input and matching the user's intentions to the world state, and available actions. This should dramatically reduce the frustration of wrestling with the parser, figuring out exactly which terminology the implementor expected, and so forth.

## Text generation

These games were also famous for repetitive text, especially for anything outside of the game's happy path. E.g., "I don't know what to do with that." An LLM-based agent, with the right guidance, can allow the player to explore and try many things not manually built into the game design, creating a depth of exploration and experience far beyond traditional interactive fiction.

## Hints

The downside of being able to generate an unbounded amount of expository text, is that the player has no way of knowing whether or not they're "on the beaten path". To balance this, we can leverage the language model's interpretation and reasoning capabilities to gently guide the player in the right direction. 

## Notes & Bookkeeping

While there's a certain nostalgia for the hand-written maps and notes needed to solve these games in their heyday, it's also very labor intensive (and often frustrating) for players. The agent can help players by generating contextual notes and maps automatically. Rather than simply exposing a fixed set of pre-canned "notes", as is still common even in modern games, we can leverage the agent to create notes and maps that precisely reflect the player's experience. And because the agent can see "behind the curtain", it can do so in such a way that they gently guide the player in the right direction.

## Conversations

TODO


# Open questions

## Result context
What do we _really_ want from effects like `(success :context (description "..."))`? Consider pulling all the context (e.g., `:context ((timer-display ...`) into explicit ui-effects that give instructions on how context should be displayed to the user.

This is best addressed when we start bolting on the agent adapter for real. This will give us a much clearer idea of what we need to solve real needs.

Related: Look at @help-key:click for an example of very repetitive success messages. While we could simplify this
a good bit with some string manipulation, it also provides an opportunity to think through what we want the interactions from grue -> agent to look like, so we can achieve our goals more flexibly.

## "Helpful" agents
We sometimes get fascinating, unsolicited responses from the agent, like so:

```
user > (do @yak-window :click)                                                                     

grue > You click the box for your paper, and the box grows reassuringly until it fills most of     
the screen. Unfortunately, the text that fills it bears no resemblance to your paper. The   
title is the same, but after that, there is something different, very different.            

agent >
Oh no! Something very strange has happened to your classics paper. The editor has opened
it, but the content is completely different from what you wrote - only the title remains
the same. This is quite alarming, especially with the paper due tomorrow!

You can see that your paper (@odd-paper) is now displayed, and there's also a @more-box
available. The fact that it's now called "odd-paper" in the system suggests something
unusual has definitely occurred.

You might want to examine the paper to see exactly what's wrong with it, or check the more │
box to see if there are additional options. There's also a hacker in the room who might
know something about what happened to your file.

What would you like to do? You could:

 • Examine the odd paper to see what's actually written there
 • Click the more box to see what options are available
 • Ask the hacker about what might have happened
 • Try to figure out how to restore your original paper
```

This is fascinating, but also a bit more helpful than we actually want it to be!

