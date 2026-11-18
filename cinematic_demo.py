"""Hand-directed illustrated split-screen episode with articulated 2D layers."""
from array import array
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import math
import os
import random
import subprocess
import uuid
import wave

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from providers import save_json
from split_screen import OUTPUT_RATIO, compose_split, split_layout

W, H, FPS = 810, 720, 24
INK = "#0b1324"
TEAL = "#79dfd1"
TITLE = "एक क्लिक… और सब खत्म?"
STYLE = "2D Cinematic Illustration"

@dataclass(frozen=True)
class Beat:
    seconds: int
    description: str
    line: str
    emotion: str
    marker: str
    reply: str = ""


SHOTS = (
    Beat(7, "Walking in the rain. A bank warning lights Rahul's phone.",
         "राहुल घर लौट रहा था। तभी फ़ोन पर संदेश आया, आपका बैंक खाता आज रात बंद हो जाएगा।",
         "serious", "संदेश"),
    Beat(7, "He opens the link and mistakes an imitation page for his bank.",
         "डर के मारे उसने संदेश की कड़ी खोल दी। सामने बैंक जैसा पन्ना था। राहुल ने अपनी जानकारी भर दी।",
         "scared", "जानकारी"),
    Beat(6, "An unfamiliar payment alert interrupts the routine.",
         "फिर एक और सूचना आई। खाते से पैसे कटे थे। राहुल ने तो कोई भुगतान किया ही नहीं था।",
         "surprised", "पैसे"),
    Beat(7, "Meera sees the screen, steps in and stops him from touching the message again.",
         "मीरा ने स्क्रीन देखी। उसने राहुल का हाथ रोक लिया।", "serious", "रोक",
         "रुक। बैंक का असली ऐप खोल।"),
    Beat(7, "He opens the official app and contacts the bank.",
         "राहुल ने इस बार असली ऐप खोला, बैंक को फ़ोन किया और उस भुगतान की शिकायत की।",
         "neutral", "शिकायत"),
    Beat(6, "The two friends put the phone away. The narrator leaves viewers with the warning sign.",
         "यही फ़िशिंग है। डर दिखाकर भरोसा चुराना। अगली बार संदेश कहे जल्दी करो, तो पहले ठहरो।",
         "serious", "ठहरो"),
)


def ease(value):
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


@lru_cache(maxsize=20)
def font(size, hindi=False, bold=False):
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    filename = "Nirmala.ttc" if hindi else "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(str(fonts / filename), size, index=1 if hindi and bold else 0)
    except OSError:
        return ImageFont.load_default(size=size)


@lru_cache(maxsize=64)
def art_size(sprite_name, height):
    sprite = ART[sprite_name]
    return sprite.resize((round(sprite.width * height / sprite.height), height), Image.Resampling.LANCZOS)


def artwork(root):
    directory = root / "assets" / "cinematic"
    layers = {}
    for name in ("host", "hero", "friend", "hand", "reaction", "studio", "street", "interior"):
        with Image.open(directory / f"{name}.png") as source:
            if name in {"host", "hero", "friend", "hand", "reaction"}:
                rgba = source.convert("RGBA")
                layers[name] = rgba.crop(rgba.getbbox())
            else:
                layers[name] = source.convert("RGB")
    return layers


ART = {}
TEXT_RENDERER = None


@lru_cache(maxsize=64)
def hindi_mask(text, size):
    ffmpeg, tool, scratch = TEXT_RENDERER
    width, height = 800, 112
    hindi_font = "Nirmala UI" if os.name == "nt" else "Noto Sans Devanagari"
    header = rf"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Text,{hindi_font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,4,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Text,,0,0,0,,{{\pos(4,56)}}{text}
"""
    (scratch / "text.ass").write_text(header, encoding="utf-8-sig")
    ffmpeg(tool, "-f", "lavfi", "-i", f"color=black@0:s={width}x{height}:r=1:d=1,format=rgba",
           "-vf", "ass=text.ass:alpha=1", "-frames:v", 1, "-threads", 1, "text.png", cwd=scratch)
    with Image.open(scratch / "text.png") as image:
        alpha = image.convert("RGBA").getchannel("A")
        return alpha.crop(alpha.getbbox())


def put_hindi(frame, text, xy, size, fill, centered=False):
    alpha = hindi_mask(text, size)
    x, y = xy
    if centered:
        x -= alpha.width / 2
        y -= alpha.height / 2
    layer = Image.new("RGBA", alpha.size, fill)
    if isinstance(fill, tuple) and len(fill) == 4 and fill[3] != 255:
        opacity = fill[3]
        alpha = alpha.point(lambda value: value * opacity // 255)
    layer.putalpha(alpha)
    frame.alpha_composite(layer, (round(x), round(y)))


@lru_cache(maxsize=3)
def base_plate(name):
    return ImageOps.fit(ART[name], (W + 88, H + 64), method=Image.Resampling.BICUBIC)


def backdrop(name, progress, motion=1):
    baseline = base_plate(name)
    left = round(40 + motion * (progress - .5) * 43)
    top = round(30 - 8 * progress)
    return baseline.crop((left, top, left + W, top + H)).convert("RGBA")


@lru_cache(maxsize=2)
def safe_gradient():
    overlay = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(overlay)
    for y in range(H):
        ratio = abs((y / H) * 2 - 1)
        alpha = round(145 * ratio ** 3.6)
        d.line((0, y, W, y), fill=(5, 13, 24, alpha))
    return overlay


RAIN = tuple((rng.randrange(W), rng.randrange(H), rng.uniform(.55, 1.4))
             for rng in (random.Random(i * 331 + 47) for i in range(68)))


def weather(canvas, time, strength=1.0):
    film = Image.new("RGBA", canvas.size)
    d = ImageDraw.Draw(film)
    for x, y, z in RAIN:
        offset = time * z * 88
        xx = (x - offset * .24) % W
        yy = (y + offset) % H
        length = z * 19
        d.line((xx, yy, xx - length * .28, yy + length), fill=(152, 211, 235, round(48 * z * strength)),
               width=1 if z < 1 else 2)
    canvas.alpha_composite(film)


def rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(tuple(round(n) for n in xy), radius, fill=fill, outline=outline, width=width)


def key_motion(height, t, stride, lean, gesture, animate_legs=True):
    """Bend a layered illustration through pelvis, shoulders and lower limbs."""
    bands = []
    for fraction in (0, .18, .39, .61, .75, .86, .95, 1):
        sway = lean * (1 - fraction) ** 2
        shoulders = math.sin(t * 2.5) * .005 * height * max(0, 1 - abs(fraction - .28) / .28)
        footfall = math.sin(t * 11 + fraction * 7) * stride * max(0, (fraction - .55) / .45) if animate_legs else 0
        arm = gesture * max(0, 1 - abs(fraction - .41) / .25)
        bands.append((round(fraction * height), sway + shoulders + footfall + arm))
    return bands


def puppet(canvas, name, center, baseline, height, t, stride=0, tilt=0, gesture=0, talking=False, expression="calm"):
    image = art_size(name, height)
    if name == "host":
        image = express(image, t, talking, expression)
    height, width = image.height, image.width
    periods = key_motion(height, t, stride, tilt, gesture, name != "host")
    pad = round(max(abs(shift) for _, shift in periods)) + 4
    columns = (0, width // 2, width)
    mesh = []
    for (top, a), (bottom, b) in zip(periods, periods[1:]):
        if bottom <= top:
            continue
        for i, (left, right) in enumerate(zip(columns, columns[1:])):
            sign = -1 if i == 0 else 1
            # Split the leg motion into opposing strides; retain an unbroken torso.
            l = sign * stride * max(0, (top / height - .72) / .28) * math.sin(t * 11)
            r = sign * stride * max(0, (bottom / height - .72) / .28) * math.sin(t * 11)
            mesh.append(((left + pad, top, right + pad, bottom),
                         (left - a + l, top, left - b + r, bottom,
                          right - b + r, bottom, right - a + l, top)))
    posed = image.transform((width + pad * 2, height), Image.Transform.MESH, mesh, Image.Resampling.BICUBIC)
    if name != "host":
        shadow = Image.new("RGBA", canvas.size)
        shadow_x, shadow_y = int(center), int(baseline - 3)
        ImageDraw.Draw(shadow).ellipse((shadow_x - width * .30, shadow_y - 15,
                                        shadow_x + width * .30, shadow_y + 8), fill=(5, 9, 15, 131))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    canvas.alpha_composite(posed, (round(center - posed.width / 2), round(baseline - height)))


def express(image, t, talking, expression):
    if not talking:
        return image
    copy = image.copy()
    d = ImageDraw.Draw(copy)
    x, y = round(image.width * .516), round(image.height * .279)
    lip_w = max(5, round(image.width * .032))
    amplitude = .008 if expression == "serious" else .011
    gap = 1 + round(abs(math.sin(t * 17.3) * math.sin(t * 6.5)) * image.height * amplitude)
    d.polygon(((x - lip_w, y + 2), (x - lip_w // 2, y - 1), (x, y - gap // 3),
               (x + lip_w, y - 2), (x + lip_w // 2, y + gap - 2),
               (x + 1, y + gap), (x - lip_w // 2, y + gap)),
              fill="#432a31")
    return copy


def reveal(cues, marker, default):
    return next((start for start, _, line in cues if marker in line), default)


def handheld_phone(state, t, width=282, height=464):
    image = Image.new("RGBA", (width + 16, height + 20))
    d = ImageDraw.Draw(image)
    rect(d, (12, 13, width + 12, height + 17), 29, (4, 8, 18, 132))
    rect(d, (2, 2, width + 3, height + 3), 29, "#1b2839", "#78909e", 2)
    rect(d, (11, 11, width - 6, height - 5), 23, "#101b2a")
    d.rounded_rectangle((width * .36, 15, width * .63, 23), 4, fill="#334557")
    d.text((27, 47), "09:41", font=font(15, bold=True), fill="#c9d7e3")
    d.line((25, 79, width - 21, 79), fill="#34485b", width=1)
    labels = {
        "refund": ("राशि वापसी", "पैसे लौटाने का दावा", "नई सूचना", "#f4ba83"),
        "request": ("भुगतान की माँग", "पैसे भेजे जाएँगे", "रुकें और जाँचें", "#ff8e9b"),
        "cancelled": ("भुगतान", "माँग बंद की गई", "कोई भुगतान नहीं", "#7ee6c9"),
        "notice": ("संदेश", "खाता बंद होने वाला है", "अभी पुष्टि करें", "#f4ba83"),
        "fake": ("अपरिचित पन्ना", "खाते की पुष्टि", "••••••••", "#f3bd90"),
        "debit": ("भुगतान की सूचना", "अनजान भुगतान", "खाते से पैसे कटे", "#ff8e9b"),
        "warn": ("सावधान", "यह पन्ना बंद करें", "सीधे असली ऐप खोलें", "#fdc58c"),
        "official": ("बैंक का असली ऐप", "सहायता", "शिकायत दर्ज", "#7ee6c9"),
        "safe": ("खाता सुरक्षा", "बैंक से संपर्क हुआ", "सतर्क रहें", "#7ee6c9"),
    }
    small, title, subtitle, accent = labels[state]
    put_hindi(image, small, (28, 104), 18, accent)
    rect(d, (24, 145, width - 21, 317), 15, "#1b2a3c", "#344d60", 1)
    d.ellipse((41, 164, 75, 198), fill=accent)
    d.text((58, 179), "!" if state in {"notice", "warn", "debit"} else "•",
           font=font(20, bold=True), fill=INK, anchor="mm")
    put_hindi(image, title, (41, 216), 24, "#f1f2ef")
    if state == "fake":
        d.text((41, 263), subtitle, font=font(19), fill=accent)
    else:
        put_hindi(image, subtitle, (41, 265), 19, accent)
    if state in {"notice", "fake", "official"}:
        percent = .22 + .60 * ease((t - .08) * 2.6)
        rect(d, (33, 360, width - 33, 367), 3, "#293e53")
        rect(d, (33, 360, 33 + (width - 66) * percent, 367), 3, accent)
    d.rounded_rectangle((width * .37, height - 19, width * .63, height - 14), 2, fill="#61748b")
    return image


def tap_hand(frame, x, y, amount, retreat=False):
    """Animate the illustrated hand on a curved approach to the phone."""
    hand = art_size("hand", 224).rotate(-6 + amount * 9, expand=True, resample=Image.Resampling.BICUBIC)
    frame.alpha_composite(hand, (round(x - 25 - amount * 43), round(y - amount * 21 + (18 if retreat else 0))))


def story_frame(index, t, active, cues):
    beat = SHOTS[index]
    p = t / beat.seconds
    turn = ease(p)
    trigger = reveal(cues, beat.marker, beat.seconds * .48)
    dt = t - trigger
    name = "street" if index < 2 else "interior"
    canvas = backdrop(name, p, motion=-1 if index == 1 else 1)
    if index < 2:
        weather(canvas, t + index * 3, .95)
    if index == 0:
        center = 273 + 233 * turn
        puppet(canvas, "hero", center, 660 + 5 * math.sin(t * 7), 573, t,
               stride=19 * math.sin(math.pi * p), tilt=-18)
        if dt > 0:
            toast = Image.new("RGBA", canvas.size)
            d = ImageDraw.Draw(toast)
            offset = 55 * (1 - ease(dt * 3))
            rect(d, (432, 282 + offset, 719, 363 + offset), 16, "#101e30", "#93d2cf", 2)
            put_hindi(toast, "बैंक से संदेश?", (453, 301 + offset), 30, "#eef6f4")
            put_hindi(toast, "खाता बंद होने की चेतावनी", (454, 335 + offset), 17, "#aacac9")
            canvas.alpha_composite(toast)
    elif index in (1, 2, 4):
        if index == 2 and dt >= -.20:
            puppet(canvas, "reaction", 235 - 22 * turn, 730, 650, t, tilt=-34 * ease(dt + 1))
        else:
            puppet(canvas, "hero", 215, 795, 760, t, tilt=8)
        state = ("fake" if dt > -.55 else "notice") if index == 1 else (
            ("debit" if dt > -.20 else "fake") if index == 2 else ("official" if dt > -1 else "warn"))
        phone = handheld_phone(state, max(dt, 0))
        angle = (8 if index == 1 else -7 if index == 2 else 5) * (1 - .38 * turn)
        if index == 2 and 0 < dt < .45:
            angle += math.sin(dt * 29) * 4 * (1 - dt / .45)
        phone = phone.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        x = round(425 - 26 * turn)
        y = round(72 + 21 * turn)
        canvas.alpha_composite(phone, (x, y))
        if index != 2:
            tap = ease((dt + .45) * 4) * (1 - ease((dt - .12) * 3))
            tap_hand(canvas, x + 144, y + 289, tap, index == 4)
            if abs(dt) < .28:
                radius = 12 + 80 * max(0, dt + .07)
                d = ImageDraw.Draw(canvas)
                d.ellipse((x + 148 - radius, y + 352 - radius, x + 148 + radius, y + 352 + radius),
                          outline=TEAL, width=2)
    else:
        meet = ease((p - .03) * 2.3)
        puppet(canvas, "hero", 270 + (71 * turn if index == 5 else -23 * meet), 680, 579, t,
               stride=9 * math.sin(math.pi * p) if index == 5 else 0, tilt=10)
        puppet(canvas, "friend", 727 - 171 * meet + (38 * p if index == 5 else 0), 682, 552, t,
               stride=13 * (1 - meet), tilt=-22, gesture=16 if active("Meera", t) else 3)
        if index == 3:
            angle = -13 + 9 * meet
            mini = handheld_phone("warn", t).resize((79, 128), Image.Resampling.LANCZOS)
            mini = mini.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
            canvas.alpha_composite(mini, (320 + round(25 * meet), 398))
        if index == 5 and p > .45:
            label = Image.new("RGBA", canvas.size)
            d = ImageDraw.Draw(label)
            alpha = round(246 * ease((p - .45) * 4))
            put_hindi(label, "संदेश में जल्दी? पहले ठहरो।", (W // 2, 69), 39,
                      (232, 252, 243, alpha), centered=True)
            canvas.alpha_composite(label)
    if index == 2 and 0 < dt < .45:
        canvas.alpha_composite(Image.new("RGBA", canvas.size, (242, 67, 83, round(51 * (1 - dt / .45)))))
    canvas.alpha_composite(safe_gradient())
    return canvas


def narrator_frame(index, t, active):
    progress = t / SHOTS[index].seconds
    canvas = backdrop("studio", progress, motion=.32)
    # A little rain, monitor pulse and a foreground desk give the articulated host depth.
    weather(canvas, t + index * 4, .30)
    transition = ease(progress)
    center = 403 + 24 * (transition - .50) * (-1 if index % 2 else 1)
    speaking = active("Narrator", t)
    breath = 4 * math.sin((t + index * 3) * 2.1)
    gesture = 11 * (1 + math.sin(t * 3.2)) * (.45 + .55 * ease(t * 1.4)) if speaking else 0
    puppet(canvas, "host", center, 755 + breath, 704, t + index * .63,
           tilt=18 * math.sin((t + index) * 1.5), gesture=gesture, talking=speaking,
           expression=SHOTS[index].emotion)
    canvas.alpha_composite(safe_gradient())
    d = ImageDraw.Draw(canvas)
    d.line((32, 32, 74, 32), fill=TEAL, width=3)

    if index == 0 and t < 2.9:
        title_plate = Image.new("RGBA", canvas.size)
        title_draw = ImageDraw.Draw(title_plate)
        alpha = round(250 * ease(t * 2.5) * (1 - ease((t - 2.15) * 1.35)))
        rect(title_draw, (26, 541, 780, 676), 12, (8, 16, 30, alpha))
        put_hindi(title_plate, TITLE, (405, 606), 54, (249, 235, 217, alpha), centered=True)
        canvas.alpha_composite(title_plate)
    return canvas

def synth_score(path, duration, cue_times):
    rate = 16000
    out = array("h")
    voices = (55.0, 82.41, 130.81, 164.81)
    for tick in range(rate * duration):
        t = tick / rate
        phrase = int(t / 8) % 4
        pad = sum(math.sin(math.tau * frequency * (1 + .004 * phrase) * t + math.sin(t * 2 + i) * .27)
                  * (650 if i == 0 else 240) for i, frequency in enumerate(voices))
        pulse_t = (t - 1.1) % .72
        pulse = 1260 * math.sin(math.tau * (57 - 13 * pulse_t) * pulse_t) * math.exp(-pulse_t * 15)
        cue = 0
        for start, pitch, strength in cue_times:
            age = t - start
            if 0 < age < .42:
                cue += strength * math.sin(math.tau * (pitch - age * pitch * .66) * age) * math.exp(-age * 12)
        volume = min(1, t * 2, (duration - t) * 2)
        out.append(round((pad + pulse + cue) * volume))
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes(out.tobytes())


def encode(tool, path, duration, draw, size=(W, H)):
    width, height = size
    command = [tool, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(FPS), "-i", "pipe:0",
               "-an", "-c:v", "libx264", "-threads", "4", "-preset", "veryfast",
               "-crf", "17", "-pix_fmt", "yuv420p", str(path)]
    with path.with_suffix(".log").open("w+b") as errors:
        with subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors) as encoder:
            try:
                for frame in range(duration * FPS):
                    encoder.stdin.write(draw(frame / FPS).convert("RGB").tobytes())
            except BrokenPipeError:
                pass
            finally:
                encoder.stdin.close()
            if encoder.wait():
                errors.seek(0)
                raise RuntimeError(errors.read().decode("utf-8", "replace"))


def render_demo(args, root, config, ffmpeg_path, ffmpeg, captions, stamp):
    from studio import assemble, render_shot

    global TEXT_RENDERER

    if args.language and args.language.casefold() not in {"hi-in", "hindi"}:
        raise ValueError("The built-in illustrated demo uses Hindi. Studio supports other languages.")
    if args.format == "landscape" or args.plan_only or args.resume:
        raise ValueError("--split-demo renders a portrait movie directly.")
    layout = split_layout(args.layout)
    ART.clear()
    ART.update(artwork(root))
    art_size.cache_clear()
    base_plate.cache_clear()
    tool = ffmpeg_path()
    job = (root / config["output_folder"] / "split-screen" / f"ek-click-{uuid.uuid4().hex[:8]}").resolve()
    job.mkdir(parents=True)
    scratch = job / "graphics"
    scratch.mkdir()
    TEXT_RENDERER = (ffmpeg, tool, scratch)
    hindi_mask.cache_clear()
    voices = {"Narrator": "hi-IN-MadhurNeural", "Meera": "hi-IN-SwaraNeural"}
    spec = {"mode": "cyber", "language": "Hindi", "ratio": OUTPUT_RATIO, "duration": sum(beat.seconds for beat in SHOTS),
            "split_screen": True, "layout": layout, "caption_size": 14}
    story = {"title": TITLE, "style": STYLE, "layout": layout,
             "summary": "एक झूठा बैंक संदेश राहुल को घबरा देता है। मीरा उसे असली बैंक से मदद लेने का रास्ता दिखाती है।"}
    shots, sound_cues = [], []
    elapsed = 0
    print(f"Illustrated split-screen | {layout} | {spec['duration']}s | {job}", flush=True)
    for index, beat in enumerate(SHOTS):
        folder = job / f"shot{index + 1:04d}"
        folder.mkdir()
        print(f"Animating shot {index + 1}/{len(SHOTS)}", flush=True)
        lines = [{"speaker": "Narrator", "line": beat.line, "emotion": beat.emotion}]
        if beat.reply:
            lines.append({"speaker": "Meera", "line": beat.reply, "emotion": "serious"})
        shot = {"seconds": beat.seconds, "opening": beat.description, "action": beat.description,
                "cast": ["Rahul", "Meera"] if index in (3, 5) else ["Rahul"], "dialogue": lines}
        shots.append(shot)

        def animate(cues, windows):
            def active(name, t):
                return any(speaker == name and start <= t < end for speaker, start, end in windows)

            if index in (0, 1, 2, 4):
                time = reveal(cues, beat.marker, beat.seconds * .48)
                pitch, impact = {0: (415, 5500), 1: (660, 3400), 2: (188, 9100), 4: (830, 4100)}[index]
                sound_cues.append((elapsed + time, pitch, impact))
            host, action = folder / "narrator.mp4", folder / "story.mp4"
            encode(tool, host, beat.seconds, lambda t: narrator_frame(index, t, active))
            encode(tool, action, beat.seconds, lambda t: story_frame(index, t, active, cues))
            compose_split(tool, ffmpeg, host, action, folder / "motion.mp4", layout, beat.seconds)

        render_shot(tool, ffmpeg, captions, shot, voices, folder / "motion.mp4", folder, OUTPUT_RATIO,
                    make_motion=animate)
        elapsed += beat.seconds
    synth_score(job / "score.wav", elapsed, sound_cues)
    assemble(tool, ffmpeg, stamp, root, job, story, shots, spec, config)
    save_json(job / "production.json", {"renderer": "illustrated-2d-composite", "asset_source": "ImageGen",
                                       "spec": spec, "story": story, "shots": shots,
                                       "voice_assignments": voices})
    print(f"Complete: {job / 'movie.mp4'}")

def demo_plan(args):
    """The authored pilot can run on Runway without a planning API call."""
    from studio import STYLES, pixel_style

    if args.language and args.language.casefold() not in {"hi-in", "hindi"}:
        raise ValueError("The built-in screenplay is Hindi. Use --split-screen with a custom prompt for other languages.")
    if args.format == "landscape":
        raise ValueError("The built-in split-screen screenplay uses portrait framing.")
    style = args.style or STYLE
    if style.isdecimal():
        index = int(style)
        if not 1 <= index <= len(STYLES) or STYLES[index - 1] == "Custom":
            raise ValueError("Choose a named style or a numbered preset.")
        style = STYLES[index - 1]
    style = STYLE if style.casefold() == "auto" else pixel_style(style)
    motions = (
        "Rahul walks through a rainy Mumbai lane. He stops when his phone lights his face and looks down, suddenly worried.",
        "Over his shoulder, Rahul squints at an abstract imitation banking screen, hesitates, then taps. Side light shifts on his face.",
        "A red payment alert reflects on Rahul's face. He freezes, then leans back in disbelief. Cutaway to the abstract red notice.",
        "Meera steps into frame, catches his eye and raises a hand to stop him. Rahul lowers the phone and looks at her.",
        "Rahul switches to the official app from the home screen, then lifts the phone to his ear for help. Amber practical light.",
        "The two friends walk away together beneath amber lights. Rahul pockets his phone. Gentle dolly and rain outside.",
    )
    timed_actions = (
        "His phone lights up and he slows.", "He taps the abstract phone display.", "The display flashes red as he recoils.",
        "Meera raises her palm to stop him.", "Rahul calls the bank through the official app.", "Rahul pockets the phone.",
    )
    shots = []
    for index, (beat, action, event) in enumerate(zip(SHOTS, motions, timed_actions)):
        people = ["Rahul", "Meera"] if index in (3, 5) else ["Rahul"]
        dialogue = [{"speaker": "Narrator", "line": beat.line, "emotion": beat.emotion}]
        if beat.reply:
            dialogue.append({"speaker": "Meera", "line": beat.reply, "emotion": "serious"})
        shots.append({"seconds": beat.seconds, "opening": beat.description, "action": action,
                      "cast": people, "dialogue": dialogue, "transition": "cut",
                      "visual_cues": [{"phrase": beat.marker, "action": event}]})
    lengths = [shot["seconds"] for shot in shots]
    layout = split_layout(args.layout)
    return {
        "spec": {"mode": "cyber", "language": "Hindi", "ratio": OUTPUT_RATIO, "duration": sum(lengths),
                 "split_screen": True, "layout": layout, "caption_size": 14,
                 "creative": {"music": "suspenseful", "seed": 0xEF142139}},
        "story": {"title": TITLE, "style": style,
                  "summary": "एक झूठा बैंक संदेश राहुल को घबरा देता है। मीरा उसे असली बैंक से मदद लेने का रास्ता दिखाती है।",
                  "layout": layout,
                  "narrator_appearance": args.narrator or "Indian young adult cybersecurity storyteller, dark wavy hair, aubergine hoodie and teal shirt in a rain-lit studio",
                  "continuity": "Contemporary Mumbai at rainy dusk. Deep teal and amber, same outfits, same blue-black phone, abstract fictional interfaces.",
                  "cast": [
                      {"tag": "rahul", "name": "Rahul", "appearance": "young Indian man, wavy dark hair, rust bomber jacket, dark shirt, blue jeans and cream sneakers"},
                      {"tag": "meera", "name": "Meera", "appearance": "young Indian woman, black bob, teal utility jacket, charcoal trousers and cream shoes"},
                  ]},
        "chapters": [shots], "shot_lengths": lengths,
        "voice_assignments": {"Narrator": "hi-IN-MadhurNeural", "Meera": "hi-IN-SwaraNeural"},
    }
