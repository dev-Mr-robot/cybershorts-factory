"""Original, reusable paper-doll cast for the animated story engine."""
from functools import lru_cache

from PIL import Image, ImageDraw

INK = "#151126"
CAST = {
    "BUNTY": {"skin": "#d99165", "light": "#f2b28a", "jacket": "#f57b36",
              "shade": "#a63e29", "hair": "#332032", "accent": "#ffe181"},
    "MEERA": {"skin": "#a96245", "light": "#d18b65", "jacket": "#2ed0ad",
              "shade": "#19796f", "hair": "#211b32", "accent": "#9affdf"},
    "PATCH": {"skin": "#9a573b", "light": "#ce8962", "jacket": "#8e69ee",
              "shade": "#4c3486", "hair": "#21192f", "accent": "#d3bbff"},
}


@lru_cache(maxsize=128)
def sprite(name, mood, gesture, mouth, stride=0, design=None):
    palette = CAST.get(name, CAST["BUNTY"])
    skin, light, jacket, shade, hair, accent = (
        palette[key] for key in ("skin", "light", "jacket", "shade", "hair", "accent")
    )
    if design:
        hair_style, skin, light, jacket, shade, hair, accent, accessory = design
    image = Image.new("RGBA", (280, 430))
    d = ImageDraw.Draw(image)

    def shape(points, color):
        d.polygon(points, fill=color)
        d.line(points + [points[0]], fill=INK, width=5, joint="curve")

    def oval(box, color, stroke=4):
        d.ellipse(box, fill=color, outline=INK, width=stroke)

    # Silhouette, track pants and shoes.
    shape([(78, 275), (196, 275), (200 + stride, 408), (155 + stride, 408),
           (136, 338), (116 - stride, 409), (70 - stride, 409)], "#343851")
    shape([(73 - stride, 398), (112 - stride, 400), (124 - stride, 424),
           (51 - stride, 424), (52 - stride, 414)], "#eee7e1")
    shape([(160 + stride, 398), (196 + stride, 398), (215 + stride, 421),
           (154 + stride, 426)], "#eee7e1")
    d.line((178, 322, 184 + stride, 392), fill="#737089", width=4)
    d.line((89, 319, 85 - stride, 392), fill="#737089", width=4)

    if name == "MEERA" and not design:
        shape([(80, 102), (61, 125), (65, 212), (101, 206), (104, 116)], hair)
        oval((52, 140, 78, 199), hair)

    shape([(106, 155), (172, 156), (203, 184), (200, 306), (79, 304),
           (74, 190)], jacket)
    shape([(104, 161), (138, 186), (170, 163), (164, 300), (108, 300)], "#25233b")
    d.line((136, 201, 136, 296), fill="#4d4767", width=4)
    d.line((88, 276, 105, 269), fill=accent, width=4)
    d.line((170, 270, 193, 277), fill=accent, width=4)
    shape([(79, 187), (62, 193), (44, 256), (60, 292), (84, 281),
           (75, 249), (93, 209)], shade)
    oval((50, 272, 78, 302), skin)
    poses = {
        "down": [(191, 188), (213, 194), (231, 260), (224, 287), (199, 283), (201, 253), (180, 216)],
        "phone": [(190, 191), (212, 198), (213, 241), (188, 256), (151, 235), (159, 214), (185, 224)],
        "point": [(196, 187), (219, 197), (254, 161), (272, 177), (230, 223), (202, 228), (182, 211)],
        "shrug": [(193, 192), (208, 206), (229, 206), (237, 178), (261, 188), (253, 232), (219, 247), (184, 220)],
    }
    shape(poses[gesture], jacket)
    hand = {"down": (205, 270, 233, 301), "phone": (144, 209, 174, 239),
            "point": (245, 148, 278, 178), "shrug": (233, 160, 264, 193)}[gesture]
    oval(hand, light)
    if gesture == "phone":
        d.rounded_rectangle((146, 180, 169, 223), 4, fill="#302748", outline=INK, width=3)
        d.rectangle((150, 185, 165, 213), fill="#a1f9e5")

    # Neck, head, rim light and recognizable hairstyles.
    shape([(116, 125), (160, 125), (162, 163), (138, 181), (113, 163)], skin)
    if name == "PATCH" and not design:
        shape([(73, 132), (66, 55), (95, 16), (145, 7), (197, 35),
               (210, 137), (187, 176), (172, 160), (101, 172)], shade)
    oval((75, 98, 102, 130), skin)
    oval((174, 98, 196, 130), skin)
    shape([(90, 65), (108, 41), (156, 38), (182, 58), (184, 111),
           (173, 143), (149, 158), (121, 151), (96, 131)], skin)
    d.polygon([(104, 63), (143, 49), (154, 61), (116, 75), (105, 119), (99, 107)], fill=light)
    if design:
        if hair_style in {"bob", "braid"}:
            shape([(78,114),(75,66),(94,42),(139,30),(171,42),(192,70),(195,141),
                   (178,138),(170,78),(141,57),(118,78),(98,79),(97,126)], hair)
            if hair_style == "braid":
                for y in (127,144,160):
                    oval((78,y,95,y+22),hair,2)
        elif hair_style == "curls":
            for x, y in ((91,66),(101,49),(116,41),(136,39),(154,40),(170,49),(182,63)):
                oval((x-13,y-13,x+15,y+14),hair,3)
        else:
            shape([(82,92),(79,59),(97,40),(137,29),(170,41),(190,67),
                   (182,85),(161,62),(128,61),(101,78),(96,99)],hair)
            if hair_style == "cap":
                shape([(79,69),(84,45),(111,32),(149,33),(175,45),(184,65),(208,73),
                       (180,81),(112,76)],jacket)
            elif hair_style == "swept":
                d.line((95,63,136,44,163,45),fill=accent,width=3)
        if accessory == "stud":
            oval((83,120,94,131),accent,2)
    elif name == "BUNTY":
        shape([(84, 92), (79, 53), (102, 34), (117, 12), (127, 29), (156, 15),
               (152, 31), (182, 28), (179, 42), (195, 49), (186, 74),
               (158, 56), (114, 71), (99, 63), (96, 97)], hair)
        d.line((105, 51, 134, 38, 151, 39), fill="#79516a", width=5)
    elif name == "MEERA":
        shape([(82, 109), (76, 69), (93, 35), (125, 25), (160, 28),
               (185, 49), (191, 88), (165, 71), (148, 53), (122, 74), (99, 88)], hair)
        d.arc((89, 36, 180, 104), 190, 320, fill="#644c70", width=5)
        oval((83, 120, 97, 135), "#ffd965", 2)
    else:
        shape([(90, 82), (92, 62), (107, 45), (151, 41), (181, 62),
               (186, 88), (162, 68), (132, 66), (106, 73)], hair)
        d.arc((78, 18, 197, 116), 192, 332, fill="#b797ff", width=5)

    if mood == "angry":
        brows = [(105, 83, 126, 91), (148, 91, 171, 82)]
    elif mood in {"shock", "confused"}:
        brows = [(104, 80, 125, 75), (150, 78, 172, 83)]
    else:
        brows = [(103, 85, 124, 80), (149, 80, 171, 84)]
    for brow in brows:
        d.line(brow, fill=INK, width=5)
    for x in (117, 159):
        if mood == "happy":
            d.arc((x - 11, 91, x + 11, 106), 185, 350, fill=INK, width=4)
        else:
            radius = 11 if mood == "shock" else 8
            oval((x - 10, 101 - radius, x + 10, 101 + radius), "#fff4dc", 2)
            oval((x - 2, 98, x + 5, 105), INK, 1)
    if (design and accessory == "glasses") or (not design and name == "PATCH"):
        for x in (102, 146):
            d.rounded_rectangle((x, 89, x + 28, 111), 4, outline=accent, width=3)
        d.line((131, 97, 146, 97), fill=accent, width=3)
    d.line((136, 102, 131, 116, 140, 117), fill="#784153", width=3)
    if mouth or mood == "shock":
        radius = 9 if mouth == 2 or mood == "shock" else 5
        oval((125, 132 - radius, 153, 133 + radius), "#401c34", 2)
        d.line((131, 129 - radius, 146, 129 - radius), fill="#ffeddf", width=3)
    elif mood == "happy":
        d.arc((122, 117, 156, 141), 8, 174, fill=INK, width=4)
    elif mood == "angry":
        d.line((125, 136, 140, 129, 153, 132), fill=INK, width=4)
    else:
        d.line((127, 134, 150, 132), fill=INK, width=4)
    return image
