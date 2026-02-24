<script lang="ts">
  import type { RenderableBlock } from '../lib/types'
  import BlockRenderer from './blocks/BlockRenderer.svelte'

  interface Props {
    blocks: RenderableBlock[]
  }

  let { blocks }: Props = $props()

  // Auto-scroll when new blocks arrive
  $effect(() => {
    if (blocks.length > 0) {
      requestAnimationFrame(() => {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
      })
    }
  })
</script>

<main class="stream">
  {#each blocks as block, i (i)}
    <BlockRenderer {block} />
  {/each}
</main>

<style>
  .stream {
    margin-left: var(--sidebar-width);
    margin-right: var(--sidebar-width);
    padding: 2rem;
    padding-bottom: var(--input-height);
  }

  @media (max-width: 768px) {
    .stream {
      margin-left: 0;
      margin-right: 0;
      padding: 1rem;
      padding-bottom: var(--input-height);
    }
  }
</style>
