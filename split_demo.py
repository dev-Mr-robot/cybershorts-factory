"""A local Hindi split-screen pilot, animated with the modern 3D renderer."""
from dataclasses import dataclass
from types import SimpleNamespace
import math
import uuid

from providers import save_json
from split_screen import OUTPUT_RATIO, compose_split, split_layout
from visual_styles import MODERN_PIXEL, pixel_style

PALETTE = ("#091627", "#305872", "#ffc682", "#48808c", "#24465b", "#172c42", "#55dfc4")
SEED = 0x751982ED

@dataclass(frozen=True)
class Beat:
    seconds: int
    cue: str
    line: str
    emotion: str
    sound: str
    reply: str = ""


BEATS = (
    Beat(6, "Rahul walks home and his phone vibrates.",
         "राहुल घर जा रहा था। तभी फ़ोन बजा। संदेश में लिखा था, आपका बैंक खाता आज बंद हो जाएगा।", "serious", "surprise"),
    Beat(6, "The warning draws his eye to a suspicious sign-in page.",
         "वो घबरा गया। उसने संदेश की कड़ी खोल दी। सामने बैंक जैसा पन्ना था, लेकिन वो नकली था।", "scared", "tension"),
    Beat(6, "An unexpected account alert flashes red. Rahul recoils.",
         "राहुल ने उस पन्ने पर भरोसा कर लिया। थोड़ी देर में अनजान भुगतान की सूचना आई। अब उसके होश उड़ गए।", "serious", "surprise"),
    Beat(7, "Meera notices his reaction and signals him to stop.",
         "मीरा ने फ़ोन देखा और तुरंत राहुल को रोका।", "serious", "quiet",
         "रुक। संदेश से मत खोल। बैंक का ऐप सीधे खोल।"),
    Beat(6, "Rahul switches to the official app and calls for help.",
         "राहुल ने असली ऐप से बैंक को फ़ोन किया। भुगतान की शिकायत की और अपना खाता सुरक्षित करवाया।", "serious", "relief"),
    Beat(6, "Rahul and Meera put the phone away and leave together.",
         "यही फ़िशिंग है। डर दिखाकर भरोसा चुराना। अगली बार संदेश कहे जल्दी करो, तो पहले ठहरो।", "sarcastic", "relief"),
)


def workshop(blocks):
    a = blocks.add
    a(0, -.20, 1.4, 14, .4, 13, "#303e53", -1)
    a(0, 2.1, 3.0, 12, 4.2, .18, "#19334a")
    a(0, .71, 1.12, 4.5, .12, 1.18, "#49465a")
    a(0, .63, .53, 4.49, .10, .045, "#59afaa", .5)
    for x in (-2.38, 2.38):
        a(x, 1.46, 2.76, 1.54, 2.94, .27, "#2b4561")
        for row in range(5):
            y = .47 + row * .46
            a(x, y, 2.57, 1.28, .32, .08, "#465372")
            for i in range(5):
                a(x - .42 + i * .20, y, 2.515, .09, .042, .023,
                  ("#4ae5c7", "#ffae74", "#9994ce")[(i + row) % 3], .8)
    a(0, 2.2, 2.80, 2.55, 1.42, .13, "#405778")
    a(0, 2.2, 2.71, 2.41, 1.26, .07, "#133446", .22)
    for x in (-1.24, 1.24):
        a(x, 2.23, 2.63, .035, 1.31, .025, "#61daca", 1.3)
    for i in range(10):
        a(-1.10 + i * .23, 1.79 + (i * 7 % 12) * .049, 2.66, .09, .025, .025, "#8ed8da", .45)
    a(0, 3.49, 2.4, 6.1, .062, .18, "#b7a8eb", 1.4)


def hacker(blocks, t, speaking, energy):
    bob = math.sin(t * 3.1) * .038
    pose = blocks.character((0, bob, .0), math.sin(t * 1.35) * .12)
    skin = "#bb876d"
    pose(0, .89, 0, .85, .80, .46, "#6a588b")
    pose(0, 1.25, .08, .81, .24, .56, "#8574a4")
    pose(0, 1.57, .08, .79, .69, .61, "#716495")
    pose(0, 1.86, .02, .78, .14, .61, "#9b81b5")
    pose(0, 1.60, -.249, .59, .53, .06, "#3c3758")
    pose(0, 1.57, -.297, .49, .42, .06, skin)
    pose(0, 1.75, -.329, .46, .065, .025, "#372c43")
    blink = (t % 3.8) < .13
    for side in (-1, 1):
        x = side * .135
        pose(x, 1.63, -.342, .194, .09, .032, "#bbaeef", .20)
        pose(x, 1.63, -.368, .155, .061, .019, "#26384a")
        pose(x - .014, 1.63, -.384, .049, .021 if blink else .045, .008, "#9bedd4", .44)
        raise_hand = (.11 + energy * .13) * (1 + math.sin(t * 4.6 + side)) if speaking else .04
        pose(side * .52, .92 + raise_hand, -.045 - raise_hand * .22, .24, .41, .29, "#675387")
        pose(side * .54, .71 + raise_hand, -.118 - raise_hand * .47, .18, .15, .21, skin)
        pose(side * .09, .98, -.239, .025, .36, .025, "#c6b1d8")
    pose(0, 1.63, -.36, .066, .025, .027, "#c4b5e6")
    mouth = .033 if not speaking else .044 + .035 * abs(math.sin(t * 19))
    pose(0, 1.45, -.337, .14, mouth, .036, "#4c374f")
    pose(0, .71, -.251, .16, .077, .029, "#8de5d2", .38)


def phone(blocks, x, y, z, angle, state, t, scale=1):
    p = blocks.character((x, y, z), angle)
    p(0, 0, 0, .38 * scale, .61 * scale, .069 * scale, "#202a43")
    p(0, .015 * scale, -.042 * scale, .31 * scale, .51 * scale, .016 * scale, "#17374d", .12)
    if state == "warn":
        pulse = .40 + .40 * abs(math.sin(t * 5))
        p(0, .060 * scale, -.057 * scale, .223 * scale, .171 * scale, .010, "#ff9c70", pulse)
        p(0, .094 * scale, -.067 * scale, .026 * scale, .079 * scale, .010, "#453748")
        p(0, .019 * scale, -.067 * scale, .025 * scale, .023 * scale, .010, "#453748")
    elif state == "lock":
        p(0, .031 * scale, -.056 * scale, .195 * scale, .205 * scale, .015, "#ef617e", .87)
        for i in range(4):
            p((i - 1.5) * .037 * scale, .036 * scale, -.075 * scale, .023 * scale, .023 * scale, .007, "#382139")
    elif state == "verified":
        p(0, .06 * scale, -.057 * scale, .21 * scale, .194 * scale, .014, "#75dcb8", .95)
        for i in range(6):
            p((i - 3) * .023 * scale, (.043 + abs(i - 2) * .018) * scale, -.074 * scale,
              .028 * scale, .028 * scale, .008, "#17374d")
    else:
        p(0, .08 * scale, -.056 * scale, .209 * scale, .130 * scale, .012, "#6cbbd8", .59)
        for i in range(3):
            p(-.063 * scale, (.03 - i * .047) * scale, -.066 * scale, .116 * scale, .008 * scale, .007, "#badae2", .45)


def render_panels(tool, ffmpeg, renderer, folder, index, beat, windows, layout, sets):
    from local_motion import Cast
    from modern_motion import Blocks, courier, encode_frames, smooth

    narrator_video = folder / "narrator.mp4"
    story_video = folder / "story.mp4"
    is_side = layout in {"narrator-left", "narrator-right"}

    def active(speaker, t):
        return any(name == speaker and start <= t < end for name, start, end in windows)

    def host(t):
        blocks = Blocks()
        level = 1 if beat.emotion in {"scared", "serious"} else .5
        hacker(blocks, t + index * .9, active("Narrator", t), level)
        if index == 2:
            blocks.add(.84, 1.94, 2.60, .10, .10, .04, "#ff7d97", 1.8)
        p = smooth(t / beat.seconds)
        eye = (-.20 + .33 * p, 1.68 + .07 * p, -3.2 + .19 * p)
        return renderer.pixels(blocks.data, (eye, (0, 1.39, .05), 39 if not is_side else 44),
                               (.28, 1.61, -1.38))

    rahul = Cast("Rahul", "", "#dfa067", "#607c98", "#c8486e")
    meera = Cast("Meera", "", "#5bb8a4", "#435476", "#9ec7d8")

    def victim(t):
        blocks = Blocks()
        p = smooth(t / beat.seconds)
        gait = abs(math.sin(math.pi * p)) if index in (0, 5) else .0
        x = -.94 + p * 1.59 if index == 0 else (-.62 + .94 * p if index == 5 else -.65)
        turn = -.78 * gait + .18
        reaction = .22 if index == 1 else .65 if index in (2, 3, 4) else .04
        courier(blocks, x, turn, t, gait, reaction, index == 2, False, rahul)
        if index >= 3:
            courier(blocks, x + 1.08 + (.25 if is_side else .0), -.34, t + .5, gait * .76,
                    .56 if index == 3 else .15, False, active("Meera", t), meera)
        color_state = ("notice", "warn", "lock", "warn", "verified", "verified")[index]
        focus = index in (1, 2, 4) and not is_side
        phone_x = x - .22 if focus else x - .31
        if focus:
            phone_x = -.42 + .11 * p
            phone_y = 1.04 + .43 * p
            phone_z = -.70
            phone_scale = 1.12
        else:
            phone_y, phone_z, phone_scale = .95 + .23 * p, -.16, .68
        phone(blocks, phone_x, phone_y, phone_z, .18 * math.sin(t), color_state, t, phone_scale)
        if index in (0, 2):
            for k in range(5):
                phase = (t * .65 + k * .24) % 1
                radius = phase * .26
                blocks.add(phone_x + radius * math.cos(k), phone_y + radius * math.sin(k),
                           phone_z - .13, .023, .023, .023, "#ff8f84" if index == 2 else "#73d8db", .8)
        if is_side:
            eye = (x + .45 - .13 * p, 1.49, -4.45)
            target = (x + .40, 1.04, 0)
            fov = 46
        elif focus:
            eye = (1.86 - .74 * p, 2.03 if index == 1 else 1.79, -4.38 + .35 * p)
            target = (-.27, 1.20, -.13)
            fov = 38
        else:
            center = x + (.38 if index >= 3 else .03)
            eye = (center + .85 - 1.62 * p, 2.66 if index == 0 else 2.02, -6.15 if index == 0 else -5.52)
            target = (center, 1.19, .18)
            fov = 41
        return renderer.pixels(blocks.data, (eye, target, fov), (phone_x, phone_y, phone_z - .21))

    renderer.stage = sets[0]
    encode_frames(tool, narrator_video, beat.seconds, host)
    renderer.stage = sets[1]
    encode_frames(tool, story_video, beat.seconds, victim)
    compose_split(tool, ffmpeg, narrator_video, story_video, folder / "motion.mp4", layout, beat.seconds)


def render_demo(args, root, config, ffmpeg_path, ffmpeg, captions, stamp):
    from local_motion import chiptune
    from modern_motion import Blocks, Renderer, stage
    from studio import assemble, render_shot

    if args.style and pixel_style(args.style) not in {MODERN_PIXEL, "5", "auto"}:
        raise ValueError("The built-in split-screen demo uses Modern 3D Pixel Cinematic.")
    if args.language and args.language.casefold() not in {"hindi", "hi-in"}:
        raise ValueError("The built-in split-screen demo uses Hindi. Studio supports other languages.")
    if args.format == "landscape" or args.plan_only or args.resume:
        raise ValueError("--split-demo renders the built-in portrait movie directly.")
    layout = split_layout(args.layout)
    tool = ffmpeg_path()
    job = (root / config["output_folder"] / "split-screen" / f"hindi-scam-{uuid.uuid4().hex[:8]}").resolve()
    job.mkdir(parents=True)
    shots = []
    elapsed = 0
    stingers = []
    for beat in BEATS:
        dialogue = [{"speaker": "Narrator", "line": beat.line, "emotion": beat.emotion}]
        if beat.reply:
            dialogue.append({"speaker": "Meera", "line": beat.reply, "emotion": "serious"})
        shots.append({"seconds": beat.seconds, "opening": beat.cue, "action": beat.cue,
                      "cast": ["Rahul", "Meera"] if len(shots) >= 3 else ["Rahul"],
                      "sound": beat.sound, "dialogue": dialogue})
        if beat.sound != "quiet":
            stingers.append(elapsed + .36)
        elapsed += beat.seconds
    voices = {"Narrator": "hi-IN-MadhurNeural", "Meera": "hi-IN-SwaraNeural"}
    spec = {"mode": "cyber", "language": "Hindi", "ratio": OUTPUT_RATIO, "duration": elapsed,
            "split_screen": True, "layout": layout}
    story = {"title": "जल्दी मत करो", "style": MODERN_PIXEL, "layout": layout,
             "summary": "एक झूठा बैंक संदेश राहुल को घबरा देता है। मीरा उसे असली बैंक से मदद लेने का रास्ता दिखाती है।"}
    chiptune(job / "score.wav", elapsed, "suspenseful", SEED, stingers, modern=True)

    studio_set = Blocks()
    workshop(studio_set)
    sets = (studio_set.data, stage("station", SEED, PALETTE[-1]))
    try:
        renderer = Renderer(SimpleNamespace(setting="station"), SEED, PALETTE)
    except Exception as error:
        raise RuntimeError(f"Could not initialize the 3D split-screen renderer: {error}") from error

    print(f"Split-screen Hindi demo | {layout} | {elapsed}s | {job}", flush=True)
    try:
        for index, (shot, beat) in enumerate(zip(shots, BEATS)):
            folder = job / f"shot{index + 1:04d}"
            folder.mkdir()
            print(f"Animating narrator and story {index + 1}/{len(shots)}", flush=True)

            def make_motion(_cues, windows):
                render_panels(tool, ffmpeg, renderer, folder, index, beat, windows, layout, sets)

            render_shot(tool, ffmpeg, captions, shot, voices, folder / "motion.mp4", folder, OUTPUT_RATIO,
                        make_motion=make_motion)
    finally:
        renderer.close()

    save_json(job / "production.json", {"renderer": "procedural-3d", "spec": spec, "story": story,
                                       "shots": shots, "voice_assignments": voices})
    assemble(tool, ffmpeg, stamp, root, job, story, shots, spec, config)
    print(f"Complete: {job / 'movie.mp4'}")
