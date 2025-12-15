"""Database layer."""

from teamarr.database.connection import get_connection, get_db, init_db, reset_db
from teamarr.database.leagues import (
    LeagueMapping,
    get_league_mapping,
    get_leagues_for_provider,
    provider_supports_league,
)
from teamarr.database.settings import (
    AllSettings,
    DispatcharrSettings,
    DurationSettings,
    EPGSettings,
    LifecycleSettings,
    ReconciliationSettings,
    SchedulerSettings,
    get_all_settings,
    get_dispatcharr_settings,
    get_epg_settings,
    get_lifecycle_settings,
    get_scheduler_settings,
)

__all__ = [
    # Connection
    "get_connection",
    "get_db",
    "init_db",
    "reset_db",
    # Leagues
    "LeagueMapping",
    "get_league_mapping",
    "get_leagues_for_provider",
    "provider_supports_league",
    # Settings
    "AllSettings",
    "DispatcharrSettings",
    "DurationSettings",
    "EPGSettings",
    "LifecycleSettings",
    "ReconciliationSettings",
    "SchedulerSettings",
    "get_all_settings",
    "get_dispatcharr_settings",
    "get_epg_settings",
    "get_lifecycle_settings",
    "get_scheduler_settings",
]
