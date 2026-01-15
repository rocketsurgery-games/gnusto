"""Comprehensive manual testing session for The Lurking Horror.

Tests various areas, objects, and interactions to find conversion issues.
"""
import sys
from datetime import datetime

sys.path.insert(0, "/Users/joel/src/rs/frotz-lm/src")

from grue.parser import load_grue
from grue.runtime import GrueRuntime


def log(msg: str):
    """Print and flush immediately."""
    print(msg, flush=True)


def test_action(rt: GrueRuntime, target: str, verb: str, *args):
    """Execute an action and print the result."""
    log(f"\n>>> (do {target} :{verb}{' ' + ' '.join(args) if args else ''})")
    try:
        result = rt.do(target, verb, *args)
        log(f"Outcome: {result.outcome}")
        if result.error:
            log(f"ERROR: {result.error}")
        for k, v in result.context:
            log(f"  {k}: {v}")
        return result
    except Exception as e:
        log(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return None


def look(rt: GrueRuntime):
    """Get room description."""
    log(f"\n>>> look (current room: {rt.state.objects.get('@player').location})")
    try:
        desc = rt.get_room_description()
        log(f"Description: {desc}")
        return desc
    except Exception as e:
        log(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_object(rt: GrueRuntime, obj_id: str):
    """Check an object's state."""
    log(f"\n--- Object state: {obj_id} ---")
    obj = rt.state.objects.get(obj_id)
    if obj:
        log(f"  location: {obj.location}")
        log(f"  flags: {obj.flags}")
        log(f"  properties: {obj.properties}")
    else:
        log(f"  (no state)")


def main():
    log("=" * 60)
    log(f"Manual Test Session - {datetime.now().isoformat()}")
    log("=" * 60)

    world = load_grue("games/lurkinghorror/")
    rt = GrueRuntime(world)

    # ========== Terminal Room Tests ==========
    log("\n" + "=" * 60)
    log("TERMINAL ROOM TESTS")
    log("=" * 60)

    look(rt)
    check_object(rt, "@player")

    # Test PC interactions
    test_action(rt, "@pc", "examine")
    test_action(rt, "@pc", "turn-on")
    test_action(rt, "@pc", "type", "help")
    test_action(rt, "@pc", "type", "ustrex")
    test_action(rt, "@pc", "type", "bazbar")  # wrong password

    # Test assignment
    test_action(rt, "@assignment", "examine")
    test_action(rt, "@assignment", "take")
    check_object(rt, "@assignment")

    # Test container
    test_action(rt, "@container", "examine")

    # ========== Elevator Tests ==========
    log("\n" + "=" * 60)
    log("ELEVATOR TESTS")
    log("=" * 60)

    # Move to hallway first
    test_action(rt, "@player", "go", "north")
    look(rt)

    # Try elevator
    test_action(rt, "@elevator-door", "examine")
    test_action(rt, "@elevator-button", "push")
    check_object(rt, "@elevator-door")

    # Wait for elevator
    for i in range(5):
        test_action(rt, "@player", "wait")
        check_object(rt, "@elevator-door")

    # Enter elevator if door is open
    test_action(rt, "@player", "go", "east")
    look(rt)

    # Try elevator buttons
    test_action(rt, "@5-button", "push")
    test_action(rt, "@player", "wait")

    # ========== Hacker Tests ==========
    log("\n" + "=" * 60)
    log("HACKER TESTS")
    log("=" * 60)

    # Reset and test hacker interactions
    rt = GrueRuntime(world)
    # Move player to hacker's location
    rt.state.objects["@player"].location = "@terminal-room"

    test_action(rt, "@hacker", "examine")
    test_action(rt, "@hacker", "ask", "@master-key")
    test_action(rt, "@hacker", "ask", "@assignment")

    # ========== Kitchen Tests ==========
    log("\n" + "=" * 60)
    log("KITCHEN TESTS")
    log("=" * 60)

    rt = GrueRuntime(world)
    rt.state.objects["@player"].location = "@kitchen"
    look(rt)

    # Test objects
    test_action(rt, "@refrigerator", "examine")
    test_action(rt, "@refrigerator", "open")
    test_action(rt, "@chinese-food", "examine")
    test_action(rt, "@chinese-food", "take")
    test_action(rt, "@chinese-food", "eat")

    # Microwave
    test_action(rt, "@microwave", "examine")
    test_action(rt, "@microwave", "open")
    test_action(rt, "@chinese-food", "put", "@microwave")
    test_action(rt, "@microwave", "close")
    test_action(rt, "@microwave", "turn-on")
    test_action(rt, "@microwave", "open")

    # ========== CS Basement Tests ==========
    log("\n" + "=" * 60)
    log("CS BASEMENT TESTS")
    log("=" * 60)

    rt = GrueRuntime(world)
    rt.state.objects["@player"].location = "@cs-basement"
    look(rt)

    test_action(rt, "@player", "go", "down")  # to tunnels stub

    # ========== Great Dome Tests ==========
    log("\n" + "=" * 60)
    log("GREAT DOME TESTS")
    log("=" * 60)

    rt = GrueRuntime(world)
    rt.state.objects["@player"].location = "@great-dome"
    look(rt)

    # Test tentacle
    test_action(rt, "@tentacle", "examine")
    test_action(rt, "@tentacle", "climb")
    look(rt)

    # ========== Yuggoth Tests ==========
    log("\n" + "=" * 60)
    log("YUGGOTH TESTS")
    log("=" * 60)

    rt = GrueRuntime(world)
    # Set up Yuggoth conditions
    rt.state.globals["yuggoth-moved"] = True
    rt.state.objects["@player"].location = "@yuggoth"
    look(rt)

    test_action(rt, "@player", "go", "north")
    look(rt)

    # ========== Brown Building Tests ==========
    log("\n" + "=" * 60)
    log("BROWN BUILDING TESTS")
    log("=" * 60)

    rt = GrueRuntime(world)
    rt.state.objects["@player"].location = "@brown-building"
    look(rt)

    test_action(rt, "@axe-case", "examine")
    test_action(rt, "@fire-axe", "take")  # Should fail - in case
    test_action(rt, "@axe-case", "open")
    test_action(rt, "@fire-axe", "take")

    # ========== Object Inventory Check ==========
    log("\n" + "=" * 60)
    log("CHECKING ALL OBJECTS FOR MISSING BEHAVIORS")
    log("=" * 60)

    rt = GrueRuntime(world)
    objects_without_behaviors = []
    for obj_id, obj_def in world.objects.items():
        if not obj_def.behaviors and obj_id.startswith("@"):
            # Skip rooms and obvious stub objects
            if obj_def.flags and "room" in obj_def.flags:
                continue
            objects_without_behaviors.append(obj_id)

    log(f"\nObjects without any behaviors: {len(objects_without_behaviors)}")
    for obj_id in sorted(objects_without_behaviors):
        log(f"  {obj_id}")

    log("\n" + "=" * 60)
    log("TEST SESSION COMPLETE")
    log("=" * 60)


if __name__ == "__main__":
    main()
