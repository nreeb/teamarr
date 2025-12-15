"""Event matching utilities.

Matches stream names to sporting events by extracting team names
and finding corresponding events in the schedule.
"""

import re
import unicodedata

from core import Event


class EventMatcher:
    """Match streams to sporting events.

    Works on pre-fetched events. The service layer handles fetching;
    this handles matching logic.
    """

    # Game indicator patterns (vs, @, at, etc.)
    GAME_INDICATORS = re.compile(
        r"\s+(?:vs\.?|v\.?|@|at)\s+", re.IGNORECASE
    )

    def find_by_team_ids(
        self,
        events: list[Event],
        team1_id: str,
        team2_id: str,
    ) -> Event | None:
        """Find event involving both teams by their IDs.

        Args:
            events: List of events to search
            team1_id: First team's ID
            team2_id: Second team's ID

        Returns:
            Matching event or None
        """
        for event in events:
            if not event.home_team or not event.away_team:
                continue
            event_team_ids = {event.home_team.id, event.away_team.id}
            if team1_id in event_team_ids and team2_id in event_team_ids:
                return event
        return None

    def find_by_team_names(
        self,
        events: list[Event],
        team1_name: str,
        team2_name: str,
    ) -> Event | None:
        """Find event by team name matching.

        Uses normalized matching (lowercase, no accents) for flexibility.

        Args:
            events: List of events to search
            team1_name: First team name (from stream, etc.)
            team2_name: Second team name

        Returns:
            Matching event or None
        """
        team1_norm = self._normalize(team1_name)
        team2_norm = self._normalize(team2_name)

        for event in events:
            if self._matches_event(event, team1_norm, team2_norm):
                return event
        return None

    def find_by_stream_name(
        self,
        events: list[Event],
        stream_name: str,
    ) -> Event | None:
        """Find event by parsing team names from stream title.

        Extracts teams from patterns like:
        - "Lions vs Bears"
        - "Detroit @ Chicago"
        - "NBA: Pistons v Celtics"

        Args:
            events: List of events to search
            stream_name: Stream title to parse

        Returns:
            Matching event or None
        """
        teams = self._extract_teams_from_stream(stream_name)
        if not teams or len(teams) < 2:
            return None

        return self.find_by_team_names(events, teams[0], teams[1])

    def find_all_by_team_id(
        self,
        events: list[Event],
        team_id: str,
    ) -> list[Event]:
        """Find all events involving a specific team.

        Args:
            events: List of events to search
            team_id: Team ID to find

        Returns:
            List of matching events
        """
        return [
            event for event in events
            if (event.home_team and event.home_team.id == team_id) or
               (event.away_team and event.away_team.id == team_id)
        ]

    def _extract_teams_from_stream(self, stream_name: str) -> list[str]:
        """Extract team names from stream title.

        Handles patterns like:
        - "Lions vs Bears"
        - "Detroit @ Chicago"
        - "NBA: Pistons v Celtics"
        - "ESPN+ 01: Team A @ Team B"

        Returns:
            List of team name strings (usually 2)
        """
        # Clean the stream name
        name = stream_name

        # Remove common prefixes (league indicators, channel numbers)
        # "ESPN+ 01: ", "NHL 123: ", "NBA: ", etc.
        name = re.sub(r"^[A-Za-z+]+\s*\d*\s*:\s*", "", name)

        # Split by game indicator
        match = self.GAME_INDICATORS.search(name)
        if not match:
            return []

        parts = self.GAME_INDICATORS.split(name, maxsplit=1)
        if len(parts) != 2:
            return []

        team1 = parts[0].strip()
        team2 = parts[1].strip()

        # Clean up team names (remove trailing time/date info)
        team1 = re.sub(r"\s+\d{1,2}:\d{2}.*$", "", team1)
        team2 = re.sub(r"\s+\d{1,2}:\d{2}.*$", "", team2)

        return [team1, team2] if team1 and team2 else []

    def _matches_event(
        self,
        event: Event,
        team1_norm: str,
        team2_norm: str,
    ) -> bool:
        """Check if event matches both team names."""
        searchable = self._build_searchable(event)
        return team1_norm in searchable and team2_norm in searchable

    def _build_searchable(self, event: Event) -> str:
        """Build normalized searchable string from event."""
        parts = [
            event.name,
            event.short_name,
        ]

        if event.home_team:
            parts.extend([
                event.home_team.name,
                event.home_team.short_name,
                event.home_team.abbreviation,
            ])

        if event.away_team:
            parts.extend([
                event.away_team.name,
                event.away_team.short_name,
                event.away_team.abbreviation,
            ])

        combined = " ".join(p for p in parts if p)
        return self._normalize(combined)

    def _normalize(self, text: str) -> str:
        """Normalize text for matching.

        - Lowercase
        - Strip whitespace
        - Remove accents (é → e)
        - Common abbreviations
        """
        if not text:
            return ""

        text = text.lower().strip()

        # Remove accents
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")

        # Common abbreviations
        text = text.replace("st.", "saint").replace("st ", "saint ")

        return text


def has_game_indicator(stream_name: str) -> bool:
    """Check if stream name contains a game indicator (vs, @, at).

    Used to filter streams that likely represent games vs generic content.
    """
    return bool(EventMatcher.GAME_INDICATORS.search(stream_name))
