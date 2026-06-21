<script lang="ts">
  interface Props {
    enabled: boolean
    gameEnded: boolean
    prefill?: string | null
    oncommand: (command: string) => void
    onprefillconsumed?: () => void
  }

  let { enabled, gameEnded, prefill = null, oncommand, onprefillconsumed }: Props = $props()

  let inputEl: HTMLInputElement | undefined = $state()

  // Auto-focus when enabled changes to true
  $effect(() => {
    if (enabled && inputEl) {
      inputEl.focus()
    }
  })

  // Fill input when prefill changes
  $effect(() => {
    if (prefill != null && inputEl) {
      inputEl.value = prefill
      inputEl.focus()
      onprefillconsumed?.()
    }
  })

  function handleGlobalKeydown(e: KeyboardEvent) {
    if (!enabled || gameEnded) return
    if (!inputEl || inputEl === document.activeElement) return
    // Ignore modifier combos (Ctrl+C, Cmd+V, etc.) and non-printable keys
    if (e.ctrlKey || e.metaKey || e.altKey) return
    if (e.key.length !== 1) return
    // Don't steal focus from other inputs/textareas
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    inputEl.focus()
  }

  function handleSubmit(e: SubmitEvent) {
    e.preventDefault()
    if (!inputEl) return
    const cmd = inputEl.value.trim()
    if (cmd) {
      oncommand(cmd)
      inputEl.value = ''
    }
  }
</script>

<svelte:window onkeydown={handleGlobalKeydown} />

<footer class="input-bar">
  <form onsubmit={handleSubmit}>
    <span class="prompt">&gt;</span>
    <input
      bind:this={inputEl}
      type="text"
      placeholder={gameEnded ? 'Game ended. Refresh to restart.' : (enabled ? 'What do you want to do?' : 'Waiting...')}
      disabled={!enabled || gameEnded}
      autocomplete="off"
    />
  </form>
</footer>

<style>
  .input-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: var(--input-height);
    padding: 0.75rem 2rem;
    background: var(--bg-primary);
    border-top: 1px solid var(--border);
    box-shadow: 0 -10px 24px -12px #000;
    z-index: 10;
  }

  form {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    max-width: 800px;
    margin: 0 auto;
  }

  .prompt {
    color: var(--accent-green);
    font-family: var(--font-mono);
    font-size: 0.95rem;
    text-shadow: 0 0 8px rgba(143, 224, 106, 0.4);
  }

  input {
    flex: 1;
    padding: 0;
    font-size: 1rem;
    font-family: var(--font-mono);
    background: transparent;
    border: none;
    color: var(--text-primary);
    outline: none;
    caret-color: var(--accent-cyan);
  }

  input::placeholder {
    color: var(--text-muted);
    font-style: italic;
  }

  input:disabled {
    opacity: 0.5;
  }
</style>
