import { useState, useEffect, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Plus, Trash2, Download, Upload, Search, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import {
  useAliases,
  useCreateAlias,
  useDeleteAlias,
  exportAliases,
  useImportAliases,
} from "@/api/aliases"
import { getLeagues, getLeagueTeams } from "@/api/teams"
import type { TeamAliasCreate } from "@/api/types"
import type { CachedLeague } from "@/api/teams"

export function TeamAliases() {
  const [leagueFilter, setLeagueFilter] = useState<string>("")
  const [searchQuery, setSearchQuery] = useState("")
  const [isCreateOpen, setIsCreateOpen] = useState(false)

  // Form state for create dialog
  const [aliasText, setAliasText] = useState("")
  const [selectedLeague, setSelectedLeague] = useState("")
  const [selectedTeamId, setSelectedTeamId] = useState("")
  const [teamSearchQuery, setTeamSearchQuery] = useState("")

  const { data, isLoading } = useAliases(leagueFilter || undefined)
  const createMutation = useCreateAlias()
  const deleteMutation = useDeleteAlias()
  const importMutation = useImportAliases()

  // Fetch all leagues for dropdown
  const { data: leaguesData, isLoading: leaguesLoading } = useQuery({
    queryKey: ["cache", "leagues"],
    queryFn: () => getLeagues(false),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Fetch teams for selected league
  const { data: teamsData, isLoading: teamsLoading } = useQuery({
    queryKey: ["cache", "leagues", selectedLeague, "teams"],
    queryFn: () => getLeagueTeams(selectedLeague),
    enabled: !!selectedLeague,
    staleTime: 5 * 60 * 1000,
  })

  // Sort leagues by sport then name
  const sortedLeagues = useMemo(() => {
    if (!leaguesData?.leagues) return []
    return [...leaguesData.leagues].sort((a, b) => {
      const sportCompare = a.sport.localeCompare(b.sport)
      if (sportCompare !== 0) return sportCompare
      return a.name.localeCompare(b.name)
    })
  }, [leaguesData?.leagues])

  // Group leagues by sport for display
  const leaguesBySport = useMemo(() => {
    const grouped: Record<string, CachedLeague[]> = {}
    for (const league of sortedLeagues) {
      if (!grouped[league.sport]) grouped[league.sport] = []
      grouped[league.sport].push(league)
    }
    return grouped
  }, [sortedLeagues])

  // Filter teams by search query
  const filteredTeams = useMemo(() => {
    if (!teamsData) return []
    if (!teamSearchQuery) return teamsData
    const query = teamSearchQuery.toLowerCase()
    return teamsData.filter(
      (t) =>
        t.team_name.toLowerCase().includes(query) ||
        t.team_abbrev?.toLowerCase().includes(query) ||
        t.team_short_name?.toLowerCase().includes(query)
    )
  }, [teamsData, teamSearchQuery])

  // Get selected team object
  const selectedTeam = useMemo(() => {
    if (!selectedTeamId || !teamsData) return null
    return teamsData.find((t) => t.provider_team_id === selectedTeamId) || null
  }, [selectedTeamId, teamsData])

  // Get unique leagues for filter dropdown (from existing aliases)
  const existingLeagues = [...new Set(data?.aliases.map((a) => a.league) || [])]

  // Filter aliases by search query
  const filteredAliases = (data?.aliases || []).filter((alias) => {
    const query = searchQuery.toLowerCase()
    return (
      alias.alias.toLowerCase().includes(query) ||
      alias.team_name.toLowerCase().includes(query) ||
      alias.league.toLowerCase().includes(query)
    )
  })

  // Reset form when dialog closes
  useEffect(() => {
    if (!isCreateOpen) {
      setAliasText("")
      setSelectedLeague("")
      setSelectedTeamId("")
      setTeamSearchQuery("")
    }
  }, [isCreateOpen])

  // Clear team selection when league changes
  useEffect(() => {
    setSelectedTeamId("")
    setTeamSearchQuery("")
  }, [selectedLeague])

  const handleCreate = async () => {
    if (!selectedTeam || !selectedLeague || !aliasText) return

    const newAlias: TeamAliasCreate = {
      alias: aliasText.toLowerCase().trim(),
      league: selectedLeague,
      team_id: selectedTeam.provider_team_id,
      team_name: selectedTeam.team_name,
      provider: selectedTeam.provider,
    }

    try {
      await createMutation.mutateAsync(newAlias)
      setIsCreateOpen(false)
    } catch {
      // Error shown by mutation
    }
  }

  const handleExport = async () => {
    try {
      const aliases = await exportAliases()
      const blob = new Blob([JSON.stringify(aliases, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "team_aliases.json"
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error("Export failed:", e)
    }
  }

  const handleImport = () => {
    const input = document.createElement("input")
    input.type = "file"
    input.accept = ".json"
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      try {
        const text = await file.text()
        const aliases = JSON.parse(text)
        await importMutation.mutateAsync(aliases)
      } catch (e) {
        console.error("Import failed:", e)
      }
    }
    input.click()
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Team Aliases</h1>
          <p className="text-muted-foreground">
            Define custom name mappings for stream matching
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button variant="outline" onClick={handleImport}>
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Alias
          </Button>
        </div>
      </div>

      {/* Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent onClose={() => setIsCreateOpen(false)} className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Team Alias</DialogTitle>
            <DialogDescription>
              Map a stream name to a team for better matching
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Alias Text */}
            <div className="space-y-2">
              <Label htmlFor="alias">Alias Text *</Label>
              <Input
                id="alias"
                value={aliasText}
                onChange={(e) => setAliasText(e.target.value)}
                placeholder="e.g., Spurs, Man U, NYG"
              />
              <p className="text-xs text-muted-foreground">
                The text that appears in stream names (case-insensitive)
              </p>
            </div>

            {/* League Dropdown */}
            <div className="space-y-2">
              <Label htmlFor="league">League *</Label>
              {leaguesLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading leagues...
                </div>
              ) : (
                <Select
                  id="league"
                  value={selectedLeague}
                  onChange={(e) => setSelectedLeague(e.target.value)}
                >
                  <option value="">Select a league...</option>
                  {Object.entries(leaguesBySport).map(([sport, leagues]) => (
                    <optgroup key={sport} label={sport}>
                      {leagues.map((league) => (
                        <option key={league.slug} value={league.slug}>
                          {league.name} ({league.team_count} teams)
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </Select>
              )}
            </div>

            {/* Team Dropdown */}
            <div className="space-y-2">
              <Label htmlFor="team">Team *</Label>
              {!selectedLeague ? (
                <p className="text-sm text-muted-foreground py-2">
                  Select a league first
                </p>
              ) : teamsLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading teams...
                </div>
              ) : (
                <>
                  {/* Team search filter */}
                  <div className="relative mb-2">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search teams..."
                      className="pl-10"
                      value={teamSearchQuery}
                      onChange={(e) => setTeamSearchQuery(e.target.value)}
                    />
                  </div>
                  <Select
                    id="team"
                    value={selectedTeamId}
                    onChange={(e) => setSelectedTeamId(e.target.value)}
                    className="max-h-60"
                  >
                    <option value="">Select a team...</option>
                    {filteredTeams.map((team) => (
                      <option key={team.provider_team_id} value={team.provider_team_id}>
                        {team.team_name}
                        {team.team_abbrev ? ` (${team.team_abbrev})` : ""}
                      </option>
                    ))}
                  </Select>
                  {filteredTeams.length === 0 && teamSearchQuery && (
                    <p className="text-xs text-muted-foreground">
                      No teams match "{teamSearchQuery}"
                    </p>
                  )}
                </>
              )}
            </div>

            {/* Selected team preview */}
            {selectedTeam && (
              <div className="bg-muted p-3 rounded-md space-y-1">
                <p className="text-sm font-medium">Selected Team</p>
                <div className="flex items-center gap-3">
                  {selectedTeam.logo_url && (
                    <img
                      src={selectedTeam.logo_url}
                      alt=""
                      className="h-8 w-8 object-contain"
                    />
                  )}
                  <div className="text-sm">
                    <p className="font-medium">{selectedTeam.team_name}</p>
                    <p className="text-muted-foreground">
                      {selectedTeam.provider.toUpperCase()} ID: {selectedTeam.provider_team_id}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={
                !aliasText.trim() ||
                !selectedLeague ||
                !selectedTeamId ||
                createMutation.isPending
              }
            >
              {createMutation.isPending ? "Creating..." : "Create Alias"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Card>
        <CardHeader>
          <CardTitle>Aliases ({filteredAliases.length})</CardTitle>
          <CardDescription>
            Aliases are checked before fuzzy matching for higher precision
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search aliases..."
                className="pl-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Select
              className="w-48"
              value={leagueFilter}
              onChange={(e) => setLeagueFilter(e.target.value)}
            >
              <option value="">All Leagues</option>
              {existingLeagues.map((league) => (
                <option key={league} value={league}>
                  {league}
                </option>
              ))}
            </Select>
          </div>

          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : filteredAliases.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery || leagueFilter ? "No aliases match your filters" : "No aliases defined yet"}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Alias</TableHead>
                  <TableHead>League</TableHead>
                  <TableHead>Team Name</TableHead>
                  <TableHead>Team ID</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead className="w-16"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAliases.map((alias) => (
                  <TableRow key={alias.id}>
                    <TableCell className="font-medium">{alias.alias}</TableCell>
                    <TableCell>
                      <code className="bg-muted px-1 py-0.5 rounded text-sm">{alias.league}</code>
                    </TableCell>
                    <TableCell>{alias.team_name}</TableCell>
                    <TableCell className="font-mono text-sm">{alias.team_id}</TableCell>
                    <TableCell className="capitalize">{alias.provider}</TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteMutation.mutate(alias.id)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>How It Works</CardTitle>
        </CardHeader>
        <CardContent className="prose prose-sm dark:prose-invert max-w-none">
          <p>
            Team aliases help with stream matching when automatic fuzzy matching fails.
            Common use cases:
          </p>
          <ul>
            <li>
              <strong>Nicknames:</strong> "Spurs" → "Tottenham Hotspur" (EPL) or "San Antonio Spurs" (NBA)
            </li>
            <li>
              <strong>Abbreviations:</strong> "Man U" → "Manchester United"
            </li>
            <li>
              <strong>Local Names:</strong> "NYG" → "New York Giants"
            </li>
          </ul>
          <p>
            Aliases are league-specific so "Spurs" can map to different teams in different leagues.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
