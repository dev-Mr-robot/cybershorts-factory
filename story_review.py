"""Editorial review before synthesis. Revise weak story beats and extend as needed."""
import math

from library import phase

RULES = """Review an animated screenplay for the requested subject. Judge what the audience
actually sees and hears, not what the summary promises. Each important claim needs an on-screen
action, contrast, or consequence. Check clear cause and effect, accurate facts, audience language,
and a resolution grounded in the setup. When sourced research is available, check
the screenplay against it. When sources are unavailable, favor well-established
claims and remove unsupported specifics. For cybersecurity, show what the victim sees, the warning
sign, the consequence or narrowly avoided consequence, and demonstrate a defensive alternative
and its result. Keep all examples defensive and avoid attack replication or payloads. Other genres
should make their own story logic and payoff clear; don't force an explanation into fiction.
For short films check the whole arc; for chapters judge their contribution to the full outline.
For the pilot backend, the animation can show stock gestures, speech, reaction shots,
actor entrances, custom phone screens (pilot_phone), and two-line evidence cards
(pilot_evidence). An action beyond those capabilities needs an achievable equivalent
in the actual shots. A generic card without the distinguishing clue does not count.
Return JSON with passed (boolean), feedback (specific revisions, as a single string),
and extra_seconds (an integer from 0 to 30). Ask for more time if another action beat is needed.
Pass only if the important logic is already understandable on screen."""


def inspect_story(plan, key, model, ask, rewrite, save):
    if plan.get("quality_review", {}).get("status") == "passed":
        return
    spec, story = plan["spec"], plan["story"]
    review = plan.setdefault("quality_review", {"status": "pending", "chapters": {}})
    results = review["chapters"]
    for index, group in enumerate(plan["chapters"]):
        if results.get(str(index), {}).get("passed"):
            continue
        for attempt in range(3):
            phase("REVIEW", f"Checking story logic in chapter {index + 1} (pass {attempt + 1})")
            verdict = ask(key, model, RULES, {
                "request": spec["idea"], "mode": spec["mode"], "language": spec["language"],
                "renderer": spec.get("render_backend", "pilot"), "research": spec.get("research"),
                "outline": story["chapters"], "chapter": index + 1, "shots": group,
                "previous_action": plan["chapters"][index - 1][-1]["action"] if index else None,
            })
            passed = verdict.get("passed") is True
            feedback = str(verdict.get("feedback", ""))[:2200]
            extra = verdict.get("extra_seconds", 0)
            extra = max(0, min(30, extra)) if type(extra) is int else 0
            results[str(index)] = {"passed": passed, "feedback": feedback, "extra_seconds_requested": extra}
            save()
            if passed:
                break
            if attempt == 2:
                raise RuntimeError(f"Story review still found unclear logic in chapter {index + 1}: {feedback}")
            slots = [shot["seconds"] for shot in group]
            remaining = max(0, 3600 - sum(shot["seconds"] for chapter in plan["chapters"] for shot in chapter))
            added = min(remaining, extra)
            if added >= 2:
                count = math.ceil(added / 10)
                length, remainder = divmod(added, count)
                slots.extend(length + (i < remainder) for i in range(count))
                phase("REVISE", f"Adding {added}s to show the missing action")
            previous = plan["chapters"][index - 1][-1] if index else None
            group = rewrite(key, model, spec, story, index, slots, previous, feedback=feedback,
                            draft=group)
            plan["chapters"][index] = group
            update_lengths(plan)
            save()
    review["status"] = "passed"
    update_lengths(plan)
    save()


def update_lengths(plan):
    groups = [[shot["seconds"] for shot in group] for group in plan["chapters"]]
    plan["chapter_lengths"] = groups
    plan["shot_lengths"] = [seconds for group in groups for seconds in group]
    plan["spec"]["duration"] = sum(plan["shot_lengths"])
