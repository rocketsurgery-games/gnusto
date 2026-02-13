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

// --- Character name resolution ---

function resolveCharacterName(speakerId, scene) {
  if (!scene?.characters) return speakerId;
  const char = scene.characters.find(c => c.id === speakerId);
  return char ? char.name : speakerId.replace(/^@/, '');
}

function speakerInitial(name) {
  const clean = name.replace(/^(the|a|an)\s+/i, '');
  return clean.charAt(0).toUpperCase();
}

// --- Block renderers ---

const blockRenderers = {
  narrate(block) {
    return el('div', 'block block-narrate', block.text);
  },

  speak(block, scene) {
    const name = resolveCharacterName(block.speaker, scene);
    const wrapper = el('div', 'block block-speak');

    // Avatar
    const avatar = el('div', 'speaker-avatar', speakerInitial(name));
    wrapper.appendChild(avatar);

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

  reveal(block) {
    const wrapper = el('div', 'block block-reveal');
    const label = el('div', 'reveal-label');
    label.textContent = 'Discovered';
    if (block.entity) {
      label.appendChild(el('span', 'entity-ref', block.entity));
    }
    wrapper.appendChild(label);
    wrapper.appendChild(el('div', null, block.text));
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

function renderSceneHeader(scene) {
  const header = el('div', 'scene-header');

  if (scene.room_image) {
    const img = document.createElement('img');
    img.className = 'room-image';
    img.src = scene.room_image;
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

    if (char.image) {
      const img = document.createElement('img');
      img.className = 'avatar';
      img.src = char.image;
      img.alt = char.name;
      img.onerror = () => {
        const ph = el('div', 'avatar-placeholder', speakerInitial(char.name));
        img.replaceWith(ph);
      };
      chip.appendChild(img);
    } else {
      chip.appendChild(el('div', 'avatar-placeholder', speakerInitial(char.name)));
    }

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

function renderBlocks(blocks, scene) {
  const stream = el('div', 'narrative-stream');

  for (const block of blocks) {
    const renderer = blockRenderers[block.type];
    if (renderer) {
      stream.appendChild(renderer(block, scene));
    } else {
      console.warn(`Unknown block type: ${block.type}`);
    }
  }

  return stream;
}

// --- Main render ---

function renderScenario(scenario, container) {
  container.innerHTML = '';

  const scene = scenario.scene || {};
  const blocks = scenario.blocks || [];

  // Update scene header from scene blocks (first scene block overrides)
  const sceneBlock = blocks.find(b => b.type === 'scene');
  if (sceneBlock) {
    if (!scene.room_name && sceneBlock.room_name) scene.room_name = sceneBlock.room_name;
    if (!scene.room_description && sceneBlock.description) scene.room_description = sceneBlock.description;
  }

  container.appendChild(renderSceneHeader(scene));
  container.appendChild(renderCharacterStrip(scene));
  container.appendChild(renderObjectTray(scene));
  container.appendChild(renderBlocks(blocks, scene));
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
      renderScenario(scenario, container);
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
