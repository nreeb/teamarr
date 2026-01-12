# V1 to V2 Migration Analysis

> **Status**: Analysis complete. Leaning towards **no migration** - fresh setup recommended.

## Table Mapping

| V1 Table | V2 Table | Migration Complexity | Notes |
|----------|----------|---------------------|-------|
| `templates` | `templates` | **MEDIUM** | Structure changed - JSON consolidation |
| `teams` | `teams` | **HIGH** | Provider-agnostic redesign |
| `settings` | `settings` | **MEDIUM** | Many columns renamed/restructured |
| `event_epg_groups` | `event_epg_groups` | **HIGH** | Major architectural changes |
| `managed_channels` | `managed_channels` | **MEDIUM** | Similar structure, some renames |
| `managed_channel_streams` | `managed_channel_streams` | **LOW** | Nearly identical |
| `managed_channel_history` | `managed_channel_history` | **LOW** | Similar structure |
| `team_aliases` | `team_aliases` | **LOW** | Added `provider` column |
| `stream_match_cache` | `stream_match_cache` | **MEDIUM** | Added `match_method`, `user_corrected` |
| `consolidation_exception_keywords` | `consolidation_exception_keywords` | **LOW** | Added `display_name`, `enabled` |
| `condition_presets` | `condition_presets` | **MEDIUM** | Complete restructure to JSON |
| `league_config` + `league_id_aliases` | `leagues` | **HIGH** | Merged + completely redesigned |
| `epg_history` | `processing_runs` | **HIGH** | Different architecture |
| `epg_matched_streams` | `epg_matched_streams` | **MEDIUM** | Column renames |
| `epg_failed_matches` | `epg_failed_matches` | **MEDIUM** | Column renames |
| `soccer_team_leagues` | `team_cache` | **HIGH** | Unified multi-provider cache |
| `team_league_cache` | `team_cache` | **HIGH** | Merged into unified cache |
| `soccer_leagues_cache` | `league_cache` | **HIGH** | Unified multi-provider cache |
| `schedule_cache` | `service_cache` | **N/A** | Different caching approach |
| `team_stats_cache` | N/A | **N/A** | Not in V2 (removed) |
| `h2h_cache` | N/A | **N/A** | Not in V2 (removed) |
| `error_log` | N/A | **N/A** | Not in V2 (uses logging) |

## Key Transformations Required

### 1. Templates (MEDIUM)

```
V1: pregame_title, pregame_subtitle, pregame_description, pregame_art_url (separate columns)
V2: pregame_fallback JSON {"title": ..., "subtitle": ..., "description": ..., "art_url": ...}

V1: postgame_conditional_enabled, postgame_description_final, postgame_description_not_final
V2: postgame_conditional JSON {"enabled": ..., "description_final": ..., "description_not_final": ...}

V1: flags JSON {"new": true, "live": false, "date": false}
V2: xmltv_flags JSON (same structure)

V1: description_options JSON
V2: conditional_descriptions JSON (rename)

V1: channel_name, channel_logo_url (event templates)
V2: event_channel_name, event_channel_logo_url (renamed)
```

### 2. Teams (HIGH)

```
V1: espn_team_id → V2: provider_team_id (+ provider='espn')
V1: league → V2: primary_league
V1: (no leagues array) → V2: leagues JSON array
V1: team_slug → DROPPED (not in V2)
```

### 3. Settings (MEDIUM)

```
V1: epg_days_ahead → V2: epg_output_days_ahead
V1: game_duration_* → V2: duration_*
V1: default_timezone → V2: epg_timezone
V1: default_channel_id_format → V2: channel_id_format
V1: web_port, web_host → DROPPED
V1: log_level → DROPPED
V1: auto_generate_enabled, auto_generate_frequency, schedule_time → DROPPED (only cron_expression)
```

### 4. Event EPG Groups (HIGH)

```
V1: dispatcharr_group_id, dispatcharr_account_id, group_name, account_name
V2: m3u_group_id, m3u_account_id, name, m3u_account_name

V1: assigned_league, assigned_sport
V2: leagues JSON (array instead of single)

V1: is_multi_sport, enabled_leagues
V2: DROPPED (handled by leagues array)

V1: channel_start → V2: channel_start_number
V1: channel_profile_id, channel_profile_ids → V2: channel_profile_ids (consolidated)
```

### 5. Leagues (HIGH - Most Complex)

```
V1: league_config + league_id_aliases tables
V2: Single leagues table with all config

Mapping:
  V1 league_config.league_code → V2 leagues.league_code
  V1 league_config.league_name → V2 leagues.display_name
  V1 league_config.sport → V2 leagues.sport
  V1 league_config.api_path → V2 leagues.provider_league_id (partial)
  V1 league_id_aliases.alias → V2 leagues.league_id
```

## Tables That CANNOT Be Migrated

1. **schedule_cache** - V1 caches raw ESPN responses, V2 uses service_cache with different structure
2. **team_stats_cache** - Removed in V2 (simplified)
3. **h2h_cache** - Removed in V2 (simplified)
4. **error_log** - V2 uses Python logging instead
5. **soccer_cache_meta, team_league_cache_meta** - Merged into cache_meta

## Migration Feasibility Assessment

| Component | Feasibility | Effort |
|-----------|-------------|--------|
| Templates | **HIGH** - Transform columns to JSON | 2-3 hours |
| Teams | **HIGH** - Add provider fields | 1-2 hours |
| Settings | **MEDIUM** - Rename + drop obsolete | 1 hour |
| Event Groups | **MEDIUM** - Significant restructure | 2-3 hours |
| Team Aliases | **HIGH** - Add provider column | 30 min |
| Stream Match Cache | **MEDIUM** - Add new columns | 1 hour |
| Managed Channels | **MEDIUM** - Column renames | 1 hour |
| Channel Streams/History | **HIGH** - Nearly identical | 30 min |
| Leagues | **LOW** - Complete rebuild needed | N/A (just use V2 seed) |
| Cache tables | **LOW** - Regenerated on startup | N/A |
| Stats/History | **MEDIUM** - Schema differs | 1-2 hours |

## Recommendation

Migration **IS technically feasible** but has significant complexity:

### What CAN be migrated (with transformation logic):
- Templates
- Teams
- Settings
- Event Groups
- Team Aliases
- Stream Match Cache
- Managed Channels/Streams/History

### What should NOT be migrated:
- **Cache data** (team_cache, league_cache, service_cache) - Regenerated on startup
- **Leagues config** - V2 has completely redesigned leagues table with HockeyTech, TSDB, Cricbuzz support that V1 lacks

### What's OPTIONAL:
- **Historical data** (processing_runs, matched_streams, failed_matches) - Can skip if user doesn't need history

## Why Skip Migration?

1. **V2 is a rewrite, not an upgrade** - Different architectural decisions
2. **Leagues are completely different** - V2 has multi-provider support (ESPN, TSDB, HockeyTech, Cricbuzz)
3. **Most valuable data is templates** - Users can export/import templates via UI
4. **Cache regenerates automatically** - No data loss for team/league cache
5. **Event groups need reconfiguration anyway** - V2's `leagues` array vs V1's `assigned_league` is fundamentally different
6. **Migration script maintenance burden** - Edge cases, testing, ongoing support

## If Migration Is Needed Later

A migration script would need to:

```python
def migrate_v1_to_v2(v1_db_path: str, v2_db_path: str):
    """Migrate V1 database to V2 schema."""

    # 1. Create fresh V2 database with schema
    # 2. Migrate templates (transform JSON structure)
    # 3. Migrate teams (add provider='espn', restructure leagues)
    # 4. Migrate settings (column mapping)
    # 5. Migrate event_epg_groups (column mapping + JSON arrays)
    # 6. Migrate team_aliases (add provider column)
    # 7. Migrate stream_match_cache (add new columns with defaults)
    # 8. Migrate managed_channels/streams/history
    # 9. Skip: all cache tables (regenerate on startup)
    # 10. Optional: migrate processing_runs/stats
```

Estimated effort: **8-12 hours** including testing.

## Conclusion

**Recommend skipping migration** and documenting that V2 requires fresh setup. The template export/import feature allows users to preserve their most valuable configuration.
