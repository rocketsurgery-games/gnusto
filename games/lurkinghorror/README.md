# The Lurking Horror - FrotzLM / Grue conversion

This is a conversion of Infocom's _The Lurking Horror_ to Grue, to execute in the FrotzLM runtime.

# Structure

`./lurkinghorror.grue` is the entrypoint, defining the world and player objects. The rest of the files are largely
organized by room (e.g., `./terminal-room.grue`), object (e.g., `./pc.grue`), and character (`./hacker.grue`). Most
non-trivial objects have unit tests (as in `./terminal-room.test.grue`) to validate their behavior.

