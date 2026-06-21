import sys
from io import BytesIO
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

# Nano Banana (original) vs Nano Banana Pro (Gemini 3). The Gemini app now
# defaults to Pro, which is the likeliest reason UI output looks different.
MODEL_NANOBANANA = "gemini-2.5-flash-image"
MODEL_NANOBANANA_PRO = "gemini-3-pro-image-preview"
DEFAULT_MODEL = MODEL_NANOBANANA_PRO
DEFAULT_IMAGE_SIZE = "2k"

OUT = Path(__file__).parent / "out"

STONE = (
    "A single small smooth stone, shiny and glowing with a blazing inner light, a "
    "strange symbol carved into it, resting alone on a plain neutral background "
    "(inventory item)."
)

LAB = (
    "A large 1980s university computer lab at night: rows of CRT monitors and old "
    "terminals on desks, pizza boxes and empty Coke cans scattered on the tables, "
    "banners and posters on the walls, dim fluorescent lighting. Completely empty "
    "of people."
)

ALCHEMY = (
    "An ultramodern, fully-equipped university chemistry lab: gleaming glassware and fume"
    "hoods, benches crowded with apparatus and tangled tubing, a low stone archway set into one wall,"
    "cold fluorescent light. Empty of people."
)

# Fixed test subject: the cave-altar :rdesc (matches the user's reference image).
ALTAR = (
    "The bottom of a huge cave-like vault reinforced with massive beams of wood, "
    "iron and steel. In the center a great flat stone slab serves as an altar, "
    "carved with strange, disturbing symbols and obscured by rusty red stains. An "
    "iron plate is set in the rough concrete floor. Dim, ominous light. Empty."
)

# Real @hacker :rdesc (black bg). The blank-smudge face is the key "unfinished
# tell" we want to preserve; the round-6 EARTH run over-resolved it.
HACKER = (
    "A scruffy, innocent-looking young man in his twenties: blue jeans, an old work "
    "shirt, worn running shoes, and a large ring of keys hanging from his belt. He "
    "looks like he needs a bath. Solid black background."
)

# A second, contrasting character (no glow, plain) to test generality.
GUARD = (
    "A heavyset, bored night security guard in a rumpled grey uniform shirt, a "
    "clip-on tie, and a flashlight on his belt, standing slouched. Solid black "
    "background."
)

STONE = (
    "A single small smooth stone, shiny and glowing with a blazing inner light, a "
    "strange symbol carved into it, resting alone on a plain neutral background "
    "(inventory item)."
)

SNOW = (
    "A deserted campus street at night in the worst blizzard of winter: an arctic "
    "wasteland of howling wind and deep drifting snow, streetlights barely visible "
    "across the road, institutional buildings looming unlit in the dark. Empty and "
    "bitterly cold."
)

# Style descriptors
STYLE = (
    "Style: Rough colored-charcoal sketch on solid black paper, suitable only as a rough mockup for a human "
    "artist to complete in graphic novel style, but little detail."
)

FIGURE = (
    "Abstract, upright, full-body, standing-up character sketch with vague features."
)

OBJECT = "Isolated against solid black background."


def compose(parts):
    return "\n\n".join(parts)


def gen(
    prompt,
    model=DEFAULT_MODEL,
    aspect_ratio="16:9",
    image_size=DEFAULT_IMAGE_SIZE,
    temperature=None,
):
    print(prompt)
    client = genai.Client()
    image_cfg = {"aspect_ratio": aspect_ratio}
    if image_size is not None:
        image_cfg["image_size"] = image_size
    cfg = {
        "response_modalities": ["IMAGE"],
        "image_config": types.ImageConfig(**image_cfg),
    }
    if temperature is not None:
        cfg["temperature"] = temperature
    resp = client.models.generate_content(
        model=model, contents=[prompt], config=types.GenerateContentConfig(**cfg)
    )
    for part in resp.parts:
        if part.inline_data is not None:
            return Image.open(BytesIO(part.inline_data.data)).convert("RGB")
    raise RuntimeError(f"No image. Text: {getattr(resp, 'text', resp)}")


# Named subjects available to both single jobs and the matrix sweep.
SUBJECTS = {
    "altar": [STYLE, ALTAR],
    "lab": [STYLE, LAB],
    "alchemy": [STYLE, ALCHEMY],
    "snow": [STYLE, SNOW],
    "hacker": [STYLE, FIGURE, OBJECT, HACKER],
    "guard": [STYLE, FIGURE, OBJECT, GUARD],
    "stone": [STYLE, OBJECT, STONE],
}

JOBS = {
    "altar": lambda: gen(compose(SUBJECTS["altar"])),
    "lab": lambda: gen(compose(SUBJECTS["lab"])),
    "alchemy": lambda: gen(compose(SUBJECTS["alchemy"])),
    "snow": lambda: gen(compose(SUBJECTS["snow"])),
    "hacker": lambda: gen(compose(SUBJECTS["hacker"])),
    "guard": lambda: gen(compose(SUBJECTS["guard"])),
    "stone": lambda: gen(compose(SUBJECTS["stone"])),
}

# Matrix axes for sweeps. Add/remove values to widen or narrow the search.
MATRIX_MODELS = {
    "nb": MODEL_NANOBANANA,
    "nbpro": MODEL_NANOBANANA_PRO,
}
MATRIX_SIZES = {
    "1k": None,  # None => model default (~1K)
    "2k": "2K",
}
MATRIX_ASPECTS = {
    "16x9": "16:9",
}


def run_matrix(subjects):
    """Sweep each subject across model x size x aspect; one PNG per combo."""
    OUT.mkdir(exist_ok=True)
    for subject in subjects:
        if subject not in SUBJECTS:
            print(f"  ?? unknown subject: {subject}")
            continue
        prompt = compose(SUBJECTS[subject])
        for mk, model in MATRIX_MODELS.items():
            for sk, image_size in MATRIX_SIZES.items():
                for ak, aspect in MATRIX_ASPECTS.items():
                    name = f"{subject}_{mk}_{sk}_{ak}"
                    print(f"  generating {name} ...", flush=True)
                    try:
                        img = gen(
                            prompt,
                            model=model,
                            aspect_ratio=aspect,
                            image_size=image_size,
                        )
                        path = OUT / f"{name}.png"
                        img.save(path)
                        print(f"     -> {path}")
                    except Exception as e:
                        print(f"     !! failed: {e}")


def main():
    args = sys.argv[1:]
    if args == ["--list"]:
        for k in JOBS:
            print(k)
        print("(matrix subjects:", ", ".join(SUBJECTS), ")")
        return
    if args and args[0] == "--matrix":
        subjects = args[1:] or ["altar"]
        run_matrix(subjects)
        return

    names = list(JOBS) if (not args or args == ["all"]) else args
    OUT.mkdir(exist_ok=True)
    for name in names:
        if name not in JOBS:
            print(f"  ?? unknown job: {name}")
            continue
        print(f"  generating {name} ...", flush=True)
        try:
            img = JOBS[name]()
            path = OUT / f"{name}.png"
            img.save(path)
            print(f"     -> {path}")
        except Exception as e:
            print(f"     !! failed: {e}")


if __name__ == "__main__":
    main()
