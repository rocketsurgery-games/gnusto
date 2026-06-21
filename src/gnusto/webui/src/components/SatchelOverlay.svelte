<script lang="ts">
  import type { EntityInfo } from '../lib/types'
  import OverlayPanel from './OverlayPanel.svelte'
  import EntityInset from './blocks/EntityInset.svelte'

  interface Props {
    items: EntityInfo[]
    onclose: () => void
    // Clicking an item prefills its name into the input (no action menus).
    onpick: (entityId: string) => void
  }

  let { items, onclose, onpick }: Props = $props()

  function pick(id: string) {
    onpick(id)
    onclose()
  }
</script>

<!--
  The SATCHEL (gnusto-4ac5.2): the summonable inventory as a comic SPREAD of
  specimen plates (reuses the EntityInset primitive from .6). Part of the unified
  "journal" affordance; the map page is a later tab (gnusto-4ac5.2.1, blocked on
  the auto-map). Clicking an item just types its name into the input.
-->
<OverlayPanel title="Satchel" {onclose} width="420px">
  {#if items.length > 0}
    <div class="spread">
      {#each items as item (item.id)}
        <button class="slot" onclick={() => pick(item.id)} title={`Mention the ${item.name}`}>
          <EntityInset entity={item.id} text={item.name} />
        </button>
      {/each}
    </div>
  {:else}
    <p class="empty">Your satchel is empty &mdash; you're carrying nothing.</p>
  {/if}
</OverlayPanel>

<style>
  .spread {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
  }

  .slot {
    display: block;
    width: 100%;
    padding: 0;
    margin: 0;
    background: none;
    border: none;
    cursor: pointer;
    transition: transform 0.12s ease;
  }
  .slot:hover {
    transform: translateY(-2px);
  }

  .empty {
    color: var(--text-muted);
    font-family: var(--font-body);
    font-style: italic;
    text-align: center;
    margin-top: 2rem;
  }
</style>
