<script lang="ts">
  import OverlayPanel from './OverlayPanel.svelte'

  interface Props {
    onclose: () => void
  }

  let { onclose }: Props = $props()
</script>

<OverlayPanel title="Help" {onclose}>
  <section class="help-section">
    <h3>Navigation</h3>
    <table><tbody>
      <tr><td class="cmd">/look</td><td class="alias">/l</td><td>Show current room</td></tr>
    </tbody></table>
  </section>

  <section class="help-section">
    <h3>Game State</h3>
    <table><tbody>
      <tr><td class="cmd">/state</td><td class="alias">/s</td><td>Show current game state</td></tr>
      <tr><td class="cmd">/hint</td><td class="alias"></td><td>Get suggestions for what to try next</td></tr>
      <tr><td class="cmd">/history</td><td class="alias"></td><td>Show turn history</td></tr>
      <tr><td class="cmd">/eval <em>expr</em></td><td class="alias"></td><td>Evaluate a Grue expression</td></tr>
    </tbody></table>
  </section>

  <section class="help-section">
    <h3>Save / Load</h3>
    <table><tbody>
      <tr><td class="cmd">/save <em>[slot]</em></td><td class="alias"></td><td>Save game</td></tr>
      <tr><td class="cmd">/load <em>[slot]</em></td><td class="alias"></td><td>Load game</td></tr>
      <tr><td class="cmd">/saves</td><td class="alias"></td><td>List saved games</td></tr>
    </tbody></table>
  </section>

  <section class="help-section">
    <h3>Debug</h3>
    <table><tbody>
      <tr><td class="cmd">/debug <em>[on|off]</em></td><td class="alias"></td><td>Toggle debug mode</td></tr>
    </tbody></table>
  </section>

  <section class="help-section">
    <h3>Session</h3>
    <table><tbody>
      <tr><td class="cmd">/clear</td><td class="alias"></td><td>Clear screen</td></tr>
      <tr><td class="cmd">/reset</td><td class="alias"></td><td>Restart game</td></tr>
      <tr><td class="cmd">/quit</td><td class="alias">/q</td><td>Quit game</td></tr>
      <tr><td class="cmd">/help</td><td class="alias">/h, /?</td><td>Show this help</td></tr>
      <tr><td class="cmd">/settings</td><td class="alias"></td><td>Open settings panel</td></tr>
    </tbody></table>
  </section>

  <section class="help-section">
    <h3>Interaction</h3>
    <p>Click on <span class="ref-example">highlighted entities</span> in the narrative or sidebar to see available actions. Some actions require a target — click another entity to complete.</p>
  </section>

  <section class="help-section shortcuts">
    <h3>Keyboard</h3>
    <table><tbody>
      <tr><td class="cmd">Escape</td><td class="alias"></td><td>Close overlay / cancel targeting</td></tr>
    </tbody></table>
  </section>
</OverlayPanel>

<style>
  .help-section {
    margin-bottom: 1.25rem;
  }

  .help-section:last-child {
    margin-bottom: 0;
  }

  h3 {
    font-family: var(--font-ui);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  tr {
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  }

  td {
    padding: 0.3rem 0;
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-secondary);
    vertical-align: top;
  }

  .cmd {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--accent-green);
    white-space: nowrap;
    width: 120px;
  }

  .cmd em {
    color: var(--text-muted);
    font-style: italic;
  }

  .alias {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-muted);
    width: 60px;
  }

  p {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  .ref-example {
    color: var(--accent-magenta);
    text-decoration: underline;
    text-decoration-style: dotted;
  }
</style>
