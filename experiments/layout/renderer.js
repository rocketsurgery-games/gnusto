/**
 * Layout renderer for content blocks.
 *
 * Takes a scenario (scene context + block sequence) and produces
 * styled DOM output. CSS does the heavy lifting - this module maps
 * block types to DOM elements with appropriate classes.
 */

// --- DOM helpers ---

function el(tag, cls, children) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (typeof children === 'string') {
    e.textContent = children;
  } else if (Array.isArray(children)) {
    for (const c of children) if (c) e.appendChild(c);
  } else if (children instanceof Node) {
    e.appendChild(children);
  }
  return e;
}

function text(str) {
  return document.createTextNode(str);
}

// --- Character / object resolution ---

function resolveCharacter(speakerId, scene) {
  if (!scene?.characters) return null;
  return scene.characters.find(c => c.id === speakerId) || null;
}

function resolveCharacterName(speakerId, scene) {
  const char = resolveCharacter(speakerId, scene);
  return char ? char.name : speakerId.replace(/^@/, '');
}

function resolveObject(entityId, scene) {
  if (!scene?.objects) return null;
  return scene.objects.find(o => o.id === entityId) || null;
}

function speakerInitial(name) {
  const clean = name.replace(/^(the|a|an)\s+/i, '');
  return clean.charAt(0).toUpperCase();
}

function makeAvatar(name, imageSrc, size) {
  if (imageSrc) {
    const img = document.createElement('img');
    img.className = size === 'large' ? 'speaker-avatar speaker-avatar-img' : 'avatar';
    img.src = imageSrc;
    img.alt = name;
    img.onerror = () => {
      const ph = el('div', size === 'large' ? 'speaker-avatar' : 'avatar-placeholder', speakerInitial(name));
      img.replaceWith(ph);
    };
    return img;
  }
  return el('div', size === 'large' ? 'speaker-avatar' : 'avatar-placeholder', speakerInitial(name));
}

// --- Block renderers ---

const blockRenderers = {
  narrate(block) {
    return el('div', 'block block-narrate', block.text);
  },

  speak(block, scene) {
    const char = resolveCharacter(block.speaker, scene);
    const name = char ? char.name : block.speaker.replace(/^@/, '');
    const wrapper = el('div', 'block block-speak');

    // Avatar (use character image if available)
    wrapper.appendChild(makeAvatar(name, char?.image, 'large'));

    // Speaker tag
    wrapper.appendChild(el('div', 'speaker-tag', name));

    // Speech bubble
    const bubble = el('div', 'speech-bubble');
    bubble.appendChild(text(block.text));
    wrapper.appendChild(bubble);

    // Manner annotation
    if (block.manner) {
      wrapper.appendChild(el('div', 'manner', block.manner));
    }

    return wrapper;
  },

  think(block) {
    return el('div', 'block block-think', block.text);
  },

  ambient(block) {
    return el('div', 'block block-ambient', block.text);
  },

  reveal(block, scene, blockIndex, manifest) {
    const wrapper = el('div', 'block block-reveal');

    // Check manifest for composed moment image
    const momentImage = manifest?.[`moment-${blockIndex}`];
    if (momentImage) {
      const img = document.createElement('img');
      img.className = 'reveal-image';
      img.src = momentImage;
      img.alt = block.entity || 'discovery';
      img.onerror = () => img.remove();
      wrapper.appendChild(img);
    }

    const label = el('div', 'reveal-label');
    label.textContent = 'Discovered';
    if (block.entity) {
      label.appendChild(el('span', 'entity-ref', block.entity));
    }
    wrapper.appendChild(label);
    wrapper.appendChild(el('div', null, block.text));
    return wrapper;
  },

  focus(block, scene, blockIndex, manifest) {
    const wrapper = el('div', 'block block-focus');

    // Check manifest for composed focus image first
    let image = manifest?.[`focus-${blockIndex}`];
    if (!image) image = block.image;
    if (!image && block.entity) {
      const char = resolveCharacter(block.entity, scene);
      const obj = resolveObject(block.entity, scene);
      image = char?.image || obj?.image;
    }

    if (image) {
      const img = document.createElement('img');
      img.className = 'focus-image';
      img.src = image;
      img.alt = block.entity || '';
      img.onerror = () => img.remove();
      wrapper.appendChild(img);
    }

    const body = el('div', 'focus-body');
    if (block.entity) {
      const label = resolveCharacterName(block.entity, scene) ||
                    resolveObject(block.entity, scene)?.name ||
                    block.entity.replace(/^@/, '');
      body.appendChild(el('div', 'focus-label', label));
    }
    body.appendChild(el('div', 'focus-text', block.text));
    wrapper.appendChild(body);
    return wrapper;
  },

  scene(block) {
    const wrapper = el('div', 'block block-scene');

    if (block.transition) {
      wrapper.appendChild(el('div', 'transition-label', block.transition));
    }

    // Room name from the block's room field (display-friendly)
    const roomName = block.room_name || block.room?.replace(/^@/, '').replace(/-/g, ' ') || 'Unknown';
    wrapper.appendChild(el('div', 'scene-room-name', roomName));

    if (block.description) {
      wrapper.appendChild(el('div', 'scene-description', block.description));
    }

    return wrapper;
  },
};

// --- Scene header ---

function renderSceneHeader(scene, manifest) {
  const header = el('div', 'scene-header');

  // Use composed scene image if available, falling back to room_image
  const composedScene = manifest?.scene;
  const bgImage = composedScene || scene.room_image;

  if (composedScene) {
    // Composed image: show prominently as scene illustration
    const img = document.createElement('img');
    img.className = 'scene-illustration';
    img.src = composedScene;
    img.alt = scene.room_name || '';
    img.onerror = () => img.remove();
    header.appendChild(img);
  } else if (bgImage) {
    // Raw ref: faint backdrop
    const img = document.createElement('img');
    img.className = 'room-image';
    img.src = bgImage;
    img.alt = scene.room_name || '';
    img.onerror = () => img.remove();
    header.appendChild(img);
  }

  const info = el('div', 'room-info');
  info.appendChild(el('div', 'room-name', scene.room_name || scene.room || 'Unknown'));

  if (scene.room_description) {
    info.appendChild(el('div', 'room-description', scene.room_description));
  }

  header.appendChild(info);
  return header;
}

// --- Character strip ---

function renderCharacterStrip(scene) {
  const strip = el('div', 'character-strip');
  if (!scene.characters?.length) return strip;

  for (const char of scene.characters) {
    const chip = el('div', 'character-chip');
    chip.appendChild(makeAvatar(char.name, char.image, 'small'));
    chip.appendChild(el('span', 'char-name', char.name));
    strip.appendChild(chip);
  }

  return strip;
}

// --- Object tray ---

function renderObjectTray(scene) {
  const tray = el('div', 'object-tray');
  if (!scene.objects?.length) return tray;

  for (const obj of scene.objects) {
    tray.appendChild(el('span', 'object-tag', obj.name));
  }

  return tray;
}

// --- Narrative stream ---

function renderBlocks(blocks, scene, manifest) {
  const stream = el('div', 'narrative-stream');

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    const renderer = blockRenderers[block.type];
    if (renderer) {
      stream.appendChild(renderer(block, scene, i, manifest));
    } else {
      console.warn(`Unknown block type: ${block.type}`);
    }
  }

  return stream;
}

// --- Main render ---

function renderScenario(scenario, container, manifest) {
  container.innerHTML = '';

  const scene = scenario.scene || {};
  const blocks = scenario.blocks || [];

  // Update scene header from scene blocks (first scene block overrides)
  const sceneBlock = blocks.find(b => b.type === 'scene');
  if (sceneBlock) {
    if (!scene.room_name && sceneBlock.room_name) scene.room_name = sceneBlock.room_name;
    if (!scene.room_description && sceneBlock.description) scene.room_description = sceneBlock.description;
  }

  container.appendChild(renderSceneHeader(scene, manifest));
  container.appendChild(renderCharacterStrip(scene));
  container.appendChild(renderObjectTray(scene));
  container.appendChild(renderBlocks(blocks, scene, manifest));
}

// --- Scenario loading ---

async function loadScenario(name) {
  const resp = await fetch(`scenarios/${name}.json`);
  if (!resp.ok) throw new Error(`Failed to load scenario: ${name}`);
  return resp.json();
}

// --- Init ---

async function init() {
  const select = document.getElementById('scenario-select');
  const container = document.getElementById('content');

  const scenarios = [
    'room-entry',
    'hacker-conversation',
    'action-sequence',
    'discovery',
    'busy-scene',
  ];

  // Populate dropdown
  for (const name of scenarios) {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    select.appendChild(opt);
  }

  // Load and render
  async function load(name) {
    try {
      const scenario = await loadScenario(name);

      // Try to load composed image manifest (optional)
      let manifest = null;
      try {
        const mResp = await fetch(`assets/composed/${name}.json`);
        if (mResp.ok) manifest = await mResp.json();
      } catch { /* no composed images for this scenario */ }

      renderScenario(scenario, container, manifest);
    } catch (err) {
      container.innerHTML = `<div style="padding:2rem;color:#e94560">Error: ${err.message}</div>`;
    }
  }

  select.addEventListener('change', () => load(select.value));

  // Load first scenario
  if (scenarios.length > 0) {
    select.value = scenarios[0];
    await load(scenarios[0]);
  }
}

document.addEventListener('DOMContentLoaded', init);
