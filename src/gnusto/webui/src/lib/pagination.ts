// Bounded comic PAGES over the panel stream (gnusto-4ac5.4).
//
// Pagination is a NON-DESTRUCTIVE VIEW over the (in-memory) block stream — the
// same order the persisted turn log would yield — so it is deterministically
// re-derivable and a break never drops content. A break only chooses where to
// draw a chunk line over an already-continuous stream; a wrong break is UGLY,
// not BROKEN (a pacing choice, not a correctness one).
//
// LEAN authority (per the .4 design note): programmatic candidates only —
//   1. SCENE break (hard): a room_enter / establishing panel always starts a
//      fresh page.
//   2. CONTINUATION break (soft): a long same-scene stay that spills past the
//      panel budget, snapped to the next TURN boundary (a `command` caption),
//      never mid-beat and never inside a bound tier (tier members are never
//      command/room_enter blocks, so groups stay atomic for free).
// Grue (success …) scene hints and optional LLM promotion are deferred.

import type { RenderableBlock } from './types'

export type PageKind = 'scene' | 'continuation'

export interface Page {
  blocks: RenderableBlock[]
  // index of this page's first block in the source stream — a stable key that
  // survives re-pagination as the live page accretes.
  startIndex: number
  kind: PageKind
}

// Target panels per page. A soft trigger with snapping, not a hard cap: we only
// continuation-break at the next turn boundary AFTER the budget is exceeded.
export const DEFAULT_PAGE_BUDGET = 8

export function paginate(
  blocks: RenderableBlock[],
  budget: number = DEFAULT_PAGE_BUDGET,
): Page[] {
  const pages: Page[] = []
  let current: RenderableBlock[] = []
  let startIndex = 0
  let kind: PageKind = 'scene'

  const commit = () => {
    if (current.length > 0) {
      pages.push({ blocks: current, startIndex, kind })
    }
  }

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i]

    // SCENE break: an establishing panel always opens a new page.
    if (block.type === 'room_enter' && current.length > 0) {
      commit()
      current = []
      startIndex = i
      kind = 'scene'
    } else if (
      // CONTINUATION break: snap to a turn boundary once over budget.
      block.type === 'command' &&
      current.length >= budget
    ) {
      commit()
      current = []
      startIndex = i
      kind = 'continuation'
    }

    if (current.length === 0) startIndex = i
    current.push(block)
  }
  commit()

  return pages
}
