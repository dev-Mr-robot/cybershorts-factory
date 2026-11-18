"""Full-screen illustrated fallback and provider storyboard for the same authored short."""
from dataclasses import dataclass
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageOps

import cinematic_demo as shared
from providers import save_json
from library import finish, job_name, phase

W, H, FPS = 540, 960, 24
RATIO = "1080:1920"
STYLE = "2D Cinematic Illustration"
TITLE = "शहर की आख़िरी लौ"
SEED = 2174178321
SUMMARY = "बिजली जाने के बाद इरा और कबीर छत पर भटकती एक लौ को वापस चिराग तक पहुँचाते हैं।"
CAST = {
    "Ira": "young Indian mechanic, olive brown skin, expressive dark eyes, curly black bob, rust red bandana, warm orange field jacket, cream shirt, slate trousers and red shoes",
    "Kabir": "slender young Indian inventor, warm brown skin, tidy black curls, round glasses, teal utility jacket, lavender scarf, dark jeans and cream shoes",
}

@dataclass(frozen=True)
class Scene:
    seconds: int
    set_name: str
    speaker: str
    line: str
    emotion: str
    action: str
    phrase: str


SCENES = (
    Scene(6, "roof", "Kabir", "फिर बिजली गई। पर देख, दादी का चिराग अब भी जल रहा है।",
          "curious", "A rainy Mumbai rooftop during a blackout. Kabir steps toward a brass lantern and points it out to Ira.", "चिराग"),
    Scene(6, "roof", "Ira", "रुक, ये लौ उड़ रही है! कबीर, वो मुंडेर की तरफ जा रही है।",
          "surprised", "A wind gust lifts a small living amber flame from the lantern. Ira bends to follow it, startled.", "उड़ रही"),
    Scene(6, "ledge", "Kabir", "वो मुंडेर के उस पार जा रही है। इरा, मेरा हाथ पकड़!",
          "scared", "Kabir hurries alongside Ira as the flame zigzags over the wet terrace. He reaches to steady her.", "हाथ पकड़"),
    Scene(6, "ledge", "Ira", "मुझे पकड़ कर रख। बस थोड़ा और… हाँ! मिल गई।",
          "serious", "Ira braces against Kabir and catches the hovering flame in her open hand. The amber light flares.", "मिल गई"),
    Scene(6, "final", "Kabir", "लौ वापस रखते ही… देख इरा, नीचे हर खिड़की जल उठी!",
          "happy", "Ira lowers the flame into the brass lantern. Windows across a rain-slicked Mumbai neighborhood flicker to life.", "खिड़की"),
    Scene(6, "final", "Ira", "अब चाय भी अपने आप बन जाए, तो इसे चमत्कार मानूँ।",
          "sarcastic", "Ira and Kabir relax on the glowing terrace. Ira cracks a dry joke, and Kabir turns toward her, amused.", "चाय"),
)


def storyboard(style=STYLE, seed=SEED):
    shots = []
    for scene in SCENES:
        shots.append({"seconds": scene.seconds, "opening": scene.action, "action": scene.action,
                      "cast": ["Ira", "Kabir"], "dialogue": [
                          {"speaker": scene.speaker, "line": scene.line, "emotion": scene.emotion}],
                      "visual_cues": [{"phrase": scene.phrase, "action": scene.action}],
                      "transition": "cut"})
    return {
        "spec": {"mode": "general", "language": "Hindi", "ratio": RATIO, "duration": sum(s.seconds for s in SCENES),
                 "caption_size": 13, "normalize_video_pts": True, "creative": {"seed": seed, "music": "warm"}},
        "story": {"title": TITLE, "style": style, "summary": SUMMARY,
                  "continuity": "Same two characters and outfits, wet Mumbai rooftops, indigo twilight and amber magic. The flame is a small golden orb.",
                  "cast": [{"name": name, "tag": name.casefold(), "appearance": appearance, "gender": gender}
                           for (name, appearance), gender in zip(CAST.items(), ("female", "male"))]},
        "chapters": [shots], "shot_lengths": [s.seconds for s in SCENES],
        "voice_assignments": {"Ira": "hi-IN-SwaraNeural", "Kabir": "hi-IN-MadhurNeural"},
    }


def load_art(root):
    assets = root / "assets" / "full_demo"
    art = {}
    for name in ("a", "b", "a_close", "roof", "ledge", "final"):
        with Image.open(assets / f"{name}.png") as source:
            layer = source.convert("RGBA")
            art[name] = layer.crop(layer.getbbox()) if name.startswith(("a", "b")) else layer
    return art


def offset_path(points, progress):
    steps = len(points) - 1
    position = min(steps - 1, max(0, int(progress * steps)))
    blend = shared.ease(progress * steps - position)
    return tuple(a + (b - a) * blend for a, b in zip(points[position], points[position + 1]))


def backdrop(plate, progress, pan):
    slide = 30 + pan * (progress - .5) * 39
    top = 17 - 9 * progress
    return plate.transform((W, H), Image.Transform.AFFINE, (1, 0, slide, 0, 1, top),
                           Image.Resampling.BILINEAR)


def animated_puppet(canvas, sprite, name, center, floor, height, t, stride, tilt, gesture, speech, cache):
    """Keep one drawing intact and pivot it gently about its floor anchor."""
    width = round(sprite.width * height / sprite.height)
    key = (name, height)
    if key not in cache:
        cache[key] = sprite.resize((width, height), Image.Resampling.BICUBIC)
    image = cache[key]

    blink_age = (t + (1.34 if name == "b" else .61)) % 4.1
    blink = math.sin(math.pi * blink_age / .17) ** 2 if blink_age < .17 else 0
    if speech > .06 or blink > .10:
        image = image.copy()
        rig_face(image, name, t, speech, blink)

    walk = min(1, abs(stride) / 24)
    # The Phishing pilot used small, frame-clocked body bobs and fixed poses.
    idle_bob = math.sin(t * 4) * 2.0
    step_bob = math.sin(t * 12) * 4.0
    baseline = floor + (1 - walk) * idle_bob + walk * step_bob
    angle = math.radians(max(-2.6, min(2.6, (tilt + gesture * .24) * .064)))
    cosine, sine = math.cos(angle), math.sin(angle)
    pad = math.ceil(height * .05) + 5
    left = math.floor(center - width / 2) - pad
    top = math.floor(baseline - height) - pad
    dx, dy = left - center, top - baseline
    posed = image.transform((width + 2 * pad, height + 2 * pad), Image.Transform.AFFINE,
                            (cosine, -sine, cosine * dx - sine * dy + width / 2,
                             sine, cosine, sine * dx + cosine * dy + height),
                            Image.Resampling.BICUBIC)
    if name != "a_close":
        shadow = Image.new("RGBA", (width + 30, 38))
        ImageDraw.Draw(shadow).ellipse((10, 9, width + 20, 33), fill=(7, 9, 26, 130))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)),
                               (round(center - shadow.width / 2), round(floor - 20)))
    canvas.alpha_composite(posed, (left, top))


def speech_amount(name, t, windows, cues):
    if not any(speaker == name and start <= t <= end for speaker, start, end in windows):
        return 0
    for start, end, _ in cues:
        if start <= t <= end:
            return shared.ease((t - start) / .10) * shared.ease((end - t) / .14)
    return 0


# Anchors measured against the cropped artwork. The lip motion preserves the drawn face.
FACE = {"rahul": (.49, .121), "meera": (.48, .113), "a": (.504, .124), "b": (.525, .121), "a_close": (.507, .332)}
EYES = {
    "a": ((.473, .094), (.524, .086)),
    "b": ((.558, .086),),
    "a_close": ((.452, .225), (.523, .217)),
}


def rig_face(sprite, name, t, speech, blink):
    draw = ImageDraw.Draw(sprite)
    if blink > .10:
        for u, v in EYES.get(name, ()):
            x, y = round(u * sprite.width), round(v * sprite.height)
            rx = max(3, round(sprite.width * .016))
            ry = max(1, round(sprite.height * (.010 if name == "a_close" else .006) * blink))
            skin = sprite.getpixel((x, y + ry + 2))
            draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=skin)
            draw.line(((x - rx, y), (x, y + 1), (x + rx, y - 1)), fill="#49313a", width=1)
    if speech > .06:
        u, v = FACE[name]
        x, y = round(u * sprite.width), round(v * sprite.height)
        width = max(3, round(sprite.width * (.024 if name == "a_close" else .014)))
        gap = round((.20 + .80 * abs(math.sin(t * 16))) * width * .56 * speech)
        if not gap:
            return
        draw.polygon(((x - width, y), (x, y - gap // 2), (x + width, y), (x, y + gap)), fill="#492b38")


def flame(canvas, position, clock, scale=1):
    x, y = position
    layer = Image.new("RGBA", canvas.size)
    d = ImageDraw.Draw(layer)
    radius = 21 * scale + math.sin(clock * 13) * 3
    for width, alpha in ((radius * 2.6, 25), (radius * 1.6, 33), (radius, 59)):
        d.ellipse((x-width, y-width, x+width, y+width), fill=(255, 166, 63, alpha))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(max(4, radius * .43))))
    center = ImageDraw.Draw(canvas)
    core = max(3, round(radius * .39))
    tip = x + math.sin(clock * 8) * core
    center.polygon(((tip, y - core * 2.2), (x + core, y - core * .35), (x + core * .76, y + core *.70),
                    (x - core * .74, y + core * .70), (x - core, y - core *.35)), fill="#f9aa51")
    center.ellipse((x-core*.55, y-core*.60, x+core*.53, y+core*.42), fill="#fff0b1")
    for i in range(11):
        age = (clock * .74 + i * .18) % 1
        dx = math.sin(clock * 3 + i * 3) * radius * (1.2 + age)
        yy = y - radius * (1 + age * 2.4)
        center.ellipse((x+dx-1.3, yy-1.4, x+dx+1.3, yy+1.4), fill="#f5bd7b")


def rain(canvas, clock, seeds):
    layer = Image.new("RGBA", canvas.size)
    d = ImageDraw.Draw(layer)
    for x, y, speed in seeds:
        shift = clock * speed * 126
        xx = (x - shift * .31) % W
        yy = (y + shift) % H
        d.line((xx, yy, xx - 5, yy + 17 * speed), fill=(154, 200, 224, round(36 * speed)), width=1)
    canvas.alpha_composite(layer)


def lantern(canvas, pos, lamp_power):
    x, y = pos
    d = ImageDraw.Draw(canvas)
    d.polygon(((x-21, y+42), (x+21, y+42), (x+28, y+50), (x-28, y+50)), fill="#98714e")
    d.rounded_rectangle((x-19, y-16, x+19, y+40), 5, fill="#594453", outline="#d2975d", width=3)
    d.rounded_rectangle((x-12, y-7, x+12, y+33), 3, fill="#8d614d" if lamp_power else "#3a3c50")
    d.polygon(((x, y-31), (x+21, y-17), (x-21, y-17)), fill="#b38556")
    d.arc((x-10, y-39, x+10, y-18), 173, 367, fill="#e4c18e", width=3)


def frame(art, plates, index, t, windows, cues, seed, rain_seeds, cache=None):
    if cache is None:
        cache = {}
    scene = SCENES[index]
    progress = t / scene.seconds
    ease = shared.ease(progress)
    trigger = shared.reveal(cues, scene.phrase, scene.seconds * .50)
    action = shared.ease((t - trigger + .4) / 1.0)
    clock = t + index * 6
    variant = (seed % 3 - 1) * 8
    canvas = backdrop(plates[scene.set_name], progress, 1 if index % 2 == 0 else -1)
    if index == 4:
        night = backdrop(plates["roof"], progress, 1)
        canvas = Image.blend(night, canvas, action)
    if index < 4:
        shade = Image.new("RGBA", (W, H), (12, 22, 49, 36 if index < 2 else 22))
        canvas.alpha_composite(shade)
    rain(canvas, clock, rain_seeds)

    def actor(name, x, floor, size, stride=0, tilt=0, gesture=0):
        source_name = "a" if name == "Ira" else "b"
        if name == "Ira" and index == 1:
            source_name = "a_close"
        spoken = speech_amount(name, t, windows, cues)
        animated_puppet(canvas, art[source_name], source_name, x, floor, size,
                        clock, stride, tilt, gesture, spoken, cache)

    if index == 0:
        actor("Ira", 145 + 14 * ease, 826, 505, tilt=-7)
        actor("Kabir", 431 - 58 * ease, 820, 535, 16 * math.sin(math.pi * progress), -12, 9)
        base = (253, 688)
        lantern(canvas, base, 1)
        flame(canvas, (base[0], base[1] + 10), clock, .78)
        if t < 2.7:
            title = Image.new("RGBA", (W, H))
            visible = round(235 * shared.ease(t * 3) * (1 - shared.ease((t - 1.9) * 1.7)))
            shared.put_hindi(title, TITLE, (W / 2, 114), 36, (255, 234, 200, visible), centered=True)
            canvas.alpha_composite(title)
    elif index == 1:
        base = (265, 695)
        lantern(canvas, base, action < .15)
        actor("Kabir", 425, 918, 555, tilt=-11)
        actor("Ira", 170 - 14 * action, 997, 748, tilt=-22 * action, gesture=18 * action)
        flame(canvas, offset_path([(265, 705), (279, 522), (342, 398), (476, 330)], action), clock, .91)
    elif index == 2:
        actor("Kabir", 451 - 39 * ease, 897, 526, 23 * math.sin(math.pi * progress), -35 * ease, -13)
        actor("Ira", 193 + 83 * ease, 879, 544, 29 * math.sin(math.pi * progress), -37 * ease, -7)
        flame(canvas, offset_path([(217, 470), (386, 374), (433, 413), (331, 466)], ease), clock, .9)
    elif index == 3:
        actor("Kabir", 454 - 19 * ease, 858, 522, tilt=-25 * ease, gesture=-19)
        actor("Ira", 145 + 56 * ease, 859, 580, tilt=-25 * ease, gesture=28 * ease)
        position = offset_path([(474, 347), (389, 414), (345, 456)], action)
        flame(canvas, (position[0] + variant, position[1]), clock, 1.00 + action * .18)
        if .10 < t-trigger < .52:
            opacity = round(49 * (1 - (t-trigger - .1) / .42))
            canvas.alpha_composite(Image.new("RGBA", (W, H), (255, 181, 80, opacity)))
    elif index == 4:
        actor("Ira", 156+15*ease, 838, 545, tilt=13, gesture=26*action)
        actor("Kabir", 400, 836, 523, tilt=11 * math.sin(t * 2))
        base = (273, 701)
        lantern(canvas, base, 1)
        flame(canvas, offset_path([(261, 556), (262, 626), (273, 711)], action), clock, .89)
    else:
        actor("Kabir", 399 - 8*ease, 846, 540, tilt=-6 + 19*math.sin(t * 1.4))
        actor("Ira", 146 + 24*ease, 850, 548, tilt=12 - 20*ease, gesture=11*math.sin(t * 2.1))
        lantern(canvas, (267, 738), 1)
        flame(canvas, (267, 749), clock, .69)
        if progress > .86:
            canvas = Image.blend(canvas, Image.new("RGBA", canvas.size, (10, 18, 30, 255)),
                                 shared.ease((progress - .86) / .14) * .9)
    return canvas


def render_illustrated(args, root, config, ffmpeg_path, ffmpeg, captions, stamp, production=None):
    from studio import assemble, render_shot

    if args.language and args.language.casefold() not in {"hindi", "hi-in"}:
        raise ValueError("The illustrated demo is authored in Hindi. Studio accepts other languages.")
    if args.format == "landscape":
        raise ValueError("The illustrated demo is authored in portrait. Studio also supports landscape.")
    seed = args.seed if args.seed is not None else SEED
    scene_source = production.SCENES if production else SCENES
    story_source = getattr(production, "illustrated_storyboard", production.storyboard) if production else storyboard
    art_source = production.load_art if production else load_art
    drawing = production.frame if production else frame
    plan = story_source(seed=seed)
    spec, story = plan["spec"], plan["story"]
    tool = ffmpeg_path()
    job = (root / config["output_folder"] / "full-screen" / job_name(story.get("slug", "shahar_ki_aakhiri_lau"))).resolve()
    job.mkdir(parents=True)
    graphics = job / "graphics"
    graphics.mkdir()
    shared.TEXT_RENDERER = (ffmpeg, tool, graphics)
    shared.hindi_mask.cache_clear()
    art = art_source(root)
    plates = {name: ImageOps.fit(art[name], (W + 72, H + 34), method=Image.Resampling.BICUBIC)
              for name in {scene.set_name for scene in scene_source}}
    rng = random.Random(seed)
    rain_seeds = [(rng.randrange(W), rng.randrange(H), rng.uniform(.47, 1.32)) for _ in range(56)]
    print(f"Illustrated full-screen 2D | {spec['duration']}s | {job}", flush=True)
    elapsed = 0
    music_cues = []
    cache = {}
    for index, shot in enumerate(plan["chapters"][0]):
        folder = job / f"shot{index + 1:04d}"
        folder.mkdir()
        phase("SCENE", f"{index + 1}/{len(scene_source)}")

        def animate(cues, windows):
            scene = scene_source[index]
            event_time = shared.reveal(cues, scene.phrase, scene.seconds * .50)
            if index < 5:
                music_cues.append((elapsed + event_time, (336, 763, 218, 602, 830)[index], 4600))
            phase("ANIMATION", f"Rendering scene {index + 1} at 24 fps")
            shared.encode(tool, folder / "motion.mp4", scene.seconds,
                          lambda time: drawing(art, plates, index, time, windows, cues, seed, rain_seeds, cache),
                          size=(W, H))

        render_shot(tool, ffmpeg, captions, shot, plan["voice_assignments"], folder / "motion.mp4",
                    folder, RATIO, make_motion=animate)
        elapsed += shot["seconds"]
    shared.synth_score(job / "score.wav", elapsed, music_cues)
    video = assemble(tool, ffmpeg, stamp, root, job, story, plan["chapters"][0], spec, config)
    plan["renderer"] = "illustrated-2d"
    plan["asset_source"] = "ImageGen"
    save_json(job / "production.json", plan)
    save_json(job / "character-design.json", story["cast"])
    phase("CHECK", "Decoding the exported video and audio")
    ffmpeg(tool, "-xerror", "-i", video, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", os.devnull)
    finish(job, story["title"], video, elapsed, RATIO, "Hindi", plan["renderer"])
