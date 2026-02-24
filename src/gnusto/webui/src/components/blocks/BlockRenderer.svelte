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

  interface Props {
    block: RenderableBlock
  }

  let { block }: Props = $props()
</script>

<div class="block">
  {#if block.type === 'narrate'}
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
</style>
