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
<main class="stream" bind:this={streamEl} onclick={handleClick} onkeydown={handleKeydown}>
  {#each blocks as block, i (i)}
    <BlockRenderer {block} />
  {/each}
</main>

<style>
  .stream {
    margin-right: var(--sidebar-width);
    padding: 2rem;
    padding-bottom: 100vh; /* reserve ensures room header can always scroll to top */
  }

  @media (max-width: 768px) {
    .stream {
      margin-left: 0;
      margin-right: 0;
      padding: 1rem;
      padding-bottom: 100vh;
    }
  }
</style>
