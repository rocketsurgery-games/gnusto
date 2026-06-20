<script lang="ts">
  import type { RenderableBlock } from '../lib/types'
  import BlockRenderer from './blocks/BlockRenderer.svelte'

  interface Props {
    blocks: RenderableBlock[]
    onentityclick?: (entityId: string, anchorEl: HTMLElement) => void
  }

  let { blocks, onentityclick }: Props = $props()
  let streamEl: HTMLElement | undefined

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
    {#each blocks as block, i (i)}
      <BlockRenderer {block} />
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

  @media (max-width: 768px) {
    .stream {
      margin-left: 0;
      margin-right: 0;
      padding: 1rem;
      padding-bottom: 55vh;
    }
  }
</style>
