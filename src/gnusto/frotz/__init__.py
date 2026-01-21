"""
Frotz - State-space analyzer for Grue games.

Named after the light spell from Enchanter, Frotz "illuminates" the dark
passages of game state space to verify winnability and detect soft-locks.

Components (to be implemented):
- effects.py: Effect analysis pass (what can change?)
- relevance.py: Victory-relevant slice (what matters?)
- explorer.py: State space exploration with quotient
- output.py: Output and visualization

See docs/frotz-design.md for the design document.
"""

__all__: list[str] = []
