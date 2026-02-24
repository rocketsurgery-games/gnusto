<script lang="ts">
  import type { RevealBlock, RenderableBlock } from '../../lib/types'
  import { resolveEntityImage } from '../../lib/entities.svelte'

  interface Props {
    block: RevealBlock & RenderableBlock
  }

  let { block }: Props = $props()

  let entityImage = $derived(block.entity ? resolveEntityImage(block.entity) : null)
  let side = $derived(block._side || 'image-left')
</script>

<div class="block-reveal {side}" class:has-image={!!entityImage}>
  {#if entityImage}
    <img class="reveal-image" src={entityImage} alt={block.entity || ''} onerror={(e) => (e.target as HTMLImageElement).remove()} />
  {/if}
  <div class="reveal-text">{block.text}</div>
</div>

<style>
  .block-reveal {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    padding: 0.5rem 0;
    overflow: visible;
  }

  .block-reveal.has-image {
    grid-template-columns: 180px 1fr;
  }

  .block-reveal.has-image.image-left {
    margin-left: calc(-1 * var(--image-overhang));
  }

  .block-reveal.has-image.image-right {
    grid-template-columns: 1fr 180px;
    margin-right: calc(-1 * var(--image-overhang));
  }

  .reveal-image {
    width: 180px;
    max-height: 220px;
    object-fit: cover;
    border-radius: 6px;
    background: #eee;
  }

  .image-right .reveal-image {
    order: 2;
  }

  .image-right .reveal-text {
    order: 1;
  }

  .reveal-text {
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--reveal-text);
    display: flex;
    align-items: center;
  }

  @media (max-width: 768px) {
    .block-reveal.has-image {
      grid-template-columns: 1fr;
      margin-left: 0;
      margin-right: 0;
    }

    .reveal-image {
      width: 100%;
      height: auto;
    }

    .image-right .reveal-image,
    .image-right .reveal-text {
      order: unset;
    }
  }
</style>
