"""Event-based EPG generation - pure dataclass pipeline.

Creates one channel per event (game). Used for event groups where
streams are matched to specific games.

Data flow:
- Service layer returns Event dataclasses (via scoreboard)
- EventMatcher links streams to events
- ContextBuilder creates TemplateContext
- TemplateResolver resolves templates
- Output: Programme dataclasses ready for XMLTV
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from core import Event, Programme
from services import SportsDataService
from template_resolver import TemplateResolver
from template_resolver.context_builder import ContextBuilder
from utilities.sports import get_sport_duration
from utilities.tz import now_user, to_user_tz, get_user_tz

logger = logging.getLogger(__name__)


@dataclass
class EventChannelInfo:
    """Generated channel info for an event."""

    channel_id: str
    name: str
    event_id: str
    league: str
    icon: str | None = None


@dataclass
class EventTemplateConfig:
    """Template configuration for event-based EPG."""

    # Event programme templates
    title_format: str = "{away_team} @ {home_team}"
    channel_name_format: str = "{away_team_abbrev} @ {home_team_abbrev}"
    description_format: str = "{matchup} | {venue_full} | {broadcast_simple}"
    subtitle_format: str = "{venue_city}"
    category: str = "Sports"
    icon_url: str | None = None

    # Pregame filler templates
    pregame_enabled: bool = True
    pregame_title: str = "Pregame Coverage"
    pregame_subtitle: str | None = None
    pregame_description: str = "{away_team} @ {home_team} starts at {game_time}"
    pregame_icon_url: str | None = None

    # Postgame filler templates
    postgame_enabled: bool = True
    postgame_title: str = "Postgame Recap"
    postgame_subtitle: str | None = None
    postgame_description: str = "{away_team} @ {home_team} - {final_score}"
    postgame_icon_url: str | None = None

    # Conditional postgame (different text based on game status)
    postgame_conditional_enabled: bool = False
    postgame_description_final: str = "{away_team} @ {home_team} Final: {final_score}"
    postgame_description_not_final: str = "{away_team} @ {home_team} - game in progress"


@dataclass
class EventEPGOptions:
    """Options for event-based EPG generation."""

    pregame_minutes: int = 30
    default_duration_hours: float = 3.0
    days_ahead: int = 14  # EPG window size
    template: EventTemplateConfig = field(default_factory=EventTemplateConfig)
    epg_timezone: str = "America/New_York"

    # Sport durations (from database settings)
    sport_durations: dict[str, float] = field(default_factory=dict)


@dataclass
class MatchedStream:
    """A stream matched to an event."""

    stream_id: str
    stream_name: str
    event: Event
    channel_id: str


class EventEPGGenerator:
    """Generates EPG programmes for event-based channels.

    Each event gets its own channel. Streams are matched to events
    by team names extracted from stream titles.

    Supports pregame/postgame filler that spans multiple days:
    - Pregame: EPG start → event start
    - Postgame: event end → EPG end
    """

    def __init__(self, service: SportsDataService):
        self._service = service
        self._context_builder = ContextBuilder(service)
        self._resolver = TemplateResolver()

    def generate_with_filler(
        self,
        event: Event,
        channel_id: str,
        options: EventEPGOptions | None = None,
        stream_name: str | None = None,
        epg_start: datetime | None = None,
    ) -> list[Programme]:
        """Generate EPG programmes for an event with filler.

        Creates pregame, event, and postgame programmes.
        Filler spans from EPG start to event start (pregame) and
        event end to EPG end (postgame), with daily chunks.

        Args:
            event: The event to generate EPG for
            channel_id: XMLTV channel ID
            options: Generation options including templates
            stream_name: Optional stream name (for UFC prelim/main detection)
            epg_start: EPG start datetime (defaults to now)

        Returns:
            List of Programme entries (pregame + event + postgame)
        """
        options = options or EventEPGOptions()
        template = options.template

        # EPG timing
        tz = get_user_tz(options.epg_timezone)
        if epg_start is None:
            epg_start = now_user().replace(minute=0, second=0, microsecond=0)
        elif epg_start.tzinfo is None:
            epg_start = epg_start.replace(tzinfo=tz)

        epg_end = datetime.combine(
            epg_start.date() + timedelta(days=options.days_ahead),
            datetime.min.time(),
        ).replace(tzinfo=tz)

        programmes: list[Programme] = []

        # Build context for template resolution
        context = self._context_builder.build_for_event(
            event=event,
            team_id=event.home_team.id,
            league=event.league,
            epg_timezone=options.epg_timezone,
        )

        # Calculate event timing
        event_start = event.start_time - timedelta(minutes=options.pregame_minutes)
        duration = get_sport_duration(
            event.sport, options.sport_durations, options.default_duration_hours
        )
        event_end = event.start_time + timedelta(hours=duration)

        # Handle UFC/MMA special timing
        if event.sport == "mma" and stream_name and event.main_card_start:
            event_start, event_end = self._get_ufc_programme_times(
                event, stream_name, options.sport_durations, options.default_duration_hours
            )
            event_start = event_start - timedelta(minutes=options.pregame_minutes)

        # 1. Pregame filler
        if template.pregame_enabled:
            pregame_programmes = self._generate_filler_programmes(
                event=event,
                channel_id=channel_id,
                context=context,
                filler_type="pregame",
                filler_start=epg_start,
                filler_end=event_start,
                template=template,
                options=options,
            )
            programmes.extend(pregame_programmes)

        # 2. Event programme
        event_programme = self._event_to_programme(
            event, context, channel_id, options, stream_name
        )
        programmes.append(event_programme)

        # 3. Postgame filler (enrich event for fresh scores)
        if template.postgame_enabled:
            enriched_event = self._enrich_event_for_postgame(event)
            postgame_context = self._context_builder.build_for_event(
                event=enriched_event,
                team_id=enriched_event.home_team.id,
                league=enriched_event.league,
                epg_timezone=options.epg_timezone,
            )
            postgame_programmes = self._generate_filler_programmes(
                event=enriched_event,
                channel_id=channel_id,
                context=postgame_context,
                filler_type="postgame",
                filler_start=event_end,
                filler_end=epg_end,
                template=template,
                options=options,
            )
            programmes.extend(postgame_programmes)

        return programmes

    def _generate_filler_programmes(
        self,
        event: Event,
        channel_id: str,
        context,  # TemplateContext
        filler_type: str,  # "pregame" or "postgame"
        filler_start: datetime,
        filler_end: datetime,
        template: EventTemplateConfig,
        options: EventEPGOptions,
    ) -> list[Programme]:
        """Generate filler programmes spanning from start to end.

        Creates daily chunks to avoid single multi-day programmes.
        """
        programmes: list[Programme] = []

        # Don't generate if start >= end
        if filler_start >= filler_end:
            return programmes

        current_start = filler_start
        while current_start < filler_end:
            # Calculate end of this chunk (midnight or filler_end, whichever is first)
            next_midnight = (current_start + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            current_end = min(next_midnight, filler_end)

            # Get title/description based on filler type
            if filler_type == "pregame":
                title_template = template.pregame_title
                subtitle_template = template.pregame_subtitle
                desc_template = template.pregame_description
                icon_url = template.pregame_icon_url
            else:  # postgame
                title_template = template.postgame_title
                subtitle_template = template.postgame_subtitle
                desc_template = self._get_postgame_description(template, event)
                icon_url = template.postgame_icon_url

            # Resolve templates
            title = self._resolver.resolve(title_template, context)
            subtitle = self._resolver.resolve(subtitle_template, context) if subtitle_template else None
            description = self._resolver.resolve(desc_template, context) if desc_template else None
            icon = self._resolver.resolve(icon_url, context) if icon_url else None

            programme = Programme(
                channel_id=channel_id,
                title=title,
                start=current_start,
                stop=current_end,
                description=description,
                subtitle=subtitle,
                category=template.category,
                icon=icon or (event.home_team.logo_url if event.home_team else None),
            )
            programmes.append(programme)

            current_start = current_end

        return programmes

    def _get_postgame_description(
        self, template: EventTemplateConfig, event: Event
    ) -> str:
        """Get postgame description based on conditional logic.

        If postgame_conditional_enabled:
        - Use postgame_description_final for completed games
        - Use postgame_description_not_final for in-progress games
        """
        if not template.postgame_conditional_enabled:
            return template.postgame_description

        # Check if game is final
        is_final = event.status in ("final", "post", "STATUS_FINAL")

        if is_final:
            return template.postgame_description_final
        return template.postgame_description_not_final

    def _enrich_event_for_postgame(self, event: Event) -> Event:
        """Fetch fresh event data to get updated scores for postgame filler.

        Returns enriched event or original if enrichment fails.
        """
        try:
            fresh = self._service.get_event(event.id, event.league)
            if fresh:
                return fresh
        except Exception as e:
            logger.warning(f"Failed to enrich event {event.id} for postgame: {e}")
        return event

    def generate_for_leagues(
        self,
        leagues: list[str],
        target_date: date,
        channel_prefix: str = "event",
        options: EventEPGOptions | None = None,
    ) -> tuple[list[Programme], list[EventChannelInfo]]:
        """Generate EPG for all events in specified leagues.

        Args:
            leagues: League codes to fetch events from
            target_date: Date to fetch events for
            channel_prefix: Prefix for generated channel IDs
            options: Generation options

        Returns:
            Tuple of (programmes, channels)
        """
        options = options or EventEPGOptions()

        # Fetch events from all leagues
        all_events: list[Event] = []
        for league in leagues:
            events = self._service.get_events(league, target_date)
            all_events.extend(events)

        # Enrich if target is today/yesterday (need fresh status/scores)
        all_events = self._enrich_if_recent(all_events, target_date)

        programmes = []
        channels = []

        for event in all_events:
            channel_id = f"{channel_prefix}-{event.id}"

            # Build context using home team perspective
            context = self._context_builder.build_for_event(
                event=event,
                team_id=event.home_team.id,
                league=event.league,
            )

            # Generate channel name from template
            channel_name = self._resolver.resolve(
                options.template.channel_name_format, context
            )

            channel_info = EventChannelInfo(
                channel_id=channel_id,
                name=channel_name,
                event_id=event.id,
                league=event.league,
                icon=event.home_team.logo_url if event.home_team else None,
            )
            channels.append(channel_info)

            programme = self._event_to_programme(event, context, channel_id, options)
            programmes.append(programme)

        return programmes, channels

    def generate_for_event(
        self,
        event_id: str,
        league: str,
        channel_id: str,
        options: EventEPGOptions | None = None,
        stream_name: str | None = None,
    ) -> Programme | None:
        """Generate EPG for a specific event.

        Args:
            event_id: ESPN event ID
            league: League code
            channel_id: XMLTV channel ID
            options: Generation options
            stream_name: Optional stream name (for UFC prelim/main detection)

        Returns:
            Programme or None if event not found
        """
        options = options or EventEPGOptions()

        event = self._service.get_event(event_id, league)
        if not event:
            return None

        # Build context using home team perspective
        context = self._context_builder.build_for_event(
            event=event,
            team_id=event.home_team.id,
            league=league,
        )

        return self._event_to_programme(
            event, context, channel_id, options, stream_name
        )

    def generate_for_matched_streams(
        self,
        matched_streams: list[MatchedStream],
        options: EventEPGOptions | None = None,
        with_filler: bool = False,
        epg_start: datetime | None = None,
    ) -> tuple[list[Programme], list[EventChannelInfo]]:
        """Generate EPG for streams that have been matched to events.

        Args:
            matched_streams: Streams with their matched events
            options: Generation options
            with_filler: If True, include pregame/postgame filler programmes
            epg_start: EPG start datetime (for filler generation)

        Returns:
            Tuple of (programmes, channels)
        """
        options = options or EventEPGOptions()

        programmes = []
        channels = []

        for match in matched_streams:
            event = match.event

            # Build context for channel name
            context = self._context_builder.build_for_event(
                event=event,
                team_id=event.home_team.id,
                league=event.league,
                epg_timezone=options.epg_timezone,
            )

            # Generate channel name
            channel_name = self._resolver.resolve(
                options.template.channel_name_format, context
            )

            channel_info = EventChannelInfo(
                channel_id=match.channel_id,
                name=channel_name,
                event_id=event.id,
                league=event.league,
                icon=event.home_team.logo_url if event.home_team else None,
            )
            channels.append(channel_info)

            if with_filler:
                # Generate event with filler (pregame + event + postgame)
                event_programmes = self.generate_with_filler(
                    event=event,
                    channel_id=match.channel_id,
                    options=options,
                    stream_name=match.stream_name,
                    epg_start=epg_start,
                )
                programmes.extend(event_programmes)
            else:
                # Just the event programme
                programme = self._event_to_programme(
                    event, context, match.channel_id, options, match.stream_name
                )
                programmes.append(programme)

        return programmes, channels

    def _event_to_programme(
        self,
        event: Event,
        context,  # TemplateContext
        channel_id: str,
        options: EventEPGOptions,
        stream_name: str | None = None,
    ) -> Programme:
        """Convert an Event to a Programme with template resolution.

        Args:
            event: Event to convert
            context: Template context
            channel_id: XMLTV channel ID
            options: Generation options
            stream_name: Optional stream name (for UFC prelim/main detection)
        """
        # UFC/MMA events have special time handling
        if event.sport == "mma" and stream_name and event.main_card_start:
            start, stop = self._get_ufc_programme_times(
                event, stream_name, options.sport_durations, options.default_duration_hours
            )
            start = start - timedelta(minutes=options.pregame_minutes)
        else:
            # Standard handling
            start = event.start_time - timedelta(minutes=options.pregame_minutes)
            duration = get_sport_duration(
                event.sport, options.sport_durations, options.default_duration_hours
            )
            stop = event.start_time + timedelta(hours=duration)

        # Resolve templates
        title = self._resolver.resolve(options.template.title_format, context)
        description = self._resolver.resolve(options.template.description_format, context)
        subtitle = self._resolver.resolve(options.template.subtitle_format, context)

        return Programme(
            channel_id=channel_id,
            title=title,
            start=start,
            stop=stop,
            description=description,
            subtitle=subtitle,
            category=options.template.category,
            icon=event.home_team.logo_url if event.home_team else None,
        )

    def _get_ufc_programme_times(
        self,
        event: Event,
        stream_name: str,
        sport_durations: dict[str, float],
        default_duration: float,
    ) -> tuple[datetime, datetime]:
        """Get start/end times for UFC events based on stream type.

        Detects prelims vs main card from stream name.
        """
        stream_lower = stream_name.lower()
        mma_duration = sport_durations.get("mma", default_duration)

        if "prelim" in stream_lower and event.main_card_start:
            # Prelims only: event start → main card start
            return event.start_time, event.main_card_start
        elif "main" in stream_lower and event.main_card_start:
            # Main card only
            main_duration = timedelta(hours=mma_duration / 2)
            return event.main_card_start, event.main_card_start + main_duration
        else:
            # Full event
            return event.start_time, event.start_time + timedelta(hours=mma_duration)

    def _enrich_if_recent(
        self, events: list[Event], target_date: date
    ) -> list[Event]:
        """Fetch fresh data for events if target is today/yesterday."""
        today = now_user().date()
        yesterday = today - timedelta(days=1)

        if target_date not in (today, yesterday):
            return events

        enriched = []
        for event in events:
            fresh = self._service.get_event(event.id, event.league)
            if fresh:
                enriched.append(fresh)
            else:
                enriched.append(event)

        return enriched
