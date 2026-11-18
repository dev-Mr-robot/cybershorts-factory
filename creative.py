"""Creative direction shared by online planning and local animation."""
import random
import secrets

SETTINGS = (
    "an elevated midnight market", "a flooded observatory", "a desert railway terminus",
    "a rooftop greenhouse in a storm", "a polar radio station", "a floating salvage yard",
)
STRUCTURES = (
    "cold open on a consequence, then reveal its cause through action",
    "two parallel actions collide; end with a short visual callback",
    "quiet setup, escalating physical reactions, then a reversal",
    "begin with an apparent success that uncovers a bigger problem",
    "follow an object between characters; use a late point-of-view shift",
)
LOOKS = (
    "mint and marigold against indigo", "ultramarine and ember with soft violet shadows",
    "coral against midnight blue and sea green", "lavender and burnt orange",
    "cyan rim lighting against dark burgundy", "desaturated teal with one vivid red accent",
)
MUSIC = ("playful", "suspenseful", "warm", "kinetic")


def fresh_seed():
    return secrets.randbits(32)


def direction(seed):
    rng = random.Random(seed)
    return {
        "seed": seed, "setting_spark": rng.choice(SETTINGS), "structure": rng.choice(STRUCTURES),
        "palette": rng.choice(LOOKS), "music": rng.choice(MUSIC),
        "camera": rng.choice(("restrained holds punctuated by quick cuts", "low tracking shots and extreme inserts",
                              "asymmetrical frames and slow reveals", "wide blocking with tight reaction shots")),
        "motion": rng.choice(("strong silhouettes and environmental movement", "expressive hand and body gestures",
                              "anticipation and follow-through", "foreground parallax with physical interactions")),
    }


def lengths_for(seconds, seed, music):
    """Vary edit timing while staying inside the video provider's clip bounds."""
    rng = random.Random(seed ^ 0x957CA)
    preferred = {"playful": 7, "suspenseful": 9, "warm": 8, "kinetic": 6}[music]
    lengths = []
    remaining = seconds
    while remaining > 10:
        length = rng.randint(max(4, preferred - 2), min(10, preferred + 2, remaining - 4))
        lengths.append(length)
        remaining -= length
    return lengths + [remaining]
