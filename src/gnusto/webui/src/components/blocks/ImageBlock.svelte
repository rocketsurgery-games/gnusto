<script lang="ts">
  import type { ImageBlock } from '../../lib/types'

  interface Props {
    block: ImageBlock
  }

  let { block }: Props = $props()
</script>

<div class="block-image image-{block.layout} image-{block.size}">
  <img src={block.src} alt={block.alt} />
</div>

<style>
  .block-image {
    text-align: center;
    margin: 1.5rem 0;
  }

  .block-image img {
    max-width: 100%;
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .image-inline {
    text-align: center;
  }

  .image-float-left {
    float: left;
    margin: 0 1.5rem 1rem 0;
    text-align: left;
  }

  .image-float-right {
    float: right;
    margin: 0 0 1rem 1.5rem;
    text-align: right;
  }

  .image-background {
    position: relative;
    margin: 2rem -2rem;
    padding: 2rem;
    text-align: center;
  }

  .image-background img {
    width: 100%;
    max-height: 400px;
    object-fit: cover;
    opacity: 0.4;
  }

  .image-small img {
    max-width: 150px;
    max-height: 150px;
  }

  .image-medium img {
    max-width: 300px;
    max-height: 300px;
  }

  .image-large img {
    max-width: 500px;
    max-height: 500px;
  }

  .image-full img {
    max-width: 100%;
  }
</style>
