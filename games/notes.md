# Resources
- [Infocom Sources](https://github.com/the-infocom-files)
- [Infocom Doc Project](https://infodoc.plover.net/manuals/index.html)
- [Adventure History: Infocom](https://mocagh.org/loadpage.php?getcompany=infocom)
- [Infocom Gallery](https://gallery.guetech.org/)
- [Invisiclues](https://www.invisiclues.org/invisiclues/)

# Zork I
- [Source](https://github.com/the-infocom-files/zork1)


# Enchanter
- [Source](https://github.com/the-infocom-files/enchanter)
- [Solution Archive](https://solutionarchive.com/game/id%2C177/Enchanter.html)
- [Gallery](https://gallery.guetech.org/enchanter/enchanter.html)
- [Museum](https://www.mocagh.org/loadpage.php?getgame=enchanterfolio)
- [Manual](https://www.mocagh.org/infocom/enchanter-manual.pdf)


# Lurking Horror
- [Source](https://github.com/the-infocom-files/lurkinghorror)


# Game Directory Structure

Each game directory follows this structure:

```
games/<game>/
├── source/           # Original ZIL source files (reference only)
├── converted/        # Auto-converted GRUE output (from zil2grue)
│   ├── objects.grue  # Object definitions with [NEEDS-TRANSLATION] markers
│   ├── rooms.grue    # Room definitions
│   ├── barriers.grue # Door/barrier logic
│   └── reference/    # ZIL constructs for reference (globals, routines, etc.)
├── *.grue            # Hand-translated source files (authoritative)
└── *.test.grue       # Test world files for specific features
```

**Workflow:**
1. `zil2grue` auto-converts ZIL source → `converted/` subdirectory
2. Hand-translate behaviors from `converted/` → root `.grue` files
3. Mark translated objects in `converted/` with reference to authoritative source
4. Never edit `converted/` in place for behavior translation

**Why this separation:**
- `converted/` preserves original ZIL comments for reference
- Root `.grue` files are clean, hand-crafted source
- Re-running converter won't clobber hand-translated work
- Easy to diff what's translated vs auto-converted

