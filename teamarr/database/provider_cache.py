"""Serialization helpers for caching dataclass objects.

Used by SportsDataService to serialize Event, Team, TeamStats to/from
JSON for storage in PersistentTTLCache (SQLite-backed).
"""

from datetime import datetime

from teamarr.core import Event, EventStatus, Team, TeamStats, Venue


def event_to_dict(event: Event) -> dict:
    """Serialize Event to dict for JSON storage."""
    return {
        "id": event.id,
        "provider": event.provider,
        "name": event.name,
        "short_name": event.short_name,
        "start_time": event.start_time.isoformat(),
        "home_team": team_to_dict(event.home_team),
        "away_team": team_to_dict(event.away_team),
        "status": {
            "state": event.status.state,
            "detail": event.status.detail,
            "period": event.status.period,
            "clock": event.status.clock,
        },
        "league": event.league,
        "sport": event.sport,
        "home_score": event.home_score,
        "away_score": event.away_score,
        "venue": venue_to_dict(event.venue) if event.venue else None,
        "broadcasts": event.broadcasts,
        "season_year": event.season_year,
        "season_type": event.season_type,
    }


def team_to_dict(team: Team) -> dict:
    """Serialize Team to dict."""
    return {
        "id": team.id,
        "provider": team.provider,
        "name": team.name,
        "short_name": team.short_name,
        "abbreviation": team.abbreviation,
        "league": team.league,
        "sport": team.sport,
        "logo_url": team.logo_url,
        "color": team.color,
    }


def venue_to_dict(venue: Venue) -> dict:
    """Serialize Venue to dict."""
    return {
        "name": venue.name,
        "city": venue.city,
        "state": venue.state,
        "country": venue.country,
    }


def dict_to_event(data: dict) -> Event:
    """Deserialize dict to Event."""
    return Event(
        id=data["id"],
        provider=data["provider"],
        name=data["name"],
        short_name=data["short_name"],
        start_time=datetime.fromisoformat(data["start_time"]),
        home_team=dict_to_team(data["home_team"]),
        away_team=dict_to_team(data["away_team"]),
        status=EventStatus(
            state=data["status"]["state"],
            detail=data["status"].get("detail"),
            period=data["status"].get("period"),
            clock=data["status"].get("clock"),
        ),
        league=data["league"],
        sport=data["sport"],
        home_score=data.get("home_score"),
        away_score=data.get("away_score"),
        venue=dict_to_venue(data["venue"]) if data.get("venue") else None,
        broadcasts=data.get("broadcasts", []),
        season_year=data.get("season_year"),
        season_type=data.get("season_type"),
    )


def dict_to_team(data: dict) -> Team:
    """Deserialize dict to Team."""
    return Team(
        id=data["id"],
        provider=data["provider"],
        name=data["name"],
        short_name=data["short_name"],
        abbreviation=data["abbreviation"],
        league=data["league"],
        sport=data["sport"],
        logo_url=data.get("logo_url"),
        color=data.get("color"),
    )


def dict_to_venue(data: dict) -> Venue:
    """Deserialize dict to Venue."""
    return Venue(
        name=data["name"],
        city=data.get("city"),
        state=data.get("state"),
        country=data.get("country"),
    )


def stats_to_dict(stats: TeamStats) -> dict:
    """Serialize TeamStats to dict."""
    return {
        "record": stats.record,
        "wins": stats.wins,
        "losses": stats.losses,
        "ties": stats.ties,
        "home_record": stats.home_record,
        "away_record": stats.away_record,
        "streak": stats.streak,
        "streak_count": stats.streak_count,
        "rank": stats.rank,
        "playoff_seed": stats.playoff_seed,
        "games_back": stats.games_back,
        "conference": stats.conference,
        "conference_abbrev": stats.conference_abbrev,
        "division": stats.division,
        "ppg": stats.ppg,
        "papg": stats.papg,
    }


def dict_to_stats(data: dict) -> TeamStats:
    """Deserialize dict to TeamStats."""
    return TeamStats(
        record=data["record"],
        wins=data.get("wins", 0),
        losses=data.get("losses", 0),
        ties=data.get("ties", 0),
        home_record=data.get("home_record"),
        away_record=data.get("away_record"),
        streak=data.get("streak"),
        streak_count=data.get("streak_count", 0),
        rank=data.get("rank"),
        playoff_seed=data.get("playoff_seed"),
        games_back=data.get("games_back"),
        conference=data.get("conference"),
        conference_abbrev=data.get("conference_abbrev"),
        division=data.get("division"),
        ppg=data.get("ppg"),
        papg=data.get("papg"),
    )
