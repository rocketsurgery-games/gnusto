"""Consistency-reference probes for the Nano Banana (Gemini) image model.

Throwaway R&D harness (yak gnusto-819a). Finds which mechanism actually holds
*identity / structural* consistency across related images, with **style held
fixed** (the real world :visual-style). See README.md for the design.

Mechanisms (per-node, see Node.mech):
  M1  prompt    - text only (control / frozen root)
  M2  ref       - fresh generation conditioned on one frozen reference image
  M3  edit      - in-place edit of one prior image ("keep all, change only X")
  M4  grid      - one model-sheet call, PIL-sliced into N panels
  M5  crop      - PIL crop of a master plate (no API call)

Nodes form a tiny DAG via `deps`; the runner is a topological executor. This
doubles as a prototype of the dependency model we'll eventually move into Grue.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

# ---------------------------------------------------------------------------
# Style: mirror games/lurkinghorror/lurkinghorror.grue :visual-style verbatim,
# so probes match production and we isolate identity from style.
# ---------------------------------------------------------------------------

STYLE_BASE = (
    "Style: broad alla prima brush strokes, suitable only as a rough mockup for a "
    "human artist, but little detail.\n\n"
    "Palette: desaturated dark blues and teals, sickly fluorescent greens, warm "
    "incandescent highlights."
)

KIND_PROMPT = {
    "room": (
        "Wide establishing shot of the empty location; environment only, no "
        "people, cinematic framing with room to breathe."
    ),
    "object": (
        "A single subject, centered, isolated on a flat pure-black background; no "
        "scene, no props, no floor, even studio lighting."
    ),
    # Events aren't specialized in the world file; beats are one-off narrative
    # panels that may depict figures/mist. Cinematic wide is a reasonable choice.
    "event": "Cinematic narrative panel; may depict figures and atmosphere.",
}

KIND_ASPECT = {"room": "16:9", "object": "1:1", "event": "16:9"}


def compose(brief: str, kind: str) -> str:
    """Full per-key prompt: style preamble (base + kind) + entity brief."""
    parts = [STYLE_BASE]
    if kind in KIND_PROMPT:
        parts.append(KIND_PROMPT[kind])
    parts.append(brief)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Real briefs lifted from the game (:rdesc text).
# ---------------------------------------------------------------------------

# Case 1 — microwave states (games/lurkinghorror/kitchen.grue @microwave :rdesc)
MW_CLOSED = "A 1980s microwave oven, door closed, mounted above a kitchen counter."
MW_OPEN = "A 1980s microwave oven, door open, interior visible, mounted above a kitchen counter."
MW_RUNNING = "A 1980s microwave oven running, interior light on, mounted above a kitchen counter."

# Case 2 — the 2nd-floor cross-visible cluster.
# The master plate is the contiguous hallway space the rooms share boundaries on.
CLUSTER_MASTER = (
    "The second floor of a 1980s university computer center at night: an "
    "institutional hallway under fluorescent light, stairs leading up and down at "
    "the far end, a pair of closed elevator doors with call buttons set into the "
    "left wall, and an open doorway on the right opening into a grubby break-room "
    "kitchen (a dirty counter, a refrigerator and a microwave just visible inside). "
    "Empty and eerie."
)
# cs-2nd :rdesc
HALLWAY = (
    "A 1980s university building hallway at night, institutional architecture under "
    "fluorescent light, stairs leading up and down in the background, empty and "
    "eerie. A doorway leads ahead into the kitchen and an elevator with call buttons "
    "stands to one side."
)
# kitchen :rdesc
KITCHEN = (
    "A grubby 1980s university break-room kitchen: a dirty counter under fluorescent "
    "light, no windows, a refrigerator and a microwave against the wall."
)
# cs-elevator-room :rdesc (interior of the car)
ELEVATOR = (
    "The interior of a battered, dirty 1980s elevator: scratched, graffitied "
    "fake-wood panel walls under fluorescent light, with a control panel of floor "
    "buttons on the right wall and the doors straight ahead."
)

# Case 3 — professor + the eight ritual beats (alchemy.grue).
# A neutral character plate to freeze his identity (object-kind brief).
PROF_PLATE = (
    "A university professor: a man in a white lab coat stained with chemicals, "
    "wearing a G.U.E. Tech class ring, with an ambiguously predatory air."
)
# professor-ritual :rdesc catalog
RITUAL = {
    "stage1": "A nervous professor pushes a young man into the center of a chalk pentagram on a lab floor, cutting and redrawing a chalk line with a small knife. Tense, dim chemistry lab.",
    "stage2": "A professor hunched over a lab bench preparing strange apparatus, glancing back with a fervent, obsessive expression. Cluttered chemistry lab, ominous mood.",
    "stage3": "A professor standing inside a second chalk pentagram, mid-ritual: chanting, brandishing strange instruments, one hand pointing toward the viewer. Eerie lab light.",
    "stage4": "A chemistry lab visibly darkening as a professor chants; shadows lengthening and deepening, an oppressive sense of wrongness gathering in the air.",
    "stage5": "A thick black mist forming in a darkened lab, parts of it congealing into a disturbing half-seen shape; a professor calling out, answered from nowhere.",
    "stage6": "A lab freezing and trembling, frost on shuttered windows, the dense black mist churning in cadence with a chant. Bone-rattling dread.",
    "stage7": "Black mist swirling wildly around a lab as a gibbering presence fills the air; the professor sweating, terrified, losing control of the ritual.",
    "stage8-survive": "Seen from below through a trapdoor: a blinding flash of light and smashing equipment in the room above, then fading light and silence. A young man crouched in the tunnel below.",
}


# ---------------------------------------------------------------------------
# Model config. Nano Banana Pro (Gemini 3) is the leading hypothesis and is much
# stronger at multi-image reference / character consistency than the 2.5 flash.
# image_size=None => model default (~1K), which matched the rough style best.
# ---------------------------------------------------------------------------

MODEL_NB = "gemini-2.5-flash-image"
MODEL_NBPRO = "gemini-3-pro-image-preview"
DEFAULT_MODEL = MODEL_NBPRO
DEFAULT_IMAGE_SIZE = None

OUT = Path(__file__).parent / "out"


_CLIENT = None


def _client():
    # Cache a single client; a fresh per-call client can get its httpx transport
    # closed out from under the request ("client has been closed").
    global _CLIENT
    if _CLIENT is None:
        from google import genai

        _CLIENT = genai.Client()
    return _CLIENT


def gen(
    prompt,
    refs=None,
    model=DEFAULT_MODEL,
    aspect_ratio="1:1",
    image_size=DEFAULT_IMAGE_SIZE,
):
    """Low-level generate. `refs` is an optional list of PIL images to condition on."""
    from google.genai import types
    from PIL import Image

    contents = [prompt]
    if refs:
        # Match filfre's phrasing so probe results transfer to production.
        contents = [
            "Generate an image based on the following description, using the "
            "provided reference image(s) for visual consistency.\n\n" + prompt,
            *refs,
        ]
    image_cfg = {"aspect_ratio": aspect_ratio}
    if image_size is not None:
        image_cfg["image_size"] = image_size
    resp = _client().models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(**image_cfg),
        ),
    )
    for part in resp.parts:
        if part.inline_data is not None:
            return Image.open(BytesIO(part.inline_data.data)).convert("RGB")
    raise RuntimeError(f"No image. Text: {getattr(resp, 'text', resp)}")


def slice_strip(img, n):
    """Slice a horizontal model-sheet into n equal-width panels (approximate)."""
    w, h = img.size
    step = w // n
    return [
        img.crop((i * step, 0, (i + 1) * step if i < n - 1 else w, h)) for i in range(n)
    ]


def crop_frac(img, box):
    """Crop by (left, top, right, bottom) fractions in [0,1]."""
    w, h = img.size
    l, t, r, b = box
    return img.crop((int(l * w), int(t * h), int(r * w), int(b * h)))


# ---------------------------------------------------------------------------
# DAG node model.
# ---------------------------------------------------------------------------


@dataclass
class Node:
    key: str
    kind: str  # room | object | event
    mech: str  # prompt | ref | edit | grid | crop
    brief: str = ""  # entity/beat brief (for prompt/ref/edit/grid)
    deps: list[str] = field(default_factory=list)  # node keys whose images we use
    panels: int = 0  # grid: number of panels to slice into
    panel_keys: list[str] = field(default_factory=list)  # grid: output stems
    box: tuple | None = None  # crop: (l,t,r,b) fractions of dep image
    edit_instruction: str = ""  # edit: what to change; brief stays the anchor
    grid_briefs: list[str] = field(default_factory=list)  # grid: per-panel change
    aspect: str | None = None  # override KIND_ASPECT


def node_prompt(n: Node) -> str:
    """The composed prompt for a node (for dry-run display and real calls)."""
    if n.mech == "edit":
        return (
            "Here is an existing illustration. Keep absolutely everything identical "
            "— same subject, same framing, same palette and brush style — and change "
            f"ONLY this: {n.edit_instruction}\n\n"
            f"(For reference, the subject is: {n.brief})"
        )
    if n.mech == "grid":
        labels = ", ".join(f"panel {i + 1}: {b}" for i, b in enumerate(n.grid_briefs))
        return compose(
            "A horizontal model sheet of the SAME object shown in "
            f"{n.panels} side-by-side panels separated by thin black gutters, the "
            f"object drawn identically in each panel except for the noted change. "
            f"{labels}.",
            n.kind,
        )
    return compose(n.brief, n.kind)


def aspect_of(n: Node) -> str:
    if n.aspect:
        return n.aspect
    if n.mech == "grid":
        return "16:9"
    return KIND_ASPECT.get(n.kind, "1:1")


# ---------------------------------------------------------------------------
# Cases. Each is a list of Nodes forming a DAG.
# ---------------------------------------------------------------------------


def case_microwave():
    g = Node(
        key="mw-sheet",
        kind="object",
        mech="grid",
        panels=3,
        panel_keys=["mw-sheet-closed", "mw-sheet-open", "mw-sheet-running"],
        grid_briefs=[
            "door closed",
            "door open, interior visible",
            "running, interior light on, door closed",
        ],
    )
    return [
        # Frozen root.
        Node("mw-closed", "object", "prompt", MW_CLOSED),
        # M1 controls.
        Node("mw-open-prompt", "object", "prompt", MW_OPEN),
        Node("mw-running-prompt", "object", "prompt", MW_RUNNING),
        # M2: fresh generation off the frozen closed ref.
        Node("mw-open-ref", "object", "ref", MW_OPEN, deps=["mw-closed"]),
        Node("mw-running-ref", "object", "ref", MW_RUNNING, deps=["mw-closed"]),
        # M3: in-place edits of the frozen closed image.
        Node(
            "mw-open-edit",
            "object",
            "edit",
            MW_CLOSED,
            deps=["mw-closed"],
            edit_instruction="open the microwave door so the interior is visible.",
        ),
        Node(
            "mw-running-edit",
            "object",
            "edit",
            MW_CLOSED,
            deps=["mw-closed"],
            edit_instruction="the microwave is running, its interior light glowing through the closed door.",
        ),
        # M4: one sheet, sliced.
        g,
    ]


def case_rooms():
    return [
        # Frozen master plate of the contiguous space (the pre-merge reference).
        Node("cluster-master", "room", "prompt", CLUSTER_MASTER),
        # M5 crop: hallway is literally a region of the master (exact seam, no API).
        Node(
            "hallway-crop",
            "room",
            "crop",
            deps=["cluster-master"],
            box=(0.0, 0.0, 0.7, 1.0),
        ),
        # M1 controls (independent renders — expected to drift at the seams).
        Node("hallway-prompt", "room", "prompt", HALLWAY),
        Node("kitchen-prompt", "room", "prompt", KITCHEN),
        Node("elevator-prompt", "room", "prompt", ELEVATOR),
        # M2 reframes off the master, for boundary agreement.
        Node(
            "kitchen-ref",
            "room",
            "ref",
            KITCHEN + " This is the kitchen glimpsed through the doorway in the "
            "reference; keep the counter, refrigerator and microwave consistent with it.",
            deps=["cluster-master"],
        ),
        Node(
            "elevator-ref",
            "room",
            "ref",
            ELEVATOR + " The doors and call-button panel should match the elevator "
            "in the reference hallway.",
            deps=["cluster-master"],
        ),
    ]


def case_professor():
    nodes = [
        # Frozen character plate.
        Node("prof-plate", "object", "prompt", PROF_PLATE),
    ]
    # For each beat: a prompt-only control and a frozen-ref variant.
    for tag, brief in RITUAL.items():
        nodes.append(Node(f"{tag}-prompt", "event", "prompt", brief))
        nodes.append(
            Node(
                f"{tag}-ref",
                "event",
                "ref",
                brief + " The professor is the same man as in the reference.",
                deps=["prof-plate"],
            )
        )
    # M3 chain: stage1 from the plate, then each beat edits the previous beat,
    # probing whether identity survives a dramatically evolving scene.
    chain_tags = list(RITUAL.keys())
    nodes.append(
        Node(
            "chain-stage1",
            "event",
            "ref",
            RITUAL[chain_tags[0]] + " The professor matches the reference.",
            deps=["prof-plate"],
        )
    )
    for prev, tag in zip(chain_tags, chain_tags[1:]):
        nodes.append(
            Node(
                f"chain-{tag}",
                "event",
                "edit",
                RITUAL[tag],
                deps=[f"chain-{prev}"],
                edit_instruction=f"evolve the scene to: {RITUAL[tag]} Keep the professor the same man.",
            )
        )
    return nodes


CASES = {
    "microwave": case_microwave,
    "rooms": case_rooms,
    "professor": case_professor,
}


# ---------------------------------------------------------------------------
# DAG runner.
# ---------------------------------------------------------------------------


def toposort(nodes: list[Node]) -> list[Node]:
    by_key = {n.key: n for n in nodes}
    ordered, seen = [], set()

    def visit(n, stack):
        if n.key in seen:
            return
        if n.key in stack:
            raise ValueError(f"cycle through {n.key}")
        stack.add(n.key)
        for d in n.deps:
            if d not in by_key:
                raise ValueError(f"{n.key} depends on unknown node {d}")
            visit(by_key[d], stack)
        stack.discard(n.key)
        seen.add(n.key)
        ordered.append(n)

    for n in nodes:
        visit(n, set())
    return ordered


def api_calls(nodes: list[Node]) -> int:
    """How many generate_content calls a real run will make (crop is free)."""
    return sum(1 for n in nodes if n.mech != "crop")


def describe(case: str, nodes: list[Node]):
    order = toposort(nodes)
    print(f"\n=== case: {case}  ({len(nodes)} nodes, {api_calls(nodes)} API calls) ===")
    for n in order:
        dep = f"  <- {', '.join(n.deps)}" if n.deps else ""
        extra = ""
        if n.mech == "grid":
            extra = f"  [slice -> {', '.join(n.panel_keys)}]"
        if n.mech == "crop":
            extra = f"  [crop {n.box} of {n.deps[0]}]"
        print(f"  [{n.mech:6}] {n.key} ({n.kind}, {aspect_of(n)}){dep}{extra}")
        print("      " + node_prompt(n).replace("\n\n", " / ").replace("\n", " "))


def _load_existing(outdir, n):
    """Load a node's output(s) from disk into a {key: img} dict, or None if absent."""
    from PIL import Image

    if n.mech == "grid":
        if all((outdir / f"{k}.png").exists() for k in n.panel_keys):
            return {
                k: Image.open(outdir / f"{k}.png").convert("RGB") for k in n.panel_keys
            }
        return None
    p = outdir / f"{n.key}.png"
    if p.exists():
        return {n.key: Image.open(p).convert("RGB")}
    return None


def run_case(case: str, dry: bool = False, only=None, force: bool = False):
    """Run a case as a DAG.

    Resumes by default: any node already on disk is loaded (so it can feed
    downstream deps) instead of regenerated. `only` restricts *generation* to the
    listed keys (everything else is loaded-or-skipped) — use it to make the
    fan-out roots first, review them, then run the full case. `force`
    regenerates even if on disk.
    """
    nodes = CASES[case]()
    if dry:
        describe(case, nodes)
        return
    outdir = OUT / case
    outdir.mkdir(parents=True, exist_ok=True)
    images: dict[str, object] = {}
    only = set(only) if only else None
    for n in toposort(nodes):
        wanted = only is None or n.key in only or bool(set(n.panel_keys) & only)
        existing = _load_existing(outdir, n)
        if existing is not None and not (force and wanted):
            images.update(existing)
            print(f"  [{n.mech}] {n.key} (reuse on-disk)")
            continue
        if not wanted:
            print(f"  [{n.mech}] {n.key} (skip; not in --only and not on disk)")
            continue
        print(f"  [{n.mech}] {n.key} ...", flush=True)
        try:
            if n.mech == "crop":
                img = crop_frac(images[n.deps[0]], n.box)
            elif n.mech == "grid":
                img = gen(node_prompt(n), aspect_ratio=aspect_of(n))
                img.save(outdir / f"{n.key}-raw.png")  # keep the un-sliced sheet
                for stem, panel in zip(n.panel_keys, slice_strip(img, n.panels)):
                    panel.save(outdir / f"{stem}.png")
                    images[stem] = panel
            else:
                refs = [images[d] for d in n.deps] if n.deps else None
                img = gen(node_prompt(n), refs=refs, aspect_ratio=aspect_of(n))
            images[n.key] = img
            if n.mech != "grid":
                img.save(outdir / f"{n.key}.png")
            print(f"     -> {outdir / (n.key + '.png')}")
        except Exception as e:  # keep going; one bad node shouldn't sink the sweep
            print(f"     !! failed: {e}")
    make_sheet(case)


def make_sheet(case: str):
    """Assemble a contact sheet of every PNG in out/<case>/ for side-by-side review."""
    from PIL import Image, ImageDraw

    outdir = OUT / case
    pngs = sorted(p for p in outdir.glob("*.png") if p.name != "_sheet.png")
    if not pngs:
        print(f"  (no images in {outdir}; nothing to sheet)")
        return
    cols = 3
    cell, pad, label_h = 360, 10, 22
    rows = (len(pngs) + cols - 1) // cols
    W = cols * cell + (cols + 1) * pad
    H = rows * (cell + label_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), (8, 13, 16))
    draw = ImageDraw.Draw(sheet)
    for i, p in enumerate(pngs):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = pad + r * (cell + label_h + pad)
        im = Image.open(p).convert("RGB")
        im.thumbnail((cell, cell))
        sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        draw.text((x + 2, y + cell + 4), p.stem, fill=(219, 230, 227))
    path = outdir / "_sheet.png"
    sheet.save(path)
    print(f"  -> {path}")


def main():
    args = sys.argv[1:]
    if not args or args == ["--list"]:
        for name, fn in CASES.items():
            describe(name, fn())
        return
    if args[0] == "--dry-run":
        for c in args[1:] or list(CASES):
            run_case(c, dry=True)
        return
    if args[0] == "--sheet":
        for c in args[1:] or list(CASES):
            make_sheet(c)
        return
    # case run: positional case names + optional --only KEY [KEY...] / --force
    only, force, cases = [], False, []
    it = iter(args)
    for a in it:
        if a == "--force":
            force = True
        elif a == "--only":
            only = list(it)  # consume the rest as keys
            break
        else:
            cases.append(a)
    if only and len(cases) != 1:
        print("  !! --only requires exactly one case")
        return
    for c in cases:
        if c not in CASES:
            print(f"  ?? unknown case: {c} (have: {', '.join(CASES)})")
            continue
        run_case(c, dry=False, only=only or None, force=force)


if __name__ == "__main__":
    main()
