"""Frame-by-frame, seeded procedural shorts with two animated characters."""
from array import array
from dataclasses import dataclass
import math
import random
import subprocess
import wave

from PIL import Image, ImageDraw

from creative import MUSIC
from library import finish
from providers import save_json
from visual_styles import MODERN_PIXEL, RETRO_PIXEL, pixel_style

W, H, FPS = 320, 180, 24

@dataclass(frozen=True)
class Plot:
    key: str
    title: str
    setting: str
    prop: str
    lines: tuple
    events: tuple

PLOTS = (
    Plot("moon", "Express Delivery to the Moon", "market", "moon",
         ("One express delivery. To the moon. How hard can it be?",
          "Checking label. It says: do not expose to moonlight.",
          "That feels like a note they should put on the front.",
          "The moon is not the customer. It is the package.",
          "Catch that handle! I have a very stupid idea.",
          "Delivery complete. Please rate your moon."),
         ("walk", "read", "open", "escape", "catch", "finish")),
    Plot("tea", "The Last Cup on Platform Nine", "station", "kettle",
         ("Last train, last cup. We can absolutely make both.",
          "Moving kettle detected. Why does your tea have legs?",
          "It's a deluxe kettle. I assumed that meant a nicer handle.",
          "It is running toward the departure bell. Follow me!",
          "There! Catch it with the cup. Quickly!",
          "Your tea has departed. Your cup is on time."),
         ("read", "open", "escape", "walk", "catch", "finish")),
    Plot("cloud", "Weather, With a Side of Toast", "greenhouse", "cloud",
         ("I ordered a toaster. This box feels suspiciously damp.",
          "Warning. That is a miniature thundercloud.",
          "Can it toast bread? Because I already bought jam.",
          "Open the greenhouse vents! It's filling up with rain.",
          "Wait. Bring it gently over the seedlings.",
          "Garden watered. Toast remains a long-term goal."),
         ("open", "read", "escape", "walk", "catch", "finish")),
    Plot("seed", "The Seed That Missed Its Stop", "station", "seed",
         ("The last seed shipment is rolling right off the deck!",
          "It is avoiding the dark, not avoiding you.",
          "Hang on. I've got a pocket torch and a sandwich.",
          "Shine it over here. Stop waving the sandwich.",
          "There you go, little guy. Straight into the planter.",
          "Shipment has grown roots. Refund request denied."),
         ("escape", "read", "walk", "open", "catch", "finish")),
)
PALETTES = (
    ("#101534", "#332058", "#fc8a83", "#55477a", "#302d5a", "#151d36", "#53e6ca"),
    ("#10273f", "#155569", "#ffc47d", "#326d77", "#1b444f", "#132f40", "#f5ab72"),
    ("#20152d", "#563557", "#efaa79", "#744962", "#3e2a49", "#281e37", "#9fe0bc"),
)
NAMES = (("Mina", "Pip"), ("Tara", "Bolt"), ("Rani", "Zip"), ("Nila", "Dot"), ("Asha", "Tick"))

@dataclass(frozen=True)
class Cast:
    courier: str
    robot: str
    coat: str
    casing: str
    scarf: str


def production(seed, previous):
    rng = random.Random(seed)
    available = [plot for plot in PLOTS if plot.key not in previous[-len(PLOTS) + 1:]]
    plot = rng.choice(available or list(PLOTS))
    names = rng.choice(NAMES)
    colors = rng.choice((("#f66f63", "#b9edf4", "#ffd774"), ("#55d1b6", "#f7cc9a", "#fb839a"),
                         ("#f8b75a", "#d3bdf4", "#72ebd3"), ("#bd92ff", "#bed8b9", "#ff976f")))
    return plot, Cast(*names, *colors), rng.choice(PALETTES), rng.choice(MUSIC), rng.randrange(3)


def tween(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def city_layer(seed, palette, setting):
    rng = random.Random(seed)
    sky, glow, sun, far, near, floor, accent = palette
    image = Image.new("RGB", (W, H), sky)
    d = ImageDraw.Draw(image)
    for y in range(0, 120, 5):
        blend = tween(y / 145)
        a = tuple(int(sky[i:i + 2], 16) for i in (1, 3, 5))
        b = tuple(int(glow[i:i + 2], 16) for i in (1, 3, 5))
        d.rectangle((0, y, W, y + 4), fill=tuple(round(x + (z - x) * blend) for x, z in zip(a, b)))
    for _ in range(95):
        x, y = rng.randrange(W), rng.randrange(7, 110)
        d.point((x, y), fill=rng.choice((far, "#ffe5bd", "#d4b9e9")))
    d.ellipse((218, 13, 270, 65), fill=sun)
    for y in range(39, 66, 6):
        d.line((215, y, 272, y), fill=glow)
    for x in range(-8, W, 13):
        height = rng.randrange(7, 36)
        d.rectangle((x, 118 - height, x + rng.randrange(8, 17), 123), fill=far)
        if rng.random() < 0.6:
            d.line((x + 4, 114 - height, x + 4, 120 - height), fill=sun)
    if setting == "greenhouse":
        for x in range(14, W, 53):
            d.line((x, 130, x, 34, x + 27, 18, x + 53, 34, x + 53, 130), fill=near, width=3)
        d.line((0, 63, W, 63), fill=near, width=3)
        for x in (31, 239, 275):
            d.rectangle((x, 118, x + 30, 130), fill="#704956", outline="#332840")
            d.line((x + 2, 119, x + 28, 119), fill="#c37d72", width=2)
            for dx in (5, 14, 24):
                d.line((x + dx, 118, x + dx, 107), fill="#639e78", width=2)
                d.polygon(((x + dx, 112), (x + dx - 5, 106), (x + dx - 6, 111)), fill="#8bd091")
                d.polygon(((x + dx, 109), (x + dx + 5, 103), (x + dx + 5, 108)), fill="#97df99")
    elif setting == "station":
        d.polygon(((0, 41), (52, 23), (212, 29), (319, 47), (319, 55), (0, 52)), fill=near)
        for x in (18, 158, 297):
            d.rectangle((x, 48, x + 4, 132), fill=near)
            d.rectangle((x, 54, x + 5, 58), fill=accent)
        d.line((0, 104, W, 104), fill=accent, width=2)
    else:
        for x, roof in ((18, 73), (255, 78)):
            d.rectangle((x, roof, x + 51, 132), fill=near)
            d.rectangle((x + 6, roof + 22, x + 43, 123), fill=glow)
            for stripe in range(7):
                d.rectangle((x - 4 + stripe * 8, roof + 11, x + 3 + stripe * 8, roof + 17),
                            fill=sun if stripe % 2 else far)
            d.rectangle((x + 3, roof + 49, x + 47, roof + 54), fill=far)
    d.rectangle((0, 127, W, H), fill=floor)
    d.line((0, 126, W, 126), fill=accent, width=2)
    for y in (136, 150, 171):
        d.line((0, y, W, y), fill=near)
    for x in range(-80, 430, 25):
        d.line((int(160 + (x - 160) * 0.35), 128, x, H), fill=near)
    return image


def courier(d, x, y, colors, phase, walk, hand, talk, emotion, mirror=False):
    x, y = round(x), round(y)
    coat, scarf = colors
    ink, skin = "#17152d", "#edab85"
    stride = round(math.sin(phase) * 5) if walk else 0
    y -= int(abs(math.sin(phase)) * 2) if walk else 0
    d.ellipse((x - 12, y - 3, x + 12, y + 2), fill="#101227")
    d.line((x - 4, y - 12, x - 4 + stride, y - 2), fill="#8191aa", width=4)
    d.line((x + 4, y - 12, x + 4 - stride, y - 2), fill="#595a86", width=4)
    d.line((x - 6 + stride, y, x - 1 + stride, y), fill="#eee3dd", width=3)
    d.line((x + 2 - stride, y, x + 7 - stride, y), fill="#eee3dd", width=3)
    d.rectangle((x - 9, y - 28, x + 9, y - 11), fill=ink)
    d.rectangle((x - 7, y - 27, x + 7, y - 13), fill=coat)
    d.line((x + 1, y - 26, x + 1, y - 14), fill=ink)
    d.rectangle((x - 7, y - 29, x + 7, y - 25), fill=scarf)
    flag = round(math.sin(phase * 0.49) * 2)
    d.polygon(((x - 6, y - 28), (x - 16, y - 25 + flag), (x - 15, y - 21 + flag), (x - 4, y - 26)), fill=scarf)
    direction = -1 if mirror else 1
    end_x = x + direction * (16 if hand else 10)
    end_y = y - (29 if hand else 17) + (0 if hand else stride // 2)
    d.line((x + 6 * direction, y - 25, end_x, end_y), fill=coat, width=4)
    d.rectangle((end_x - 2, end_y - 1, end_x + 1, end_y + 2), fill=skin)
    d.rectangle((x - 7, y - 42, x + 7, y - 28), fill=ink)
    d.rectangle((x - 5, y - 38, x + 6, y - 30), fill=skin)
    d.rectangle((x - 8, y - 44, x + 4, y - 37), fill="#262143")
    d.rectangle((x - 5, y - 45, x + 4, y - 43), fill=scarf)
    d.line((x - 5, y - 39, x + 9, y - 39), fill=scarf, width=2)
    eye_y = y - 35
    eye = "#f9f3e6" if emotion == "shock" else ink
    for dx in (-2, 4):
        d.point((x + dx, eye_y), fill=eye)
    if talk or emotion == "shock":
        d.rectangle((x + 1, y - 33, x + 4, y - 31 - int(talk == 1)), fill=ink)


def robot(d, x, y, casing, phase, hand, talk, emotion):
    x, y = round(x), round(y)
    y += round(math.sin(phase * 0.63) * 2)
    d.ellipse((x - 12, y + 2, x + 12, y + 6), fill="#101227")
    d.ellipse((x - 8, y - 6, x + 8, y + 3), fill="#583975")
    d.polygon(((x - 5, y - 6), (x + 5, y - 6), (x + 2, y + 3 + int(phase % 2)),
               (x - 2, y + 2)), fill="#9dfefa")
    d.rounded_rectangle((x - 11, y - 29, x + 11, y - 7), 4, fill=casing, outline="#282149")
    d.rounded_rectangle((x - 8, y - 25, x + 8, y - 13), 3, fill="#212142")
    d.line((x, y - 29, x + 3, y - 36), fill=casing)
    d.ellipse((x + 1, y - 38, x + 5, y - 34), fill="#ffd184")
    for dx in (-4, 4):
        d.line((x + dx, y - 21, x + dx, y - (17 if emotion == "shock" else 19)), fill="#75fcdb", width=2)
    if talk:
        d.line((x - 2, y - 16, x + 2, y - 16), fill="#97f9fd")
    d.line((x - 10, y - 18, x - 16, y - (27 if hand else 15)), fill=casing, width=2)
    d.line((x + 10, y - 18, x + 15, y - 15), fill=casing, width=2)


def object_art(d, prop, x, y, opened, time):
    x, y = round(x), round(y)
    if not opened:
        d.rectangle((x - 10, y - 10, x + 10, y + 5), fill="#cd7b54", outline="#382442")
        d.line((x - 10, y - 9, x + 10, y - 9), fill="#ffc37f", width=2)
        d.line((x + 1, y - 9, x + 1, y + 3), fill="#ffe18d", width=3)
        return
    if prop == "moon":
        d.ellipse((x - 10, y - 10, x + 10, y + 10), fill="#ffd481", outline="#fff3ad")
        for dx, dy, r in ((-4, -2, 2), (3, 4, 3), (5, -5, 2)):
            d.ellipse((x + dx - r, y + dy - r, x + dx + r, y + dy + r), fill="#e9a879")
    elif prop == "kettle":
        d.arc((x + 4, y - 8, x + 15, y + 6), 260, 115, fill="#f6cc89", width=2)
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill="#f8a974", outline="#ffe4a8")
        d.polygon(((x - 7, y), (x - 14, y - 6), (x - 8, y - 3)), fill="#ffe4a8")
        stride = round(math.sin(time * 15) * 4)
        d.line((x - 4, y + 6, x - 4 + stride, y + 12), fill="#ffe4a8", width=2)
        d.line((x + 4, y + 6, x + 4 - stride, y + 12), fill="#ffe4a8", width=2)
    elif prop == "cloud":
        for dx, dy in ((-7, 1), (1, -4), (7, 0)):
            d.ellipse((x + dx - 6, y + dy - 5, x + dx + 6, y + dy + 5), fill="#d1c9f7")
        for dx in (-7, -1, 5, 10):
            yy = y + 7 + int((time * 22 + dx) % 11)
            d.line((x + dx, yy, x + dx - 1, yy + 3), fill="#83dffc")
    else:
        d.ellipse((x - 7, y - 3, x + 7, y + 8), fill="#f6a779", outline="#fac587")
        d.line((x, y, x + 1, y - 10), fill="#98f594", width=2)
        d.ellipse((x, y - 11, x + 6, y - 7), fill="#98f594")


def draw_frame(bg, plot, cast, palette, variant, index, event, t, duration, clock, talk):
    p = t / duration
    motion = tween((p - 0.08) / 0.75)
    image = bg.copy()
    d = ImageDraw.Draw(image)
    moving = event in {"walk", "escape", "catch"}
    if event == "walk":
        x, rx = 48 + motion * 100, 81 + motion * 102
    elif event == "escape":
        x, rx = 103 + motion * 29, 177 + motion * 24
    elif event == "catch":
        x, rx = 92 + motion * 67, 206 - motion * 26
    else:
        x, rx = 110, 183
    if event == "escape":
        prop_x, prop_y = 146 + motion * 110, 111 - 46 * motion - abs(math.sin(t * 5)) * 8
    elif event == "catch":
        prop_x, prop_y = 241 - motion * 72, 58 + motion * 53
    else:
        prop_x = 149 + (9 if event == "finish" else 0)
        prop_y = 121 if event == "read" else 113 - 15 * (tween(p * 2) if event == "open" else 0)
    if plot.prop == "kettle" and event == "escape":
        prop_y = 124 - abs(math.sin(t * 8)) * 9
    for n in range(11):
        point_x = round((44 + n * 31 - clock * (11 + n % 4)) % W)
        point_y = 60 + (n * 13) % 67 + round(math.sin(clock * 2 + n) * 3)
        d.point((point_x, point_y), fill=palette[2])
    courier(d, x, 135, (cast.coat, cast.scarf), t * (13 if moving else 6), moving,
            event in {"open", "catch", "finish"}, talk if index % 2 == 0 else 0,
            "shock" if event == "escape" else "okay")
    robot(d, rx, 129, cast.casing, clock * 9, event in {"read", "catch"},
          talk if index % 2 else 0, "shock" if event == "escape" else "okay")
    opened = (any(beat in {"open", "escape"} for beat in plot.events[:index])
              or event in {"escape", "catch", "finish"} or event == "open" and p > 0.38)
    if plot.prop == "cloud" and opened and event in {"escape", "catch", "finish"}:
        for k in range(24):
            yy = round(prop_y + 12 + ((clock * (38 + k % 4) + k * 11) % 48))
            xx = round(prop_x - 23 + k * 13 % 51 - (yy - prop_y) * 0.23)
            if yy < 136:
                d.line((xx, yy, xx - 1, yy + 4), fill="#86b8dd")
    if plot.prop == "cloud" and event == "finish":
        for k, xx in enumerate(range(135, 183, 9)):
            height = round(10 + tween(p * 2) * (13 + k % 3 * 4))
            d.rectangle((xx - 4, 126, xx + 4, 132), fill="#b26a60")
            d.line((xx, 126, xx, 126 - height), fill="#5eac80", width=2)
            d.ellipse((xx - 4, 122 - height, xx + 4, 127 - height), fill="#a0e3a4")
            if p > 0.38:
                d.point((xx, 121 - height), fill="#f9cc86")
    object_art(d, plot.prop, prop_x, prop_y, opened, clock)
    if opened:
        for k in range(7):
            angle = k * math.tau / 7 + clock * 0.9
            radial = 13 + 7 * ((clock + k * 0.13) % 1)
            px = round(prop_x + math.cos(angle) * radial)
            py = round(prop_y + math.sin(angle) * radial * 0.65)
            d.line((px, py, px + 1, py), fill=palette[2])
    for k in (0, 1, 2):
        edge = (int((k * 128 - clock * 16) % 440) - 55)
        d.rectangle((edge, 152, edge + 7, 180), fill="#11152a")
        d.rectangle((edge - 2, 149, edge + 9, 152), fill=palette[3])
    zoom = {"walk": 1.12, "read": 1.55, "open": 1.43, "escape": 1.18,
            "catch": 1.36, "finish": 1.29}[event]
    zoom += (0.06 + variant * 0.02) * tween(p)
    center_x = 160 if event == "walk" else (x * 0.33 + rx * 0.28 + prop_x * 0.39)
    center_y = 101 if event in {"read", "open", "catch"} else 90
    width, height = round(W / zoom), round(H / zoom)
    left = min(W - width, max(0, round(center_x - width / 2)))
    top = min(H - height, max(0, round(center_y - height / 2)))
    image = image.crop((left, top, left + width, top + height)).resize((W, H), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(image)
    if index == 0:
        d.rectangle((14, 11, 17, 19), fill=palette[2])
        d.text((23, 10), plot.title.upper(), fill="#fff2dd")
    if index in (2, 4) and t < 0.32:
        # Animated shutter covers the cut and then clears the new angle.
        cover = round((1 - tween(t / 0.32)) * W)
        if variant % 2:
            d.rectangle((W - cover, 0, W, H), fill=palette[0])
        else:
            d.rectangle((0, 0, cover, H), fill=palette[0])
    if event == "finish" and p > 0.87:
        image = Image.blend(image, Image.new("RGB", (W, H), palette[0]), tween((p - 0.87) / 0.13) * 0.92)
    return image

def write_motion(tool, output, bg, plot, cast, palette, variant, index, duration, elapsed, cues):
    command = [tool, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0",
               "-vf", "scale=1280:720:flags=neighbor", "-an", "-pix_fmt", "yuv420p",
               "-c:v", "libx264", "-preset", "veryfast", "-threads", "4", str(output)]
    with (output.parent / "motion.log").open("w+b") as errors:
        with subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors) as encoder:
            try:
                for frame in range(duration * FPS):
                    t = frame / FPS
                    speaking = any(start <= t < end for start, end, _ in cues)
                    mouth = (1 + frame // 3 % 2) if speaking else 0
                    art = draw_frame(bg, plot, cast, palette, variant, index, plot.events[index],
                                     t, duration, elapsed + t, mouth)
                    encoder.stdin.write(art.tobytes())
            except BrokenPipeError:
                pass
            finally:
                encoder.stdin.close()
            if encoder.wait() != 0:
                errors.seek(0)
                raise RuntimeError(errors.read().decode("utf-8", "replace"))


def chiptune(path, duration, mood, seed, beats, modern=False):
    rng = random.Random(seed ^ 0xF235)
    rate = 16000
    step = {"playful": 0.24, "warm": 0.36, "suspenseful": 0.31, "kinetic": 0.21}[mood]
    base = rng.choice((98, 110, 130.81))
    intervals = (0, 7, 12, 7, 3, 10, 15, 10) if mood == "suspenseful" else (0, 7, 12, 14, 4, 7, 16, 12)
    notes = [base * 2 ** (interval / 12) for interval in intervals]
    audio = array("h")
    for frame in range(duration * rate):
        t = frame / rate
        count = int(t / step)
        age = t - count * step
        lead = notes[count % len(notes)] * 2
        low = notes[(count // 8 * 4) % len(notes)] / 2
        melody = (math.sin(math.tau * lead * t) + 0.35 * math.sin(math.tau * lead * 3 * t)) * math.exp(-age * 11)
        bass = math.sin(math.tau * low * t) * math.exp(-(t % (step * 2)) * 6)
        value = 1450 * melody + 1600 * bass
        if modern:
            shimmer = math.sin(math.tau * lead * t + .27 * math.sin(math.tau * 3.2 * t))
            pad = math.sin(math.tau * low * 2 * t) + .28 * math.sin(math.tau * low * 3 * t)
            value = 1950 * bass + 1350 * shimmer * math.exp(-age * 6) + 1180 * pad
        scene_cue = min((t - beat for beat in beats if 0 <= t - beat < 0.32), default=None)
        if scene_cue is not None:
            value += 5000 * math.sin(math.tau * (640 + 1700 * scene_cue) * scene_cue) * math.exp(-scene_cue * 13)
        audio.append(round(value * min(1, t * 4, (duration - t) * 2)))
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes(audio.tobytes())


def local_movie(args, root, config, ffmpeg_path, ffmpeg, captions, stamp, seed):
    from studio import assemble, select_voices

    import asyncio
    import json
    import uuid

    duration = args.duration if args.duration is not None else 35
    if not 24 <= duration <= 120:
        raise ValueError("Local random animation supports 24–120 seconds. Studio supports 15–3600 seconds.")
    from studio import STYLES

    style = args.style or MODERN_PIXEL
    if style.isdecimal() and 0 <= int(style) <= len(STYLES):
        style = STYLES[int(style) - 1] if int(style) else MODERN_PIXEL
    style = pixel_style(style)
    if style.casefold() == "auto":
        style = MODERN_PIXEL
    if style not in {MODERN_PIXEL, RETRO_PIXEL} or args.format == "portrait":
        raise ValueError("The local renderer supports landscape Modern 3D Pixel Cinematic and explicit Retro Pixel Art. Other styles use Studio.")
    modern = style == MODERN_PIXEL
    if args.mode == "cyber" or args.plan_only or args.resume or args.prompt or args.topic:
        raise ValueError("Local random animation generates its own general story. Use Studio for a supplied topic or prompt.")
    if args.characters not in (None, 2) or args.voice:
        raise ValueError("The local random animation uses two characters with automatically selected voices.")
    if args.language and args.language.casefold() != "english":
        raise ValueError("Local random stories use English dialogue. Studio accepts other languages.")
    jobs = root / config["output_folder"] / "random"
    recent = sorted(jobs.glob("*/production.json"), key=lambda path: path.stat().st_mtime)
    previous = [json.loads(path.read_text(encoding="utf-8"))["concept"] for path in recent[-len(PLOTS):]]
    plot, cast, palette, mood, variant = production(seed, [] if args.seed is not None else previous)
    tool = ffmpeg_path()
    job = (jobs / f"{seed:08x}-{uuid.uuid4().hex[:6]}").resolve()
    job.mkdir(parents=True)
    print(f"{style} | local procedural animation | seed {seed} | {plot.title}", flush=True)
    print(f"Job: {job}", flush=True)
    names = (cast.courier, cast.robot)
    story = {"title": plot.title, "style": style, "summary": (
        f"{cast.courier}, an optimistic courier, and {cast.robot}, a literal-minded robot, "
        f"try to deal with a runaway {plot.prop} at the {plot.setting}."
    ), "cast": [{"name": names[0], "gender": "Female"}, {"name": names[1], "gender": "Male"}]}
    spec = {"mode": "general", "language": "English", "locale": args.locale or "en-US", "voices": {},
            "ratio": "1280:720", "duration": duration}
    voices = asyncio.run(select_voices(spec, story, False))
    weights = {"read": 5, "walk": 6, "escape": 6, "open": 5, "catch": 6, "finish": 5}
    cumulative = 0
    shots = []
    beats = []
    total = sum(weights[event] for event in plot.events)
    for index, event in enumerate(plot.events):
        end = round(duration * (cumulative + weights[event]) / total)
        start = round(duration * cumulative / total)
        cumulative += weights[event]
        if event in {"open", "escape", "catch", "finish"}:
            beats.append(start + (end - start) * (0.38 if event == "open" else 0.12))
        mood_name = {"walk": "happy", "escape": "scared", "read": "serious", "open": "surprised",
                     "catch": "scared", "finish": "sarcastic"}[event]
        shots.append({"seconds": end - start, "opening": f"{plot.setting.capitalize()}, {event} shot",
                      "action": f"{names[0]} and {names[1]} react to the {plot.prop}.", "cast": list(names),
                      "dialogue": [{"speaker": names[index % 2], "line": plot.lines[index], "emotion": mood_name}]})
    chiptune(job / "score.wav", duration, mood, seed, beats, modern=modern)
    from studio import render_shot

    if modern:
        try:
            from modern_motion import Renderer, render_motion

            renderer = Renderer(plot, seed, palette)
        except (ImportError, OSError) as error:
            raise RuntimeError("Install requirements.txt and enable OpenGL 3.3 to render Modern 3D Pixel Cinematic.") from error
        except Exception as error:
            raise RuntimeError(f"Modern 3D renderer could not initialize OpenGL: {error}") from error
    else:
        bg = city_layer(seed, palette, plot.setting)

    elapsed = 0
    try:
        for index, shot in enumerate(shots):
            folder = job / f"shot{index + 1:04d}"
            folder.mkdir()
            source = folder / "motion.mp4"
            print(f"Animating scene {index + 1}/{len(shots)}", flush=True)

            def make_motion(cues, _windows):
                if modern:
                    render_motion(renderer, tool, source, plot, cast, variant, index, shot["seconds"], elapsed, cues)
                else:
                    write_motion(tool, source, bg, plot, cast, palette, variant, index, shot["seconds"], elapsed, cues)

            render_shot(tool, ffmpeg, captions, shot, voices, source, folder, spec["ratio"], make_motion=make_motion)
            elapsed += shot["seconds"]
    finally:
        if modern:
            renderer.close()
    video = assemble(tool, ffmpeg, stamp, root, job, story, shots, spec, config)
    save_json(job / "production.json", {"renderer": "procedural-3d" if modern else "procedural-sprites", "seed": seed, "concept": plot.key,
                                       "story": story, "spec": spec, "shots": shots,
                                       "palette": palette, "music": mood, "voice_assignments": voices})
    finish(job, story["title"], video, duration, spec["ratio"], "English", "procedural-3d" if modern else "procedural-sprites")
