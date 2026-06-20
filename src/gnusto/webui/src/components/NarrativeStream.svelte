<script lang="ts">
  import type { RenderableBlock } from '../lib/types'
  import BlockRenderer from './blocks/BlockRenderer.svelte'

  interface Props {
    blocks: RenderableBlock[]
    onentityclick?: (entityId: string, anchorEl: HTMLElement) => void
  }

  let { blocks, onentityclick }: Props = $props()
  let streamEl: HTMLElement | undefined

  // Tier grouping (gnusto-4ac5.5/.7): consecutive small panels that share a
  // non-empty `group` tag are bound into one comic TIER (a row on desktop,
  // stacked on mobile). The LLM tags members; the engine owns the geometry.
  // We fold the flat stream into a list of items, each either a lone block or
  // a tier (a run of same-group blocks). Keys stay tied to the first member's
  // stream index so frozen panels keep stable identity.
  type StreamItem =
    | { kind: 'block'; key: number; block: RenderableBlock }
    | { kind: 'tier'; key: number; blocks: RenderableBlock[] }

  let items = $derived.by(() => {
    const out: StreamItem[] = []
    let i = 0
    while (i < blocks.length) {
      const b = blocks[i]
      const g = b.group
      if (g) {
        // gather the maximal run of consecutive blocks with the same group
        const run: RenderableBlock[] = [b]
        let j = i + 1
        while (j < blocks.length && blocks[j].group === g) {
          run.push(blocks[j])
          j++
        }
        if (run.length > 1) {
          out.push({ kind: 'tier', key: i, blocks: run })
          i = j
          continue
        }
        // a lone grouped block is just a normal panel
      }
      out.push({ kind: 'block', key: i, block: b })
      i++
    }
    return out
  })

  // Auto-scroll when new blocks arrive — scroll the last block into view
  // (not scrollHeight, which would scroll into the padding-bottom reserve)
  $effect(() => {
    if (blocks.length > 0) {
      requestAnimationFrame(() => {
        streamEl?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' })
      })
    }
  })

  function handleClick(e: MouseEvent) {
    const target = (e.target as HTMLElement).closest('.ref[data-entity]') as HTMLElement | null
    if (target && onentityclick) {
      onentityclick(target.dataset.entity!, target)
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      const target = (e.target as HTMLElement).closest('.ref[data-entity]') as HTMLElement | null
      if (target && onentityclick) {
        e.preventDefault()
        onentityclick(target.dataset.entity!, target)
      }
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<main class="stream" onclick={handleClick} onkeydown={handleKeydown}>
  <!-- the webtoon SPINE: a bounded, centered reading column (gnusto-4ac5.7) -->
  <div class="spine" bind:this={streamEl}>
    {#each items as item (item.key)}
      {#if item.kind === 'tier'}
        <!-- TIER: a row of small panels on desktop, stacked on mobile (4ac5.7) -->
        <div class="tier">
          {#each item.blocks as block, k (k)}
            <BlockRenderer {block} />
          {/each}
        </div>
      {:else}
        <BlockRenderer block={item.block} />
      {/if}
    {/each}
  </div>
</main>

<style>
  .stream {
    margin-right: var(--sidebar-width);
    padding: 1.5rem 1rem;
    padding-bottom: 55vh; /* reserve so the live page can accrete + scroll */
  }

  .spine {
    max-width: var(--spine-max);
    margin: 0 auto;
  }

  /* TIER — print-style multi-panel row. DESKTOP-ONLY progressive enhancement
     layered on the vertical spine (gnusto-4ac5.7). Mobile: children just stack;
     desktop: an equal-column row aligned to the baseline of the strip. */
  @media (min-width: 900px) {
    .tier {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: 1fr;
      gap: 14px;
      align-items: end;
      margin-bottom: 1.5rem;
    }
    /* the BlockRenderer wrapper already supplies per-block margin; zero it out
       inside a tier so the row gap is the only spacing */
    .tier > :global(.block) {
      margin-bottom: 0;
    }
  }

  @media (max-width: 768px) {
    .stream {
      margin-left: 0;
      margin-right: 0;
      padding: 1rem;
      padding-bottom: 55vh;
    }
  }
</style>
