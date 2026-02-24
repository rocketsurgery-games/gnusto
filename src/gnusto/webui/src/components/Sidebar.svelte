<script lang="ts">
  interface Props {
    side: 'left' | 'right'
  }

  let { side }: Props = $props()
</script>

<aside class="sidebar sidebar-{side}">
  <p>Coming soon</p>
</aside>

<style>
  .sidebar {
    position: fixed;
    top: 0;
    bottom: var(--input-height);
    width: var(--sidebar-width);
    padding: 1rem;
    color: var(--text-muted);
    font-size: 0.85rem;
    font-family: var(--font-ui);
    overflow-y: auto;
    z-index: 5;
  }

  .sidebar-left {
    left: 0;
  }

  .sidebar-right {
    right: 0;
  }

  @media (max-width: 768px) {
    .sidebar {
      display: none;
    }
  }
</style>
