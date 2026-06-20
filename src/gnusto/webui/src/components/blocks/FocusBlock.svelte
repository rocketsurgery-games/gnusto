<script lang="ts">
  import type { FocusBlock, RenderableBlock } from '../../lib/types'
  import { resolveEntityImage } from '../../lib/entities.svelte'
  import EntityInset from './EntityInset.svelte'

  interface Props {
    block: FocusBlock & RenderableBlock
  }

  let { block }: Props = $props()

  let entityImage = $derived(block.entity ? resolveEntityImage(block.entity) : null)
  let side = $derived(block._side || 'image-left')
  // deploy=inset routes through the framed 'specimen plate' (with its own
  // no-art caption fallback, gnusto-4ac5.6); other modes use the avatar layout.
  let asInset = $derived(block.deploy === 'inset')
</script>

{#if asInset}
  <div class="block-focus inset-layout {side}">
    <div class="focus-inset"><EntityInset entity={block.entity} text={block.text} /></div>
    <div class="focus-body"><div class="focus-text">{block.text}</div></div>
  </div>
{:else}
  <div class="block-focus {side}" class:has-image={!!entityImage}>
    {#if entityImage}
      <img class="focus-image" src={entityImage} alt={block.entity || ''} onerror={(e) => (e.target as HTMLImageElement).remove()} />
    {/if}
    <div class="focus-body">
      <div class="focus-text">{block.text}</div>
    </div>
  </div>
{/if}

<style>
  .block-focus {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    padding: 0.5rem 0;
    overflow: hidden;
  }

  .block-focus.has-image,
  .block-focus.inset-layout {
    grid-template-columns: 180px 1fr;
  }

  .block-focus.has-image.image-right,
  .block-focus.inset-layout.image-right {
    grid-template-columns: 1fr 180px;
  }

  .inset-layout .focus-inset {
    width: 180px;
  }

  .image-right .focus-inset {
    order: 2;
  }

  .focus-image {
    width: 180px;
    height: 180px;
    object-fit: cover;
    border-radius: 50%;
    background: var(--panel-fill);
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
    .block-focus.has-image,
    .block-focus.inset-layout {
      grid-template-columns: 1fr;
    }

    .inset-layout .focus-inset {
      width: min(60%, 240px);
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
