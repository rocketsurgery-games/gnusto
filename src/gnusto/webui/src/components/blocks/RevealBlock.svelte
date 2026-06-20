<script lang="ts">
  import type { RevealBlock, RenderableBlock } from '../../lib/types'
  import { resolveEntityImage } from '../../lib/entities.svelte'
  import EntityInset from './EntityInset.svelte'

  interface Props {
    block: RevealBlock & RenderableBlock
  }

  let { block }: Props = $props()

  let entityImage = $derived(block.entity ? resolveEntityImage(block.entity) : null)
  let side = $derived(block._side || 'image-left')
  // deploy=inset routes through the framed 'specimen plate' (with its own
  // no-art caption fallback, gnusto-4ac5.6); other modes overhang the image.
  let asInset = $derived(block.deploy === 'inset')
</script>

{#if asInset}
  <div class="block-reveal inset-layout {side}">
    <div class="reveal-inset"><EntityInset entity={block.entity} text={block.text} /></div>
    <div class="reveal-text">{block.text}</div>
  </div>
{:else}
  <div class="block-reveal {side}" class:has-image={!!entityImage}>
    {#if entityImage}
      <img class="reveal-image" src={entityImage} alt={block.entity || ''} onerror={(e) => (e.target as HTMLImageElement).remove()} />
    {/if}
    <div class="reveal-text">{block.text}</div>
  </div>
{/if}

<style>
  .block-reveal {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    padding: 0.5rem 0;
    overflow: visible;
  }

  .block-reveal.has-image,
  .block-reveal.inset-layout {
    grid-template-columns: 180px 1fr;
  }

  .inset-layout .reveal-inset {
    width: 180px;
  }

  .image-right .reveal-inset {
    order: 2;
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
    background: var(--panel-fill);
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
    .block-reveal.has-image,
    .block-reveal.inset-layout {
      grid-template-columns: 1fr;
      margin-left: 0;
      margin-right: 0;
    }

    .inset-layout .reveal-inset {
      width: min(60%, 240px);
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
