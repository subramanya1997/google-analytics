import { useMemo } from "react"

/** Available page size options shown in every pagination dropdown. */
export const PAGE_SIZE_OPTIONS = [25, 50, 100] as const

/** Default number of items per page. */
export const DEFAULT_PAGE_SIZE = 25

/**
 * Computes a sliding window of visible page numbers for pagination controls.
 *
 * Given the current page and total pages, returns an array of sequential,
 * unique page numbers centered around `currentPage` (clamped to valid bounds).
 *
 * @param currentPage - The active page (1-indexed)
 * @param totalPages  - Total number of pages
 * @param maxVisible  - Maximum page buttons to show (default 5)
 * @returns An array of page numbers, e.g. [3, 4, 5, 6, 7]
 */
export function usePageNumbers(
  currentPage: number,
  totalPages: number,
  maxVisible: number = 5
): number[] {
  return useMemo(() => {
    const half = Math.floor(maxVisible / 2)

    let start = Math.max(1, currentPage - half)
    let end = Math.min(totalPages, start + maxVisible - 1)

    // Adjust start if we're near the end and have room to show more
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1)
    }

    const pages: number[] = []
    for (let i = start; i <= end; i++) {
      pages.push(i)
    }
    return pages
  }, [currentPage, totalPages, maxVisible])
}
