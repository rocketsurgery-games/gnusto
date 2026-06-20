<script lang="ts">
  import { resolveEntityImage, resolveEntityName } from '../../lib/entities.svelte'

  interface Props {
    entity: string | null
    text?: string
  }

  let { entity, text }: Props = $props()

  let src = $derived(entity ? resolveEntityImage(entity) : null)
  let failed = $state(false)
  let label = $derived(entity ? resolveEntityName(entity) : '')
</script>

<!--
  Framed 'specimen plate' inset (deploy=inset, gnusto-4ac5.5). Object/character
  art is single-subject on an opaque, often-inconsistent background, so it reads
  as a deliberate field-notes plate rather than a full-bleed panel.

  DEGRADATION (gnusto-4ac5.6): with no resolvable asset (missing key) — or a
  broken URL — it degrades to a CAPTION INSET (an italic placeholder card),
  never a broken image.
-->
{#if src && !failed}
  <figure class="inset">
    <img src={src} alt={label} onerror={() => (failed = true)} />
    {#if label}<figcaption class="plate-label">{label}</figcaption>{/if}
  </figure>
{:else}
  <figure class="inset inset--noart">
    <figcaption>{text || label || '\u2014'}</figcaption>
  </figure>
{/if}

<style>
  /* a light 'specimen plate': object art is single-subject on an opaque bg, so
     a light plate lets it sit deliberately rather than fight the dark gutter */
  .inset {
    margin: 0;
    background: linear-gradient(180deg, #efe8d6, #ded5bd);
    border: 1px solid #000;
    box-shadow:
      0 0 0 1px #000,
      0 10px 24px -12px #000;
    padding: 8px 8px 6px;
    border-radius: 2px;
  }

  .inset img {
    display: block;
    width: 100%;
    aspect-ratio: 1 / 1;
    object-fit: contain;
    background: #f4eede;
    filter: saturate(0.95) contrast(1.04);
  }

  .plate-label {
    margin-top: 6px;
    font-family: var(--font-letter);
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: center;
    color: #2a2620;
  }

  /* no-art fallback: an italic caption card in the same plate footprint */
  .inset--noart {
    display: grid;
    place-items: center;
    aspect-ratio: 1 / 1;
    background: var(--game-panel-2);
    border: 1px dashed var(--game-line);
    box-shadow: none;
    color: var(--text-muted);
    font-family: var(--font-body);
    font-style: italic;
    text-align: center;
    padding: 14px;
  }

  .inset--noart figcaption {
    font-size: 0.9rem;
    line-height: 1.4;
  }
</style>
