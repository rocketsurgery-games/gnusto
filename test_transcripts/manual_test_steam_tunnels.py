#!/usr/bin/env python3
"""Manual test session for Steam Tunnels conversion."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grue import load_grue, GrueRuntime
from grue.repl import ReplEvaluator, ActionDone, ActionBlocked, ActionError, LocationResult
from grue.sexpr import parse, to_string

def test_session():
    """Run manual tests on steam tunnels area."""

    output_lines = []
    def log(msg):
        print(msg)
        output_lines.append(msg)

    log("=" * 60)
    log(f"Steam Tunnels Manual Test - {datetime.now().isoformat()}")
    log("=" * 60)

    # Load the game
    game_dir = Path(__file__).parent.parent / "games" / "lurkinghorror"
    world = load_grue(game_dir)
    rt = GrueRuntime(world)
    repl = ReplEvaluator(rt)

    def do_action(action_str):
        """Execute an action and return the result."""
        expr = parse(action_str)
        return repl.eval(expr)

    def show_state(obj_name):
        """Show object state."""
        try:
            obj = rt.state.objects.get(obj_name.lstrip("@"))
            if obj:
                log(f"--- Object state: {obj_name} ---")
                log(f"  location: {obj.location}")
                log(f"  flags: {obj.flags}")
            else:
                log(f"--- Object {obj_name} not found ---")
        except Exception as e:
            log(f"--- Error getting state for {obj_name}: {e} ---")

    def look():
        """Look at current room."""
        result = do_action("(look)")
        if isinstance(result, LocationResult):
            log(f"\n>>> look (current room: @{result.room})")
            log(f"Description: {result.description}")

    def test_action(action_str, description=""):
        """Test an action and log results."""
        log(f"\n>>> {action_str}")
        if description:
            log(f"  # {description}")
        try:
            result = do_action(action_str)
            if isinstance(result, ActionDone):
                log(f"  Outcome: success")
                if result.message:
                    log(f"  Message: {result.message}")
                if result.effects:
                    log(f"  Effects: {result.effects}")
            elif isinstance(result, ActionBlocked):
                log(f"  Outcome: blocked")
                log(f"  Reason: {result.reason}")
                for k, v in result.context:
                    log(f"    {k}: {v}")
            elif isinstance(result, ActionError):
                log(f"  Outcome: error")
                log(f"  Error: {result.message}")
            else:
                log(f"  Result: {result}")
            return result
        except Exception as e:
            log(f"  ERROR: {e}")
            return None

    # === CAVE AREA TESTS ===
    log("\n" + "=" * 60)
    log("CAVE AREA TESTS")
    log("=" * 60)

    # Start at brick tunnel
    do_action("(move! @player @brick-tunnel)")
    look()

    # Navigate to cave room
    test_action("(go north)", "Go north to cave room")
    look()

    # Navigate down to cave altar
    test_action("(go down)", "Go down to cave altar")
    look()

    # Examine objects at cave altar
    test_action("(do @knife :examine)", "Examine the knife")
    test_action("(do @knife :take)", "Take the knife")
    test_action("(do @slab :examine)", "Examine the stone slab")
    test_action("(do @slab :touch)", "Try to touch the slab (should cause revulsion)")
    test_action("(do @carvings :examine)", "Examine the carvings")

    # Iron plate puzzle
    test_action("(do @iron-plate :examine)", "Examine the iron plate")
    test_action("(do @iron-plate :open)", "Open the iron plate")
    show_state("@iron-plate")

    test_action("(do @iron-plate :look-inside)", "Look inside the pit (traumatic!)")
    log(f"\n  Global seen-pit = {rt.get_global('seen-pit')}")

    # Try again after seeing pit
    test_action("(do @iron-plate :look-inside)", "Try to look again (should be blocked)")
    test_action("(do @iron-plate :open)", "Try to open again (should be blocked)")

    # Go back up
    test_action("(go up)", "Go back up to cave room")
    look()

    # === STEAM TUNNEL TESTS ===
    log("\n" + "=" * 60)
    log("STEAM TUNNEL TESTS")
    log("=" * 60)

    # Go to tunnel area
    do_action("(move! @player @tunnel)")
    look()

    # Check cable climbing
    log(f"\n  Global on-cable = {rt.get_global('on-cable')}")
    test_action("(do @cable :climb)", "Climb onto the cable")
    log(f"  Global on-cable = {rt.get_global('on-cable')}")
    test_action("(do @cable :climb)", "Climb off the cable")
    log(f"  Global on-cable = {rt.get_global('on-cable')}")

    # Check access hatch
    test_action("(do @access-hatch :examine)", "Examine access hatch")
    test_action("(do @access-hatch :open)", "Open access hatch")
    show_state("@access-hatch")
    test_action("(do @access-hatch :close)", "Close access hatch")
    show_state("@access-hatch")

    # === PRESSURE VALVE / STEAM TESTS ===
    log("\n" + "=" * 60)
    log("PRESSURE VALVE / STEAM TESTS")
    log("=" * 60)

    # Go to tunnel-east where valve is
    do_action("(move! @player @tunnel-east)")
    look()

    # Make sure valve is off first
    do_action("(clear-flag! @pressure-valve OPENBIT)")
    do_action("(clear-flag! @steam-pipes HOT)")

    test_action("(do @pressure-valve :examine)", "Examine pressure valve")
    test_action("(do @pressure-valve :turn)", "Turn valve ON")
    show_state("@pressure-valve")
    show_state("@steam-pipes")

    # Try to go west through steam
    do_action("(move! @player @tunnel)")
    test_action("(go east)", "Try to go east through steam (should be blocked)")

    # Turn off valve and try again
    do_action("(move! @player @tunnel-east)")
    test_action("(do @pressure-valve :turn)", "Turn valve OFF")
    show_state("@pressure-valve")
    show_state("@steam-pipes")

    do_action("(move! @player @tunnel)")
    test_action("(go east)", "Go east with valve closed (should work)")
    look()

    # === BRICK WALL TESTS ===
    log("\n" + "=" * 60)
    log("BRICK WALL TESTS")
    log("=" * 60)

    do_action("(move! @player @steam-tunnel-east)")
    do_action("(set! brick-wall-broken false)")
    look()

    test_action("(do @brick-wall :examine)", "Examine brick wall")
    test_action("(do @brick-wall :push)", "Push through brick wall")
    log(f"\n  Global brick-wall-broken = {rt.get_global('brick-wall-broken')}")

    # Try going south through broken wall
    test_action("(go south)", "Go south through broken wall")
    look()

    # === RATS BARRIER TEST ===
    log("\n" + "=" * 60)
    log("RATS BARRIER TEST")
    log("=" * 60)

    # Rats start at @tunnel-west, so test from @tunnel going west
    do_action("(move! @player @tunnel)")
    do_action("(move! @rats @tunnel-west)")  # Ensure rats are at tunnel-west
    look()

    test_action("(go west)", "Try to go west through rats (should be blocked)")

    # Now test climbing cable to bypass rats
    test_action("(do @cable :climb)", "Climb onto cable")
    log(f"  Global on-cable = {rt.get_global('on-cable')}")
    test_action("(go west)", "Try to go west on cable (should pass)")
    look()

    # === DEAD END TEST ===
    log("\n" + "=" * 60)
    log("DEAD END (EAST WALL) TEST")
    log("=" * 60)

    do_action("(move! @player @steam-tunnel-east)")
    test_action("(go east)", "Try to go east (dead end)")

    # === SUMMARY ===
    log("\n" + "=" * 60)
    log("TEST SESSION COMPLETE")
    log("=" * 60)

    # Save transcript
    transcript_path = Path(__file__).parent / f"manual_test_steam_tunnels_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(transcript_path, 'w') as f:
        f.write('\n'.join(output_lines))
    print(f"\nTranscript saved to: {transcript_path}")

    return output_lines

if __name__ == "__main__":
    test_session()
