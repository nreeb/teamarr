"""Consumer layer for EPG generation.

Consumers implement business logic using the service layer.
All processing uses dataclasses - no dict conversion layers.
"""

from consumers.event_epg import (
    EventChannelInfo,
    EventEPGGenerator,
    EventEPGOptions,
    EventTemplateConfig,
    MatchedStream,
)
from consumers.event_matcher import EventMatcher, has_game_indicator
from consumers.orchestrator import (
    GenerationResult,
    Orchestrator,
)
from consumers.team_epg import (
    TeamChannelConfig,
    TeamEPGGenerator,
    TeamEPGOptions,
    TemplateConfig,
)

__all__ = [
    # Orchestrator
    "GenerationResult",
    "Orchestrator",
    # Team EPG
    "TeamChannelConfig",
    "TeamEPGGenerator",
    "TeamEPGOptions",
    "TemplateConfig",
    # Event EPG
    "EventChannelInfo",
    "EventEPGGenerator",
    "EventEPGOptions",
    "EventTemplateConfig",
    "MatchedStream",
    # Event Matcher
    "EventMatcher",
    "has_game_indicator",
]
