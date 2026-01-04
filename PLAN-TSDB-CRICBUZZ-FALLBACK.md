# Plan: TSDB Premium / Cricbuzz Fallback for Cricket

## Goal

Implement a provider fallback system for cricket leagues:
- **Option A (TSDB Premium)**: TSDB handles everything (teams, logos, schedules, scores)
- **Option B (No Premium)**: TSDB for teams/logos, Cricbuzz for schedules/scores

## Current State

- Cricket leagues configured as `provider=cricbuzz` in schema
- Cricbuzz extracts teams from schedule (no teams when out of season)
- Cricbuzz team data has no logos (imageId not in schedule response)
- TSDB free tier: team endpoints work, schedule limited to ~5 events/day
- TSDB premium: no limits

## Architecture Principles

### Layer Separation (MUST respect)

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                 │
│  (No changes needed - uses service layer)                       │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│                      Service Layer                               │
│  SportsDataService - ADD fallback resolution here               │
│  - Checks league config for fallback_provider                   │
│  - Checks if primary provider is "fully available"              │
│  - Routes to appropriate provider                               │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│                      Provider Layer                              │
│  - Each provider is INDEPENDENT (no cross-provider logic)       │
│  - TSDBProvider.is_premium_available() - NEW method             │
│  - ProviderRegistry exposes premium status check                │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principle: Providers Don't Know About Each Other

- TSDBProvider knows nothing about Cricbuzz
- CricbuzzProvider knows nothing about TSDB
- Fallback logic lives in SERVICE layer, not provider layer

## Implementation Steps

### Phase 1: Schema Changes

**File: `teamarr/database/schema.sql`**

1. Add columns to leagues table:
   ```sql
   fallback_provider TEXT,      -- e.g., 'cricbuzz'
   fallback_league_id TEXT,     -- e.g., '9241/indian-premier-league-2026'
   ```

2. Update cricket leagues configuration:
   ```sql
   -- Cricket: TSDB primary (when premium), Cricbuzz fallback
   ('ipl', 'tsdb', '4460', 'Indian Premier League', ..., 'cricbuzz', '9241/indian-premier-league-2026'),
   ('bbl', 'tsdb', '4461', 'Big Bash League', ..., 'cricbuzz', '10289/big-bash-league-2025-26'),
   ('bpl', 'tsdb', '5529', 'Bangladesh Premier League', ..., 'cricbuzz', '11328/bpl-2025-26'),
   ('sa20', 'tsdb', '5532', 'SA20', ..., 'cricbuzz', '10394/sa20-2025-26'),
   ```

**File: `teamarr/database/connection.py`**

3. Add pre-migration for new columns:
   ```python
   def _add_fallback_columns_if_needed(conn):
       # Add fallback_provider and fallback_league_id columns
   ```

### Phase 2: Provider Layer Changes

**File: `teamarr/providers/tsdb/client.py`**

Already has `is_premium` property - no changes needed.

**File: `teamarr/providers/registry.py`**

4. Add method to check provider premium status:
   ```python
   @classmethod
   def is_provider_premium(cls, name: str) -> bool:
       """Check if provider has premium/full capabilities."""
       provider = cls.get(name)
       if provider and hasattr(provider, 'is_premium'):
           return provider.is_premium
       return True  # Assume full capability if no is_premium method
   ```

### Phase 3: Core Types (Interface)

**File: `teamarr/core/interfaces.py`**

5. Add LeagueMapping fields for fallback:
   ```python
   @dataclass
   class LeagueMapping:
       league_code: str
       provider: str
       provider_league_id: str
       # ... existing fields ...
       fallback_provider: str | None = None
       fallback_league_id: str | None = None
   ```

### Phase 4: League Mapping Source

**File: `teamarr/database/leagues.py`** (or wherever LeagueMappingSource is)

6. Update to load fallback fields from database
7. Add method to resolve effective provider:
   ```python
   def get_effective_provider(self, league_code: str) -> tuple[str, str]:
       """Get (provider, league_id) considering fallbacks.

       Returns primary if available, else fallback.
       """
       mapping = self.get_mapping(league_code)
       if not mapping:
           return None, None

       # Check if primary provider is fully available
       if mapping.provider == 'tsdb':
           from teamarr.providers import ProviderRegistry
           if not ProviderRegistry.is_provider_premium('tsdb'):
               # Use fallback if available
               if mapping.fallback_provider and mapping.fallback_league_id:
                   return mapping.fallback_provider, mapping.fallback_league_id

       return mapping.provider, mapping.provider_league_id
   ```

### Phase 5: Service Layer

**File: `teamarr/services/sports_data.py`**

8. Update SportsDataService to use effective provider:
   ```python
   def get_events(self, league: str, date: date) -> list[Event]:
       # Get effective provider (considers fallbacks)
       provider_name, league_id = self._league_mapping.get_effective_provider(league)
       provider = ProviderRegistry.get(provider_name)
       # ... rest of method
   ```

### Phase 6: Cache Refresh (Team Data)

**File: `teamarr/consumers/cache/refresh.py`**

9. For cricket leagues, ALWAYS fetch team data from TSDB:
   ```python
   def _discover_from_provider(self, provider, ...):
       # Existing logic...

       # Special handling: For cricket leagues using Cricbuzz for schedules,
       # still fetch team data from TSDB (has logos, works year-round)
       if provider.name == 'cricbuzz':
           teams = self._enrich_cricket_teams_from_tsdb(leagues, teams)

   def _enrich_cricket_teams_from_tsdb(self, leagues, cricbuzz_teams):
       """Fetch team data from TSDB for cricket leagues.

       TSDB has complete team rosters with logos even in off-season.
       Cricbuzz only has teams that appear in scheduled matches.
       """
       tsdb = ProviderRegistry.get('tsdb')
       # For each cricket league, fetch teams from TSDB
       # Merge with/replace cricbuzz teams
   ```

### Phase 7: Cricbuzz Auto-Discovery Update

**File: `teamarr/consumers/cache/refresh.py`**

10. Update `_update_cricbuzz_series_ids()` to update fallback_league_id:
    ```python
    # When discovering new Cricbuzz series IDs, update fallback_league_id
    # (since cricket leagues now have provider=tsdb, fallback_provider=cricbuzz)
    ```

## Data Flow Examples

### Example 1: Get IPL Schedule (No TSDB Premium)

```
1. API calls GET /events?league=ipl
2. SportsDataService.get_events('ipl', date)
3. LeagueMappingSource.get_effective_provider('ipl')
   - Primary: tsdb (but ProviderRegistry.is_provider_premium('tsdb') = False)
   - Fallback: cricbuzz
   - Returns: ('cricbuzz', '9241/indian-premier-league-2026')
4. ProviderRegistry.get('cricbuzz')
5. CricbuzzProvider.get_events('9241/indian-premier-league-2026', date)
6. Return events
```

### Example 2: Get IPL Schedule (TSDB Premium)

```
1. API calls GET /events?league=ipl
2. SportsDataService.get_events('ipl', date)
3. LeagueMappingSource.get_effective_provider('ipl')
   - Primary: tsdb (ProviderRegistry.is_provider_premium('tsdb') = True)
   - Returns: ('tsdb', '4460')
4. ProviderRegistry.get('tsdb')
5. TSDBProvider.get_events('4460', date)
6. Return events
```

### Example 3: Cache Refresh (Teams)

```
1. CacheRefresher.refresh()
2. For cricbuzz provider:
   - Fetch teams from schedules (may be incomplete)
   - Call _enrich_cricket_teams_from_tsdb()
   - TSDB returns complete team list with logos
   - Merge: TSDB teams replace/supplement Cricbuzz teams
3. Save to team_cache with TSDB logo URLs
```

## Files Modified (Summary)

| File | Changes |
|------|---------|
| `teamarr/database/schema.sql` | Add fallback columns, update cricket leagues |
| `teamarr/database/connection.py` | Add pre-migration for fallback columns |
| `teamarr/core/interfaces.py` | Add fallback fields to LeagueMapping |
| `teamarr/providers/registry.py` | Add is_provider_premium() method |
| `teamarr/database/leagues.py` | Add get_effective_provider(), load fallback fields |
| `teamarr/services/sports_data.py` | Use effective provider for routing |
| `teamarr/consumers/cache/refresh.py` | Add TSDB team enrichment for cricket |

## Testing Plan

1. **No TSDB key**: Verify cricket uses Cricbuzz for schedules
2. **TSDB premium key**: Verify cricket uses TSDB for everything
3. **Team cache**: Verify cricket teams have TSDB logos regardless of key
4. **Off-season**: Verify IPL teams appear (from TSDB) even when Cricbuzz returns 0
5. **Auto-discovery**: Verify Cricbuzz series IDs update in fallback_league_id

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| TSDB team IDs don't match Cricbuzz | Match by team name, not ID |
| TSDB rate limiting on free tier | Team endpoints aren't rate limited |
| Breaking existing cricket configs | Pre-migration handles gracefully |

## Rollback Plan

If issues arise:
1. Revert cricket leagues to `provider=cricbuzz` (no fallback)
2. Remove fallback resolution logic
3. Teams won't have logos until next cache refresh with TSDB

---

## Checkpoint

After implementing each phase, verify:
- [ ] Phase 1: Schema migration runs, cricket leagues have fallback config
- [ ] Phase 2: ProviderRegistry.is_provider_premium() works
- [ ] Phase 3: LeagueMapping dataclass has fallback fields
- [ ] Phase 4: get_effective_provider() returns correct provider based on premium status
- [ ] Phase 5: SportsDataService routes to correct provider
- [ ] Phase 6: Cricket teams in cache have TSDB logos
- [ ] Phase 7: Auto-discovery updates fallback_league_id
