<script lang="ts">
  import type { RenderableBlock } from '../../lib/types'
  import NarrateBlock from './NarrateBlock.svelte'
  import SpeakBlock from './SpeakBlock.svelte'
  import ThinkBlock from './ThinkBlock.svelte'
  import AmbientBlock from './AmbientBlock.svelte'
  import FocusBlock from './FocusBlock.svelte'
  import RevealBlock from './RevealBlock.svelte'
  import ActionResultBlock from './ActionResultBlock.svelte'
  import ImageBlock from './ImageBlock.svelte'
  import SystemBlock from './SystemBlock.svelte'
  import CommandBlock from './CommandBlock.svelte'
  import DebugBlock from './DebugBlock.svelte'
  import EstablishingBlock from './EstablishingBlock.svelte'
  import SfxBlock from './SfxBlock.svelte'

  interface Props {
    block: RenderableBlock
  }

  let { block }: Props = $props()

  // The LLM's pacing intent -> a presentation class the engine owns (4ac5.5).
  let beatClass = $derived(
    block.beat && block.beat !== 'normal' ? `beat-${block.beat}` : ''
  )
</script>

<div class="block {beatClass}">
  {#if block.type === 'room_enter'}
    <EstablishingBlock {block} />
  {:else if block.type === 'sfx'}
    <SfxBlock {block} />
  {:else if block.type === 'narrate'}
    <NarrateBlock {block} />
  {:else if block.type === 'speak'}
    <SpeakBlock {block} />
  {:else if block.type === 'think'}
    <ThinkBlock {block} />
  {:else if block.type === 'ambient'}
    <AmbientBlock {block} />
  {:else if block.type === 'focus'}
    <FocusBlock {block} />
  {:else if block.type === 'reveal'}
    <RevealBlock {block} />
  {:else if block.type === 'action_result'}
    <ActionResultBlock {block} />
  {:else if block.type === 'image'}
    <ImageBlock {block} />
  {:else if block.type === 'system'}
    <SystemBlock {block} />
  {:else if block.type === 'command'}
    <CommandBlock {block} />
  {:else if block.type === 'debug'}
    <DebugBlock {block} />
  {/if}
</div>

<style>
  .block {
    margin-bottom: 1.5rem;
    border-radius: var(--panel-radius);
    animation: block-enter 0.3s ease-out;
  }

  /* beat = the engine's mapping of the LLM's pacing intent (4ac5.5).
     emphasis: comic 'decompression' — more air around the beat + a quiet accent.
     aside: tighter, indented, dimmer. Coarse + robust; no per-block coupling. */
  .block.beat-emphasis {
    margin: 1.9rem 0;
    padding-left: 0.9rem;
    border-left: 2px solid var(--game-accent);
  }

  .block.beat-aside {
    margin-top: 0.25rem;
    margin-left: 1.6rem;
    opacity: 0.7;
  }
</style>
