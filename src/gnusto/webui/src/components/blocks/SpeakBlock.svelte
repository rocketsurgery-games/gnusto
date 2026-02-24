<script lang="ts">
  import type { SpeakBlock } from '../../lib/types'
  import { resolveEntityName, resolveEntityImage, speakerInitial } from '../../lib/entities.svelte'

  interface Props {
    block: SpeakBlock
  }

  let { block }: Props = $props()

  let speakerId = $derived(block.speaker || 'unknown')
  let name = $derived(resolveEntityName(speakerId))
  let avatarImage = $derived(resolveEntityImage(speakerId))
  let initial = $derived(speakerInitial(name))

  function handleImageError(e: Event) {
    const img = e.target as HTMLImageElement
    img.style.display = 'none'
    // Show fallback initial
    const parent = img.parentElement
    if (parent) {
      const fallback = document.createElement('div')
      fallback.className = 'speaker-avatar fallback'
      fallback.textContent = initial
      parent.insertBefore(fallback, img)
      img.remove()
    }
  }
</script>

<div class="block-speak">
  <div class="avatar-slot">
    {#if avatarImage}
      <img class="speaker-avatar speaker-avatar-img" src={avatarImage} alt={name} onerror={handleImageError} />
    {:else}
      <div class="speaker-avatar">{initial}</div>
    {/if}
  </div>
  <div class="speech-bubble">
    {block.text}
    {#if block.manner}
      <span class="manner">{block.manner}</span>
    {/if}
  </div>
</div>

<style>
  .block-speak {
    display: grid;
    grid-template-columns: 44px 1fr;
    gap: 0 0.75rem;
    align-items: start;
  }

  .speaker-avatar {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--accent-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    color: #fff;
    font-weight: bold;
    margin-top: 0.1rem;
  }

  .speaker-avatar-img {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    object-fit: cover;
    object-position: center 15%;
    margin-top: 0.1rem;
    border: 2px solid var(--border);
    background: none;
  }

  .speech-bubble {
    position: relative;
    padding: 0.5rem 0;
    color: var(--text-primary);
    font-size: 0.95rem;
    line-height: 1.6;
  }

  .speech-bubble::before {
    content: '\201C';
    color: var(--text-muted);
    font-size: 1.2rem;
    line-height: 1;
    margin-right: 0.05rem;
  }

  .speech-bubble::after {
    content: '\201D';
    color: var(--text-muted);
    font-size: 1.2rem;
    line-height: 1;
    margin-left: 0.05rem;
  }

  .manner {
    font-family: var(--font-ui);
    font-size: 0.75rem;
    color: var(--text-muted);
    font-style: italic;
    margin-left: 0.5rem;
  }
</style>
