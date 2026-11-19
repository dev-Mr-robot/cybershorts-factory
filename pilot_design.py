"""Stable per-production design choices for the pilot's procedural artwork."""
import hashlib
import random

from PIL import Image, ImageDraw, ImageFilter

SETS = ("street", "cafe", "workshop", "rooftop", "forest", "station", "space", "hallway")
GENRE_SETS = {
    "cybersecurity": ("street", "workshop", "cafe"),
    "horror": ("hallway", "forest", "station"),
    "comedy": ("cafe", "street", "rooftop"),
    "mystery": ("station", "hallway", "cafe"),
    "fantasy": ("forest", "rooftop", "hallway"),
    "sci-fi": ("space", "workshop", "rooftop"),
}
PALETTES = (
    ("#151935", "#655888", "#253348", "#c8a8ee", "#fbc879"),
    ("#0d263a", "#226763", "#172e3f", "#70d4cd", "#ffaf7a"),
    ("#2a193a", "#874763", "#302943", "#dcc3ff", "#ff966e"),
    ("#161e2c", "#546879", "#283549", "#a5d5ec", "#f2c66d"),
)
JACKETS = (("#ba526c", "#79394e"), ("#4e8cce", "#38568e"), ("#d7a94c", "#986a35"),
           ("#45a889", "#25615c"), ("#9e76db", "#5c3e87"), ("#e87a51", "#916046"))
SKINS = (("#ecaa83", "#ffd4a6"), ("#a55d45", "#cb8865"), ("#b77c61", "#e0a786"),
         ("#d49470", "#efbb92"), ("#784942", "#a77458"))
HAIR = ("#251e2c", "#552c2d", "#302942", "#6f4835")
ACCENTS = ("#ffe18a", "#cff8e8", "#ffcfda", "#e0cafa")


def seed_for(*values):
    return int.from_bytes(hashlib.blake2b(repr(values).encode("utf-8"), digest_size=8).digest(), "big")


def design_cast(names, seed):
    rng = random.Random(seed)
    coats = list(JACKETS)
    rng.shuffle(coats)
    forms = ["crop", "curls", "bob", "swept", "cap", "braid"]
    rng.shuffle(forms)
    return {
        name: (forms[i % len(forms)], *rng.choice(SKINS), *coats[i % len(coats)],
               rng.choice(HAIR), rng.choice(ACCENTS), ("none", "stud", "glasses", "none")[rng.randrange(4)])
        for i, name in enumerate(names)
    }


def scene_sets(shots, genre, seed):
    choices = list(GENRE_SETS.get(genre, ("street", "cafe", "rooftop", "workshop")))
    rng = random.Random(seed)
    rng.shuffle(choices)
    return [shot.get("pilot_set") if shot.get("pilot_set") in SETS else choices[min(len(choices)-1, i * len(choices) // len(shots))]
            for i, shot in enumerate(shots)]


def background(location, seed):
    """Draw an original environment with scene-specific geometry and lighting."""
    rng = random.Random(seed_for(seed, location))
    sky, horizon, ground, trim, glow = rng.choice(PALETTES)
    size = (660, 1050)
    image = Image.new("RGB", size)
    d = ImageDraw.Draw(image)
    def color(value):
        return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))
    a, b = color(sky), color(horizon)
    for y in range(size[1]):
        p = min(1, y / 790)
        d.line((0,y,660,y), fill=tuple(round(x + (z - x)*p) for x,z in zip(a,b)))
    d.rectangle((0,721,660,1050), fill=ground)
    if location == "space":
        d.rounded_rectangle((48, 155, 613, 650), 47, fill="#10152c", outline=trim, width=11)
        for _ in range(230):
            x, y = rng.randrange(70, 587), rng.randrange(186, 626)
            d.point((x, y), fill=rng.choice((trim, glow, "#ffffff")))
        d.ellipse((265, 279, 446, 460), fill=horizon, outline=trim, width=4)
        d.ellipse((241, 349, 475, 392), outline=glow, width=5)
        for x in (89, 516):
            d.rounded_rectangle((x, 704, x + 74, 800), 7, fill=sky, outline=trim, width=3)
            for i in range(3):
                d.rectangle((x+13+i*17,733,x+22+i*17,741), fill=glow)
        d.line((0,814,261,690,402,690,660,814),fill=trim,width=4)
    elif location in {"street", "rooftop"}:
        for _ in range(100):
            x,y=rng.randrange(660),rng.randrange(60,650)
            d.point((x,y),fill=trim)
        x=rng.randrange(110,520)
        d.ellipse((x,185,x+105,290),fill=glow)
        for x in range(-5,660,33):
            top=rng.randint(410,705)
            d.rectangle((x,top,x+rng.randrange(22,40),734), fill=rng.choice((sky,ground)))
            for y in range(top+10,730,18):
                if rng.random()<.65:
                    d.rectangle((x+7,y,x+13,y+4),fill=glow)
        if location == "street":
            for x in (100,550):
                d.rectangle((x,395,x+8,740),fill=sky)
                d.rectangle((x-14,400,x+28,417),fill=glow)
        else:
            d.rectangle((0,695,660,737),fill=sky,outline=trim,width=2)
    elif location == "forest":
        for x in range(-2,680,40):
            y=rng.randrange(130,420)
            d.ellipse((x-50,y-85,x+72,y+185),fill=rng.choice((sky,ground)))
            d.polygon(((x+8,y),(x+25,y),(x+40,778),(x-2,778)), fill=sky)
        d.polygon(((300,730),(358,730),(551,1050),(69,1050)),fill=horizon)
    elif location in {"hallway","station"}:
        center=(330,493)
        for x in (0,660):
            d.line((x,185,*center),fill=trim,width=3)
            d.line((x,915,*center),fill=trim,width=3)
        for side in (-1,1):
            for i in range(4):
                x=330+side*(82+i*44)
                size=45+i*30
                d.rectangle((x-size//3,555-size,x+size//3,555+size),fill=ground,outline=trim,width=2)
                d.rectangle((x-9,520-size,x+9,527-size),fill=glow)
        if location=="station":
            d.line((12,815,285,581,375,581,646,815),fill=glow,width=4)
    else:
        for x in (29,433):
            d.rounded_rectangle((x,281,x+195,664),12,fill=sky,outline=trim,width=3)
            for i in range(5):
                y=328+i*55
                d.line((x+11,y+23,x+184,y+23),fill=trim,width=2)
                for j in range(5):
                    xx=x+16+j*32
                    top=y+rng.randrange(0,12)
                    d.rectangle((xx,top,xx+11,y+21),fill=rng.choice((horizon,trim,glow)))
        if location=="cafe":
            d.ellipse((232,689,420,735),fill=glow,outline=trim,width=3)
            d.rectangle((314,729,334,849),fill=sky)
        else:
            d.rectangle((207,675,454,747),fill=ground,outline=trim,width=3)
            d.rounded_rectangle((267,557,396,651),7,fill=sky,outline=trim,width=3)
            d.line((284,618,314,595,339,607,373,579),fill=glow,width=3)
    for y in (785,854,940,1031):
        d.line((0,y,660,y),fill=horizon,width=1)
    shine=Image.new("RGBA",image.size)
    ImageDraw.Draw(shine).ellipse((100,468,580,918),fill=(*color(trim),27))
    return Image.alpha_composite(image.convert("RGBA"),shine.filter(ImageFilter.GaussianBlur(80))).convert("RGB")
