<script lang="ts">
  interface Props {
    side: 'left' | 'right'
  }

  let { side }: Props = $props()
</script>

<div class="peek-tab peek-{side}">
  <span class="peek-icon">{side === 'left' ? '\u25B6' : '\u25C0'}</span>
</div>

<style>
  .peek-tab {
    display: none;
    position: fixed;
    top: 50%;
    transform: translateY(-50%);
    width: 24px;
    height: 48px;
    background: var(--border);
    border-radius: 0 4px 4px 0;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 20;
    opacity: 0.5;
    transition: opacity 0.2s;
  }

  .peek-tab:hover {
    opacity: 1;
  }

  .peek-left {
    left: 0;
    border-radius: 0 4px 4px 0;
  }

  .peek-right {
    right: 0;
    border-radius: 4px 0 0 4px;
  }

  .peek-icon {
    font-size: 0.7rem;
    color: var(--text-muted);
  }

  @media (max-width: 768px) {
    .peek-tab {
      display: flex;
    }
  }
</style>
