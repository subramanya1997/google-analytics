import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Formats a duration in milliseconds to a compact human-readable format.
 * Precision scales with magnitude — longer durations drop smaller units:
 *
 *   < 1 min  → seconds with one decimal  ("1.5s", "45s")
 *   1–59 min → minutes only              ("2m", "14m")
 *   ≥ 1 hour → hours + minutes           ("1h 1m", "3h")
 *
 * Handles null/undefined gracefully with a configurable fallback.
 *
 * @example formatDurationMs(1500)       // "1.5s"
 * @example formatDurationMs(125000)     // "2m"
 * @example formatDurationMs(3661000)    // "1h 1m"
 * @example formatDurationMs(null)       // "—"
 * @example formatDurationMs(null, "")   // ""
 */
export function formatDurationMs(
  ms: number | null | undefined,
  fallback = "—"
): string {
  if (ms == null || ms < 0) return fallback

  const totalSeconds = Math.floor(ms / 1000)

  // < 1 minute → show seconds (with one decimal if fractional)
  if (totalSeconds < 60) {
    const seconds = ms / 1000
    return seconds % 1 === 0
      ? `${seconds}s`
      : `${parseFloat(seconds.toFixed(1))}s`
  }

  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)

  // ≥ 1 hour → hours + minutes (drop seconds)
  if (hours > 0) {
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
  }

  // 1–59 minutes → minutes only (drop seconds)
  return `${minutes}m`
}

/**
 * Convenience wrapper: computes the duration between two ISO date strings and
 * formats it with {@link formatDurationMs}.
 *
 * @example formatDurationBetween("2024-01-01T00:00:00Z", "2024-01-01T00:02:05Z") // "2m"
 * @example formatDurationBetween(undefined, undefined)                            // "—"
 */
export function formatDurationBetween(
  startDate: string | undefined | null,
  endDate: string | undefined | null,
  fallback = "—"
): string {
  if (!startDate || !endDate) return fallback

  const ms = new Date(endDate).getTime() - new Date(startDate).getTime()
  return formatDurationMs(ms, fallback)
}
