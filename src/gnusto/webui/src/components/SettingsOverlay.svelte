<script lang="ts">
  import OverlayPanel from './OverlayPanel.svelte'

  interface Props {
    debugMode: boolean
    onclose: () => void
    oncommand: (cmd: string) => void
  }

  let { debugMode, onclose, oncommand }: Props = $props()

  // Font size: persisted to localStorage
  let fontSize = $state(parseFloat(localStorage.getItem('gnusto-font-size') || '16'))

  function setFontSize(size: number) {
    fontSize = size
    document.documentElement.style.fontSize = `${size}px`
    localStorage.setItem('gnusto-font-size', String(size))
  }

  function toggleDebug() {
    oncommand(debugMode ? '/debug off' : '/debug on')
  }
</script>

<OverlayPanel title="Settings" {onclose} width="360px">
  <section class="setting">
    <div class="setting-row">
      <div class="setting-label">
        <span class="setting-name">Debug mode</span>
        <span class="setting-desc">Show agent tool calls and actions</span>
      </div>
      <button class="toggle" class:on={debugMode} onclick={toggleDebug} aria-label="Toggle debug mode">
        <span class="toggle-knob"></span>
      </button>
    </div>
  </section>

  <section class="setting">
    <div class="setting-row">
      <div class="setting-label">
        <span class="setting-name">Font size</span>
        <span class="setting-desc">{fontSize}px</span>
      </div>
      <div class="font-controls">
        <button class="font-btn" onclick={() => setFontSize(Math.max(12, fontSize - 1))}>A-</button>
        <button class="font-btn" onclick={() => setFontSize(16)}>A</button>
        <button class="font-btn" onclick={() => setFontSize(Math.min(24, fontSize + 1))}>A+</button>
      </div>
    </div>
  </section>
</OverlayPanel>

<style>
  .setting {
    padding: 0.75rem 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  }

  .setting:last-child {
    border-bottom: none;
  }

  .setting-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .setting-label {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .setting-name {
    font-family: var(--font-ui);
    font-size: 0.9rem;
    color: var(--text-primary);
    font-weight: 500;
  }

  .setting-desc {
    font-family: var(--font-ui);
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  /* Toggle switch */
  .toggle {
    position: relative;
    width: 44px;
    height: 24px;
    border-radius: 12px;
    border: none;
    background: var(--border);
    cursor: pointer;
    flex-shrink: 0;
    transition: background 0.2s;
  }

  .toggle.on {
    background: var(--accent-cyan);
  }

  .toggle-knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: white;
    transition: transform 0.2s;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }

  .toggle.on .toggle-knob {
    transform: translateX(20px);
  }

  /* Font size controls */
  .font-controls {
    display: flex;
    gap: 0.25rem;
  }

  .font-btn {
    font-family: var(--font-ui);
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-secondary);
    background: none;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.25rem 0.5rem;
    cursor: pointer;
    min-width: 32px;
    transition: background 0.15s, border-color 0.15s;
  }

  .font-btn:hover {
    background: rgba(0, 0, 0, 0.05);
    border-color: var(--text-muted);
  }
</style>
