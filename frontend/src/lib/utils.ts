import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Sport display names - handles special cases like MMA, NFL, etc.
 * Used for consistent sport name formatting across the UI.
 */
const SPORT_DISPLAY_NAMES: Record<string, string> = {
  mma: "MMA",
  nfl: "NFL",
  nba: "NBA",
  nhl: "NHL",
  mlb: "MLB",
}

/**
 * Get display name for a sport.
 * Returns special-cased names (MMA, NFL) or capitalizes the first letter.
 */
export function getSportDisplayName(sport: string): string {
  const lower = sport.toLowerCase()
  return SPORT_DISPLAY_NAMES[lower] ?? sport.charAt(0).toUpperCase() + sport.slice(1)
}
