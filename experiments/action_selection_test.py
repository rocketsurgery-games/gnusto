#!/usr/bin/env python3
"""
Test harness for evaluating LLM action selection.

This experiment tests whether an LLM can reliably:
1. Map natural language to valid game actions
2. Identify when no action applies (generate flavor response)
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Add parent to path for zil imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

from zil import load_game, LLMGameInterface, create_test_cases


@dataclass
class TestResult:
    """Result of a single test case."""
    input: str
    expected_action: str | None
    expected_target: str | None
    actual_action: str | None
    actual_target: str | None
    response_text: str
    reasoning: str
    category: str
    passed: bool
    error: str | None = None


def run_test(
    client: anthropic.Anthropic,
    interface: LLMGameInterface,
    test_case: dict,
    model: str = "claude-sonnet-4-20250514",
) -> TestResult:
    """Run a single test case."""
    player_input = test_case["input"]
    expected_action = test_case.get("expected_action")
    expected_target = test_case.get("expected_target")
    category = test_case.get("category", "unknown")

    # Build prompt
    prompt = interface.build_prompt(player_input)

    try:
        # Call Claude
        response = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract response text
        response_text = response.content[0].text

        # Parse JSON from response
        # Look for JSON block
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            parsed = json.loads(json_str)
        else:
            return TestResult(
                input=player_input,
                expected_action=expected_action,
                expected_target=expected_target,
                actual_action=None,
                actual_target=None,
                response_text=response_text,
                reasoning="",
                category=category,
                passed=False,
                error="Could not find JSON in response",
            )

        # Extract results
        has_action = parsed.get("has_action", False)
        actual_action = parsed.get("action") if has_action else None
        actual_target = parsed.get("target") if has_action else None
        reasoning = parsed.get("reasoning", "")
        flavor_response = parsed.get("response_text", "")

        # Determine if test passed
        if expected_action is None:
            # Expected no action - pass if LLM also said no action
            passed = not has_action
        else:
            # Expected action - check if it matches
            action_match = actual_action and actual_action.lower() == expected_action.lower()
            if expected_target:
                # Normalize target comparison
                actual_norm = actual_target.lower() if actual_target else ""
                expected_norm = expected_target.lower()
                target_match = expected_norm in actual_norm or actual_norm in expected_norm
                passed = action_match and target_match
            else:
                passed = action_match

        return TestResult(
            input=player_input,
            expected_action=expected_action,
            expected_target=expected_target,
            actual_action=actual_action,
            actual_target=actual_target,
            response_text=flavor_response or response_text[:200],
            reasoning=reasoning,
            category=category,
            passed=passed,
        )

    except json.JSONDecodeError as e:
        return TestResult(
            input=player_input,
            expected_action=expected_action,
            expected_target=expected_target,
            actual_action=None,
            actual_target=None,
            response_text=response_text if 'response_text' in dir() else "",
            reasoning="",
            category=category,
            passed=False,
            error=f"JSON parse error: {e}",
        )
    except Exception as e:
        return TestResult(
            input=player_input,
            expected_action=expected_action,
            expected_target=expected_target,
            actual_action=None,
            actual_target=None,
            response_text="",
            reasoning="",
            category=category,
            passed=False,
            error=str(e),
        )


def run_experiment(
    model: str = "claude-sonnet-4-20250514",
    test_cases: list[dict] | None = None,
):
    """Run the full experiment."""
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    client = anthropic.Anthropic()

    # Load game
    print("Loading game...")
    data, world = load_game("infocom/lurkinghorror")
    interface = LLMGameInterface(world)
    print(f"Loaded: {len(data.rooms)} rooms, {len(data.objects)} objects")
    print(f"Starting room: {world.state.current_room}\n")

    # Get test cases
    if test_cases is None:
        test_cases = create_test_cases()

    print(f"Running {len(test_cases)} test cases with model: {model}\n")
    print("=" * 60)

    results: list[TestResult] = []
    categories: dict[str, list[TestResult]] = {}

    for i, tc in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Input: \"{tc['input']}\"")
        print(f"  Expected: action={tc.get('expected_action')}, target={tc.get('expected_target')}")

        result = run_test(client, interface, tc, model)
        results.append(result)

        # Track by category
        cat = result.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(result)

        print(f"  Actual:   action={result.actual_action}, target={result.actual_target}")
        print(f"  Reasoning: {result.reasoning[:100]}..." if len(result.reasoning) > 100 else f"  Reasoning: {result.reasoning}")
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status}")

        if result.error:
            print(f"  Error: {result.error}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_passed = sum(1 for r in results if r.passed)
    print(f"\nOverall: {total_passed}/{len(results)} ({100*total_passed/len(results):.1f}%)")

    print("\nBy category:")
    for cat, cat_results in sorted(categories.items()):
        cat_passed = sum(1 for r in cat_results if r.passed)
        print(f"  {cat}: {cat_passed}/{len(cat_results)} ({100*cat_passed/len(cat_results):.1f}%)")

    print("\nFailed cases:")
    for r in results:
        if not r.passed:
            print(f"  - \"{r.input}\" (expected {r.expected_action}/{r.expected_target}, got {r.actual_action}/{r.actual_target})")

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test LLM action selection")
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Model to use (default: claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only a few test cases",
    )

    args = parser.parse_args()

    test_cases = None
    if args.quick:
        # Just run a few representative cases
        test_cases = [
            {"input": "go south", "expected_action": "go", "expected_target": "south", "category": "clear_match"},
            {"input": "grab the chair", "expected_action": "take", "expected_target": "chair", "category": "synonym"},
            {"input": "what's that computer over there?", "expected_action": "examine", "expected_target": "pc", "category": "natural"},
            {"input": "hello there!", "expected_action": None, "expected_target": None, "category": "flavor"},
            {"input": "fly away", "expected_action": None, "expected_target": None, "category": "impossible"},
        ]

    run_experiment(model=args.model, test_cases=test_cases)


if __name__ == "__main__":
    main()
