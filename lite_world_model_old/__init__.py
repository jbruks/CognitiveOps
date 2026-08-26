"""
Lite World Model subsystem.

Initial semantic cognitive layer inspired by scene graphs / LiteOpenUSD ideas.
Currently passive and non-invasive:
- receives perception/state
- builds semantic world snapshots
- does NOT affect rover behavior yet
"""

from .world_model import WorldModel
from .world_builder import WorldBuilder
