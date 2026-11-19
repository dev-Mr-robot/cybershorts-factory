"""Adapter from Studio's storyboard to the original Phishing pilot renderer."""
import asyncio
import os

from PIL import Image

import cinematic_demo as graphics
import episode
from library import finish, phase, slug
from providers import save_json
from pilot_design import background, design_cast, scene_sets, seed_for


def render_plan(plan, tool, ffmpeg, captions, stamp, root, job, config):
    from studio import assemble, render_shot, select_voices

    spec, story = plan["spec"], plan["story"]
    shots = [shot for chapter in plan["chapters"] for shot in chapter]
    names = [person["name"] for person in story["cast"]]
    if not names and not any(shot["dialogue"] for shot in shots):
        raise ValueError("The pilot format needs characters or spoken dialogue.")
    spoken = {line["speaker"] for shot in shots for line in shot["dialogue"]}
    if "voice_assignments" not in plan:
        cast = story | {"cast": [person for person in story["cast"] if person["name"] in spoken]}
        plan["voice_assignments"] = asyncio.run(select_voices(spec, cast, "Narrator" in spoken))
    persisted = plan.get("pilot_art")
    if not persisted:
        story_seed = spec.get("creative", {}).get("seed")
        seed = seed_for(story_seed if story_seed is not None else job.name, story["title"])
        cast_names = list(dict.fromkeys(names + (["Narrator"] if "Narrator" in spoken else []))) or ["Narrator"]
        custom = [name for name in cast_names if not (spec.get("recurring_cast") and name.upper() in episode.CAST)]
        designs = design_cast(custom, seed)
        designs.update({name: design for name, design in spec.get("reuse_pilot_designs", {}).items() if name in designs})
        persisted = plan["pilot_art"] = {
            "seed": seed,
            "designs": designs,
            "locations": scene_sets(shots, spec.get("genre") or ("cybersecurity" if spec["mode"] == "cyber" else None), seed),
        }
    designs = {name: tuple(values) for name, values in persisted["designs"].items()}
    avatars = {name: name if name in designs else name.upper() for name in names}
    avatars.setdefault("Narrator", "Narrator" if "Narrator" in designs else "BUNTY")
    plan["renderer"] = "original-phishing-pilot"
    spec.update(ratio="1080:1920", normalize_video_pts=True, captions_in_frames=True)
    save_json(job / "production.json", plan)
    if spec.get("research"):
        save_json(job / "sources.json", spec["research"])
    save_json(job / "character-design.json", [
        person | {"pilot_sprite": avatars[person["name"]], "pilot_design": designs.get(avatars[person["name"]])}
        for person in story["cast"]])
    sets = job / "sets"
    sets.mkdir(exist_ok=True)
    backgrounds = {}
    for location in set(persisted["locations"]):
        path = sets / (location + ".png")
        if not path.exists():
            temporary = path.with_suffix(".tmp")
            background(location, persisted["seed"]).save(temporary, format="PNG")
            temporary.replace(path)
        with Image.open(path) as image:
            backgrounds[location] = image.convert("RGB")
    scratch = job / "graphics"
    scratch.mkdir(exist_ok=True)
    graphics.TEXT_RENDERER = (ffmpeg, tool, scratch)
    graphics.hindi_mask.cache_clear()
    label = slug(story.get("slug") or story["title"], "animated story").replace("_", " ").upper()
    for index, shot in enumerate(shots):
        folder = job / f"shot{index + 1:04d}"
        folder.mkdir(exist_ok=True)
        phase("PILOT", f"Animating shot {index + 1}/{len(shots)} at 24 fps")
        source = folder / "motion.mp4"
        plate = backgrounds[persisted["locations"][index]]

        def animate(cues, windows):
            speakers = shot["cast"] or names
            default = shot["dialogue"][0]["speaker"] if shot["dialogue"] else (speakers or ["Narrator"])[0]
            camera = shot.get("pilot_camera", "wide" if index in (0, len(shots) - 1) else "duo")
            if camera not in {"wide", "single", "duo", "phone"}:
                camera = "duo"
            phone = None
            if camera == "phone":
                display = shot.get("pilot_phone")
                if not isinstance(display, (list, tuple)) or len(display) != 4 or not all(isinstance(text, str) for text in display):
                    display = ("PHONE", "Check the details", "", "PAUSE AND VERIFY")
                phone = (*[text[:42] for text in display], "#ffe079")

            evidence = shot.get("pilot_evidence")
            if isinstance(evidence, list) and len(evidence) == 2 and all(isinstance(text, str) for text in evidence):
                evidence = [text[:58] for text in evidence]
            else:
                evidence = None

            def frame(t):
                line = next((line for start, end, line in cues if start <= t < end), "")
                current = next((name for name, start, end in windows if start <= t < end), default)
                emotion = next((item.get("emotion") for item in shot["dialogue"] if item["speaker"] == default), None)
                mood = {"happy": "happy", "sarcastic": "happy", "angry": "angry", "scared": "shock",
                        "surprised": "shock"}.get(emotion, "confused")
                avatar = avatars.get(default, avatars["Narrator"])
                secondary = next((avatars[name] for name in speakers if name in avatars and avatars[name] != avatar), None)
                safe_camera = camera if secondary or camera in {"phone", "single"} else "single"
                gesture = "phone" if safe_camera == "phone" else ("point" if index % 2 else "down")
                beat = episode.Shot(avatar, "", safe_camera, mood, gesture, "custom", 1)
                picture = episode.frame_at(plate, beat, index, t, shot["seconds"], bool(line),
                                           "", partner=secondary, count=len(shots), label=label,
                                           speaker_label=slug(current, "speaker").upper() if line else None,
                                           phone=phone, motion_speaker=avatars.get(current, avatar),
                                           evidence=evidence, designs=designs).convert("RGBA")
                if line:
                    for i, text in enumerate(line.splitlines()[:2]):
                        graphics.put_hindi(picture, text.replace(chr(92), "/").replace("{", "(").replace("}", ")"),
                                           (51, 787 + i * 29), 24, "#fff8ef")
                return picture

            graphics.encode(tool, source, shot["seconds"], frame, size=(episode.W, episode.H))

        render_shot(tool, ffmpeg, captions, shot, plan["voice_assignments"], source, folder,
                    spec["ratio"], make_motion=animate)
    video = assemble(tool, ffmpeg, stamp, root, job, story, shots, spec, config)
    ffmpeg(tool, "-xerror", "-i", video, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", os.devnull)
    finish(job, story["title"], video, spec["duration"], spec["ratio"], spec["language"], plan["renderer"])
