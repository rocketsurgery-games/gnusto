<script lang="ts">
  import type { RenderableBlock } from '../lib/types'
  import { paginate } from '../lib/pagination'
  import NarrativeStream from './NarrativeStream.svelte'

  interface Props {
    blocks: RenderableBlock[]
    onentityclick?: (entityId: string, anchorEl: HTMLElement) => void
    // Notifies the parent when the reader moves between the LIVE page and a
    // history page, so live-only frame affordances can hide (gnusto-4ac5.2).
    onfollowingchange?: (following: boolean) => void
  }

  let { blocks, onentityclick, onfollowingchange }: Props = $props()

  // Bounded comic PAGES — a non-destructive view over the stream (gnusto-4ac5.4).
  let pages = $derived(paginate(blocks))

  // pageIndex === null means LIVE/follow: always show the latest page and follow
  // new panels as they accrete. Paging back pins a fixed page until the reader
  // returns to "now".
  let pageIndex = $state<number | null>(null)

  let pageCount = $derived(pages.length)
  let current = $derived(
    pageIndex === null
      ? Math.max(0, pageCount - 1)
      : Math.min(pageIndex, Math.max(0, pageCount - 1)),
  )
  let following = $derived(pageIndex === null)
  let page = $derived(pages[current])

  // Surface live/history to the parent (frame affordances are live-only).
  $effect(() => {
    onfollowingchange?.(following)
  })

  // FAIL-SAFE: if pagination is somehow degenerate (no pages but we do have
  // blocks), fall back to the full unbounded stream rather than a blank view.
  let fallback = $derived(pageCount === 0 && blocks.length > 0)

  function goOlder() {
    if (current > 0) pageIndex = current - 1
  }
  function goNewer() {
    const next = current + 1
    // stepping onto the last page re-enters live/follow mode
    pageIndex = next >= pageCount - 1 ? null : next
    scrollPageTop()
  }
  function goNow() {
    pageIndex = null
  }
  function scrollPageTop() {
    requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: 'smooth' }))
  }
</script>

<div class="paged">
  {#if pageCount > 1 && !fallback}
    <div class="pager" class:is-history={!following}>
      <button class="pg" onclick={goOlder} disabled={current === 0} title="Older page">‹ Older</button>
      <span class="pos">
        {#if page?.kind === 'continuation'}<span class="cont" title="continued scene">cont.</span>{/if}
        Page {current + 1} / {pageCount}
      </span>
      {#if following}
        <span class="live" title="following the latest panels">● live</span>
      {:else}
        <button class="pg" onclick={goNewer} title="Newer page">Newer ›</button>
        <button class="pg now" onclick={goNow} title="Jump to the latest page">Now ⤓</button>
      {/if}
    </div>
  {/if}

  {#if fallback}
    <NarrativeStream {blocks} {onentityclick} />
  {:else}
    {#key current}
      <NarrativeStream blocks={page?.blocks ?? []} {onentityclick} autoscroll={following} />
    {/key}
  {/if}
</div>

<style>
  /* slim, unobtrusive pager — chrome-less ethos; only shown when >1 page */
  .pager {
    position: sticky;
    top: 0;
    z-index: 5;
    margin-right: var(--sidebar-width);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.9rem;
    padding: 0.4rem 1rem;
    font-family: var(--font-ui);
    font-size: 0.74rem;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    background: linear-gradient(180deg, var(--game-bg), transparent);
    backdrop-filter: blur(2px);
  }

  .pager.is-history {
    color: var(--game-accent-glow);
  }

  .pos {
    text-transform: uppercase;
    white-space: nowrap;
  }

  .cont {
    color: var(--game-warm);
    margin-right: 0.4rem;
    font-style: italic;
    text-transform: none;
  }

  .pg {
    background: none;
    border: 1px solid var(--game-line);
    color: inherit;
    font: inherit;
    text-transform: uppercase;
    padding: 0.18rem 0.55rem;
    border-radius: 3px;
    cursor: pointer;
  }
  .pg:hover:not(:disabled) {
    border-color: var(--game-accent);
    color: var(--game-accent-glow);
  }
  .pg:disabled {
    opacity: 0.35;
    cursor: default;
  }
  .pg.now {
    border-color: var(--game-accent);
    color: var(--game-accent-glow);
  }

  .live {
    text-transform: uppercase;
    color: var(--game-accent);
    white-space: nowrap;
  }

  @media (max-width: 768px) {
    .pager {
      margin-right: 0;
    }
  }
</style>
