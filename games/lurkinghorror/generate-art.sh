#!/usr/bin/env bash
# Generate sketch-style artwork for Lurking Horror rooms and objects.
# Uses filfre + nanobanana (Gemini Flash) for generation.
#
# Usage: cd games/lurkinghorror && ./generate-art.sh

set -euo pipefail

ASSETS="assets"
STYLE="""
STYLE: Rough, light pencil sketch, modern comic style.
Broad strokes, only main object, very little detail, lines fading out at the edges.
No color, just pencil lines. Always with a solid white background.
"""

generate() {
    local file="$1"
    local desc="$2"
    local output="$ASSETS/$file"

    if [[ -f "$output" ]]; then
        echo "  SKIP $file (exists)"
        return
    fi

    echo "  GEN  $file"
    filfre generate --model nanobanana \
        --prompt "$STYLE"$'\n\n'"$desc" \
        --output "$output"
    echo "  OK   $file"
}

echo "Generating sketch art for Lurking Horror..."
echo

# --- Rooms ---

generate "terminal-room.png" \
    "A large 1980s university computer lab at night. Rows of CRT monitors and old terminals on desks. Pizza boxes and empty Coke cans scattered on tables. Banners, posters, and signs on the walls. Dim fluorescent lighting. Empty of people."

generate "cs-2nd.png" \
    "University building hallway at night, fluorescent lights, institutional architecture, stairs leading up and down visible in background, empty and eerie, wide angle view. A forward doorway, an elevator with call buttons on the left."

generate "kitchen.png" \
    "A 1980s university break room kitchen, dirty counter, fluorescent lighting, no windows, wide angle view showing full room, with refrigerator and microwave. Dirty, but not foul."

generate "cs-elevator-room.png" \
    "Dirty 1980s elevator interior with fake wood panel walls, scratched and graffitied, fluorescent light, control panel with buttons visible on the right wall, elevator doors straight ahead."

# --- Objects ---

generate "keyring.png" \
    "A large keyring with many keys hanging from it."

generate "carton.png" \
    "A Chinese food takeout carton with an occult-looking symbol on the front."

generate "hacker.png" \
    "A scruffy hacker in blue jeans and old work shirt. A large ring of keys hangs from his belt."

generate "pc.png" \
    "A late 1980s workstation PC with CRT monitor, mouse and keyboard. Windows with text overlap on the screen."

generate "access-panel.png" \
    "Elevator control panel with floor buttons (B, 1, 2, 3), open and close buttons, a stop switch, and an alarm button. A small access panel below."

generate "elevator-doors.png" \
    "1980s elevator doors in a university building hallway, brushed metal, closed."

generate "chair.png" \
    "A molded blue plastic chair, cheap and uncomfortable looking."

# --- Dynamic states: microwave ---

generate "microwave.png" \
    "A 1980s microwave oven with door closed, mounted above a kitchen counter."

generate "microwave-open.png" \
    "A 1980s microwave oven with door open, mounted above a kitchen counter, interior visible."

generate "microwave-running.png" \
    "A 1980s microwave oven running, light on inside, mounted above a kitchen counter."

# --- Dynamic states: refrigerator ---

generate "refrigerator.png" \
    "An old white refrigerator with notes and papers stuck to the front, door closed."

generate "refrigerator-open.png" \
    "An old white refrigerator with door open, revealing cluttered shelves with soggy lunch bags and old food containers."

echo
echo "Done. Update :render specs in .grue files to use new filenames."
