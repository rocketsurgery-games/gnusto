<script lang="ts">
  interface Props {
    enabled: boolean
    gameEnded: boolean
    oncommand: (command: string) => void
  }

  let { enabled, gameEnded, oncommand }: Props = $props()

  let inputEl: HTMLInputElement | undefined = $state()

  // Auto-focus when enabled changes to true
  $effect(() => {
    if (enabled && inputEl) {
      inputEl.focus()
    }
  })

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
