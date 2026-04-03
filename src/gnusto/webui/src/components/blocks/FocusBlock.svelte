<script lang="ts">
  import type { FocusBlock, RenderableBlock } from '../../lib/types'
  import { resolveEntityImage } from '../../lib/entities.svelte'

  interface Props {
    block: FocusBlock & RenderableBlock
  }

  let { block }: Props = $props()

  let entityImage = $derived(block.entity ? resolveEntityImage(block.entity) : null)
  let side = $derived(block._side || 'image-left')
</script>

<div class="block-focus {side}" class:has-image={!!entityImage}>
  {#if entityImage}
    <img class="focus-image" src={entityImage} alt={block.entity || ''} onerror={(e) => (e.target as HTMLImageElement).remove()} />
  {/if}
  <div class="focus-body">
    <div class="focus-text">{block.text}</div>
  </div>
</div>

<style>
  .block-focus {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    padding: 0.5rem 0;
    overflow: hidden;
  }

  .block-focus.has-image {
    grid-template-columns: 180px 1fr;
  }

  .block-focus.has-image.image-right {
    grid-template-columns: 1fr 180px;
  }

  .focus-image {
    width: 180px;
    height: 180px;
    object-fit: cover;
    border-radius: 50%;
    background: #eee;
  }

  .image-right .focus-image {
    order: 2;
  }

  .image-right .focus-body {
    order: 1;
  }

  .focus-body {
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .focus-text {
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--text-primary);
  }

  @media (max-width: 768px) {
    .block-focus.has-image {
      grid-template-columns: 1fr;
    }

    .focus-image {
      width: 100%;
      height: auto;
      border-radius: 6px;
    }

    .image-right .focus-image,
    .image-right .focus-body {
      order: unset;
    }
  }
</style>
