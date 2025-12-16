import { useQuery } from "@tanstack/react-query"
import { api, checkHealth } from "@/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Users,
  Calendar,
  Tv,
  FileText,
  RefreshCw,
  Rocket,
  Database,
  Clock,
} from "lucide-react"
import { toast } from "sonner"

interface Stats {
  overall: {
    total_teams: number
    total_event_groups: number
    total_templates: number
    total_managed_channels: number
  }
  streams: {
    total_cached: number
    cache_hit_rate: number
  }
  programmes: {
    total_generated: number
  }
  last_24h: {
    runs: number
    programmes_generated: number
  }
}

interface CacheStatus {
  leagues: { count: number; last_refresh: string | null }
  teams: { count: number; last_refresh: string | null }
}

export function Dashboard() {
  // Health check
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: checkHealth,
    refetchInterval: 30000,
  })

  // Stats
  const statsQuery = useQuery({
    queryKey: ["stats"],
    queryFn: () => api.get<Stats>("/stats"),
  })

  // Cache status
  const cacheQuery = useQuery({
    queryKey: ["cache-status"],
    queryFn: () => api.get<CacheStatus>("/cache/status"),
  })

  const handleRefreshCache = async () => {
    toast.loading("Refreshing cache...", { id: "cache-refresh" })
    try {
      await api.post("/cache/refresh")
      toast.success("Cache refreshed", { id: "cache-refresh" })
      cacheQuery.refetch()
    } catch (err) {
      toast.error("Failed to refresh cache", { id: "cache-refresh" })
    }
  }

  const handleGenerateEPG = async () => {
    toast.loading("Generating EPG...", { id: "epg-generate" })
    try {
      const result = await api.post<{ programmes_count: number }>("/epg/generate")
      toast.success(`Generated ${result.programmes_count} programmes`, {
        id: "epg-generate",
      })
      statsQuery.refetch()
    } catch (err) {
      toast.error("EPG generation failed", { id: "epg-generate" })
    }
  }

  const stats = statsQuery.data?.overall
  const cache = cacheQuery.data

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your EPG system
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={handleRefreshCache}>
            <RefreshCw className="h-4 w-4" />
            Refresh Cache
          </Button>
          <Button variant="success" size="sm" onClick={handleGenerateEPG}>
            <Rocket className="h-4 w-4" />
            Generate EPG
          </Button>
        </div>
      </div>

      {/* Status indicator */}
      <div className="flex items-center gap-2 text-sm">
        <span
          className={`h-2 w-2 rounded-full ${
            healthQuery.data?.status === "healthy"
              ? "bg-success"
              : "bg-destructive"
          }`}
        />
        <span className="text-muted-foreground">
          Backend: {healthQuery.data?.status || "checking..."}
        </span>
      </div>

      {/* Stats Grid - 4 quadrants like V1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Teams */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Teams</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.total_teams ?? "—"}
            </div>
            <p className="text-xs text-muted-foreground">
              Team channels configured
            </p>
          </CardContent>
        </Card>

        {/* Event Groups */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Event Groups</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.total_event_groups ?? "—"}
            </div>
            <p className="text-xs text-muted-foreground">
              Active event groups
            </p>
          </CardContent>
        </Card>

        {/* Managed Channels */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Channels</CardTitle>
            <Tv className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.total_managed_channels ?? "—"}
            </div>
            <p className="text-xs text-muted-foreground">
              Managed channels in Dispatcharr
            </p>
          </CardContent>
        </Card>

        {/* Templates */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.total_templates ?? "—"}
            </div>
            <p className="text-xs text-muted-foreground">
              EPG templates defined
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Secondary stats row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Cache Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Cache</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Leagues</span>
                <span>{cache?.leagues?.count ?? "—"}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Teams</span>
                <span>{cache?.teams?.count ?? "—"}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stream Cache */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Stream Cache</CardTitle>
            <Tv className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Cached</span>
                <span>{statsQuery.data?.streams?.total_cached ?? "—"}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Hit Rate</span>
                <span>
                  {statsQuery.data?.streams?.cache_hit_rate
                    ? `${(statsQuery.data.streams.cache_hit_rate * 100).toFixed(
                        1
                      )}%`
                    : "—"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Last 24h Activity */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Last 24h</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Runs</span>
                <span>{statsQuery.data?.last_24h?.runs ?? "—"}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Programmes</span>
                <span>
                  {statsQuery.data?.last_24h?.programmes_generated ?? "—"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
