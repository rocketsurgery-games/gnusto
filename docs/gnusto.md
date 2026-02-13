# Gnusto

Gnusto is an LLM-powered interactive fiction system. Named after the write-magic-spell
from Infocom's Enchanter, it uses the Grue language to define game worlds.

The core innovation is the use of a language model to parse and interpret user input;
and to adapt world state to user-visible descriptions. The idea's pretty simple:
there's a logical world model that maintains the state of all the world's rooms,
objects, actors, and their varied relationships to one another. It interprets actions,
enforces constraints, and provides structured responses and world state information
that the agent interprets on behalf of the player.


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
  :ldesc "A really whiz-bang pc"
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

## Narrative Generation

The agent's primary job is to **interpret Grue output faithfully** while **stitching it together coherently**. The game's Grue code provides the narrative soul -- room descriptions, action results, character dialogue -- and the agent provides the glue that makes it flow naturally.

This is deliberately conservative: the agent doesn't invent narrative from scratch. Instead it:
- Adapts player input to available actions (flexible parsing)
- Executes actions and receives structured results from Grue
- Weaves multiple results into coherent prose
- Reduces repetition when similar actions occur
- Preserves character dialogue and key descriptions verbatim

This approach lets game authors maintain control over tone and story, while the agent handles the tedious work of natural language parsing and smooth presentation.

## Hints

The downside of being able to generate an unbounded amount of expository text, is that the player has no way of knowing whether or not they're "on the beaten path". To balance this, we can leverage the language model's interpretation and reasoning capabilities to gently guide the player in the right direction. 

## Context Management

Long play sessions create a challenge: the agent needs enough context to be helpful ("where did we leave that stone?") without overwhelming the LLM's context window. We address this with **progressive summarization**.

### History Tiers

The agent maintains three tiers of history:

```
[Summaries...] [Pending Buffer] [Recent turns]
                    ↑
       Summarize when action count exceeds threshold
```

**Recent turns**: Full detail -- player command, actions taken, Grue results, and the agent's narrative response. This provides immediate context for ongoing interactions.

**Pending buffer**: Full turns waiting to be batched. When the total action count exceeds the threshold, we summarize the oldest turns into a narrative block.

**Summaries**: Narrative blocks summarizing earlier gameplay. These form "the story so far" and grow as the game progresses.

### Action-Based Counting

A single user command ("sit at the pc and work on my term paper") can execute many game actions (sit, login, type, read, etc.). We track **actions**, not user commands, to ensure proper context management.

When total actions exceed `recent_actions + pending_buffer_actions`:
1. Remove oldest TurnRecords until we've cleared ~`pending_buffer_actions` worth
2. Call LLM to summarize those turns into narrative
3. The summary preserves: room context, objects found, NPC interactions, key events
4. Add the summary block to the summaries list

TurnRecords are never split -- we always summarize complete user commands together, preserving the connection between what the player asked and what happened.

### What the Agent Sees

Each turn, the agent receives:
```
System prompt
+ Summaries (oldest → newest, "the story so far")
+ Recent full turns (as conversation history)
+ Current game state + player command
```

The summaries provide long-term context while recent turns provide immediate detail.

### Notes as Emergent Knowledge

This design naturally supports player queries like "where was that stone?" or "what did the hacker say about the key?" The knowledge is embedded in the narrative summaries. Because the agent only knows what emerged through play (not by introspecting Grue state), it can't accidentally spoil puzzles.

Future enhancements could extract structured data from summaries (rooms visited, objects found, NPC relationships) for more precise queries, but the narrative-first approach works well as a starting point.

## Notes & Maps (Future)

While there's a certain nostalgia for the hand-written maps and notes needed to solve these games in their heyday, it's also very labor intensive (and often frustrating) for players. The agent can help players by generating contextual notes and maps automatically. Rather than simply exposing a fixed set of pre-canned "notes", as is still common even in modern games, we can leverage the agent to create notes and maps that precisely reflect the player's experience. And because the agent can see "behind the curtain", it can do so in such a way that they gently guide the player in the right direction.

## Conversations

Conversations in Infocom games aren't modeled specially -- spoken text is interleaved with regular text and not treated specially. In Gnusto, we're taking the opportunity to structure the output in such a way that the renderer can identify spoken words, alongside text and metadata indicating the speaker, demeanor, and anything else needed to capture the essence of the interaction.

### Hacker conversation example:
Here's an example conversation implementation from the Lurking Horror game:

```grue
  (def stage1-desc "The hacker wanders over, trying to look nonchalant. \"Losing, huh?\" he asks wittily. He glances at your terminal, which displays a pattern of snow and unusual characters. He appears somewhat excited.")

  (def stage2-desc "The hacker, mumbling under his breath, begins a flurry of activity. First the screen returns to something nearly normal, then windows begin popping up like toadstools after a rain.")

  (def stage3-desc "The hacker types furiously. After a while he says, \"Chomping file system. Your directory has gone seriously west. I fixed it.\" He checks the screen. \"It was mixed up on the file server with some files from the Department of Alchemy.\" He grunts. \"People's names for their nodes are getting weird. This one is called 'Lovecraft.'\" He pauses. \"Your paper is gone, though. Sorry. Maybe they could help you down there.\"")

  (def stage4-desc "The hacker wanders back to his terminal and returns to his hacking.")

  :location @terminal-room
  :on-turn (condp = (:help-stage @hacker)
    0 `((set @hacker :help-stage 1) (success :stage 1 :description ,stage1-desc))
    1 `((set @hacker :help-stage 2) (success :stage 2 :description ,stage2-desc))
    2 `((set @hacker :help-stage 3) (success :stage 3 :description ,stage3-desc))
    `((dequeue hacker-helps) (move @hacker @terminal-room) (success :stage 4 :description ,stage4-desc))))
```

In this format, there's no way to reliably distinguish arbitrarily quoted text from spoken words,
nor to reliably identify the speaker, even though it's often clear from context. Instead, we model
a mixture of conversation and exposition like this:

```grue
  (def stage1-desc (
    "The hacker wanders over, trying to look nonchalant."
    (speak @hacker "Losing, huh?" :demeanor "dry wit")
    "He glances at your terminal, which displays a pattern of snow and unusual characters. He appears somewhat excited."))

  (def stage2-desc (
    "The hacker, mumbling under his breath, begins a flurry of activity."
    "First the screen returns to something nearly normal, then windows begin popping up like toadstools after a rain."))

  (def stage3-desc (
    "The hacker types furiously."
    (speak @hacker "Chomping file system. Your directory has gone seriously west. I fixed it.")
    "He checks the screen."
    (speak @hacker "It was mixed up on the file server with some files from the Department of Alchemy.")
    "He grunts."
    (speak @hacker "People's names for their nodes are getting weird. This one is called 'Lovecraft.'")
    "He pauses."
    (speak @hacker "Your paper is gone, though. Sorry. Maybe they could help you down there.")))

  ...
```

# Open questions

## Result context
What do we _really_ want from effects like `(success :context (description "..."))`? Consider pulling all the context (e.g., `:context ((timer-display ...`) into explicit ui-effects that give instructions on how context should be displayed to the user.

Related: Look at @help-key:click for an example of very repetitive success messages. The agent's narrative stitching should help reduce this repetition, but we may want to revisit how Grue expresses context for the agent to work with.

## Summarization tuning
The progressive summarization system has several parameters to tune:
- **Batch size**: How many turns per summary block? Smaller = finer granularity, more LLM calls.
- **Summary prompt**: What should the LLM preserve? Room context, object locations, NPC dialogue, puzzle state?
- **Re-summarization**: When summaries grow too long, we may need to summarize summaries. Design TBD.

## Structured knowledge extraction
The current design embeds knowledge in narrative summaries. For precise queries ("list all rooms I've visited"), we may want to extract structured data alongside the narrative. This could be a simple addition to the summarization prompt.

