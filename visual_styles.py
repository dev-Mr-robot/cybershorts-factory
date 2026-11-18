"""Pixel style names and art direction for the motion provider."""
import re

MODERN_PIXEL = "Modern 3D Pixel Cinematic"
RETRO_PIXEL = "Retro Pixel Art"
PIXEL_STYLES = {
    MODERN_PIXEL: "Three-dimensional stylized characters and environments, fine pixel-inspired material details, expressive animation, perspective dolly, cast shadows, ambient occlusion, depth haze, contemporary cinematic grade",
    "High-Resolution Pixel Art": "Dense, hand-placed pixel detail, modern palettes and layered parallax, contemporary compositions and smoothly animated characters at high output resolution",
    "3D Voxel Cinematic": "Volumetric voxel-built characters, architectural block detail, modern cast shadows, atmospheric depth and rendered 3D camera movement",
    "Pixel-Shader 3D": "Smooth articulated 3D geometry with deliberate material-level pixel shading, sharp high-resolution silhouettes and cinematic depth",
    "Hybrid 3D + Pixel": "Smooth 3D characters and camera, high-density pixel surfaces, selective pixel particles and effects",
    "Pixel Cyberpunk": "Modern 3D pixel-inspired urban future, neon practical lighting, wet reflections, rain and layered atmosphere",
    "Pixel Fantasy": "Modern stylized 3D fantasy geometry, pixel-detailed materials, expressive character motion and atmospheric light",
    "Pixel Realism": "Realistic 3D perspective, physically plausible lighting and scale, subtle deliberate pixel material treatment",
    RETRO_PIXEL: "Explicitly requested low-resolution sprite aesthetic with stepped pixel silhouettes and a period game palette",
}

RETRO_SIGNAL = re.compile(r"\b(?:8\s*bit|16\s*bit|game\s*boy|arcade|snes|nes)\b")
PIXEL_SIGNAL = re.compile(r"\b(?:pixel\w*|voxel\w*)\b")
MODERN_ALIASES = {"pixel", "pixelated", "pixel art", "pixel inspired", "pixel cinematic",
                  "3d pixel art", "modern 3d pixel art", "pixelated cinematic", "3d pixelated"}


def pixel_style(style):
    normalized = " ".join(style.strip().casefold().replace("-", " ").split())
    for name in PIXEL_STYLES:
        if normalized == name.casefold().replace("-", " "):
            return name
    if normalized in MODERN_ALIASES:
        return MODERN_PIXEL
    if RETRO_SIGNAL.search(normalized) or "retro" in normalized.split() and PIXEL_SIGNAL.search(normalized):
        return RETRO_PIXEL
    return style.strip()


def style_direction(style):
    return f"{style}. {PIXEL_STYLES[style]}" if style in PIXEL_STYLES else style
