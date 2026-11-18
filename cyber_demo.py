"""New illustrated demo: a fake refund meets a real friend."""
import math

from PIL import Image

import cinematic_demo as art_tools
import full_demo as motion

TITLE = "पैसे आए या गए?"
SLUG = "paise_aaye_ya_gaye"
SCENES = (
    motion.Scene(6, "street", "Rahul", "मीरा, मेरी चाय ठंडी हो गई। पर सुन, दुकानदार पैसे लौटा रहा है।",
                 "happy", "Rahul approaches Meera with a phone alert in the rainy lane.", "लौटा"),
    motion.Scene(6, "street", "Meera", "एक मिनट। पैसे वापस मिल रहे हैं, तो ये भुगतान की माँग क्यों है?",
                 "serious", "Meera signals Rahul to stop as the alert turns amber.", "भुगतान"),
    motion.Scene(6, "interior", "Rahul", "उसने कहा पुष्टि कर दो, वरना पैसे नहीं मिलेंगे। मैं तो दबाने ही वाला था।",
                 "scared", "Rahul hesitates above the payment screen and pulls his hand back.", "पुष्टि"),
    motion.Scene(6, "interior", "Meera", "पैसे लेने के लिए यूपीआई पिन मत डाल। अपने ऐप में देख, वहाँ क्या लिखा है।",
                 "serious", "Meera points to the official app and explains the warning.", "ऐप"),
    motion.Scene(6, "interior", "Rahul", "अरे, यहाँ तो साफ़ लिखा है कि मेरे खाते से पैसे जाएँगे। इसे बंद करता हूँ।",
                 "surprised", "Rahul rejects the suspicious request and puts the phone down.", "बंद"),
    motion.Scene(6, "interior", "Meera", "चल, नई चाय मँगाते हैं। इस बार पैसे सच में जाएँगे, पर चाय भी आएगी।",
                 "happy", "They relax and Meera closes with a joke about buying another tea.", "चाय"),
)


def illustrated_storyboard(style=motion.STYLE, seed=motion.SEED):
    plan = motion.storyboard(style=style, seed=seed)
    cast = [
        {"name": "Rahul", "tag": "rahul", "gender": "male",
         "appearance": "young adult Indian man with wavy black hair, rust-orange bomber jacket and blue jeans"},
        {"name": "Meera", "tag": "meera", "gender": "female",
         "appearance": "young adult Indian woman with a black bob, teal utility jacket and charcoal trousers"},
    ]
    plan["story"].update(title=TITLE, slug=SLUG, cast=cast,
                         summary="राहुल पैसे वापस पाने की कोशिश में एक झूठी भुगतान माँग देखता है। मीरा समय पर उसे रोकती है।",
                         continuity="Rainy Mumbai lane and warm café, consistent clothing, same abstract blue phone screen.")
    plan["spec"].update(mode="cyber")
    plan["chapters"] = [[{"seconds": scene.seconds, "opening": scene.action, "action": scene.action,
                         "cast": ["Rahul"] if index in {2, 4} else ["Rahul", "Meera"], "transition": "cut",
                         "pilot_camera": ("wide", "duo", "phone", "single", "phone", "wide")[index],
                         "dialogue": [{"speaker": scene.speaker, "line": scene.line, "emotion": scene.emotion}],
                         "visual_cues": [{"phrase": scene.phrase, "action": scene.action}]} for index, scene in enumerate(SCENES)]]
    plan["voice_assignments"] = {"Rahul": "hi-IN-MadhurNeural", "Meera": "hi-IN-SwaraNeural"}
    return plan


# These authored beats show both choices before the general lesson.
PILOT_BEATS = (
    ("Rahul", "मीरा, मेरी चाय ठंडी थी। देख, दुकान से पैसे वापस आने का संदेश आया है।",
     "happy", "wide", None),
    ("Rahul", "उसने कहा पैसे वापस मिलेंगे। पर मेरे फ़ोन पर पुष्टि करने की माँग आई है।",
     "confused", "phone", ["REFUND MESSAGE", "Refund promised", "Rs. 120", "CHECK THE REQUEST"]),
    ("Meera", "रुक। ऊपर लिखा है, भुगतान की माँग। ये पैसे पाने की सूचना नहीं है।",
     "serious", "phone", ["PAYMENT REQUEST", "You will pay", "Rs. 120", "APPROVAL REQUIRED"]),
    ("Rahul", "मतलब मैंने इसे मंज़ूर किया, तो पैसे मेरे खाते से जाएँगे?",
     "surprised", "duo", None),
    ("Meera", "हाँ। और पिन माँगे तो मत डालना। पैसे पाने के लिए यूपीआई पिन नहीं डालना पड़ता।",
     "serious", "single", None),
    ("Rahul", "ठीक है, ये माँग बंद कर दी। अब अपना असली यूपीआई ऐप खोलता हूँ।",
     "serious", "phone", ["OFFICIAL APP", "Request declined", "No money sent", "VIEW ACTIVITY"]),
    ("Rahul", "लेन-देन देख लिया। वापस आया पैसा दिख ही नहीं रहा। संदेश बस झाँसा था।",
     "surprised", "phone", ["TRANSACTION HISTORY", "No refund received", "Check your balance", "NO PAYMENT MADE"]),
    ("Meera", "दुकान से उसी नंबर पर बात कर जो तेरे पास पहले से है। संदेश वाले नंबर पर नहीं।",
     "neutral", "duo", None),
    ("Rahul", "दुकान ने भी कहा, उन्होंने ऐसी कोई माँग नहीं भेजी। चलो, पैसे बच गए।",
     "happy", "duo", None),
    ("Meera", "चल, अब गरम चाय लेते हैं। इस बार पैसे सच में जाएँगे। चाय भी आएगी!",
     "happy", "wide", None),
)


def storyboard(style=motion.STYLE, seed=motion.SEED):
    plan = illustrated_storyboard(style, seed)
    actions = (
        "Rahul asks Meera about a purported refund.",
        "The phone shows a refund claim distinct from any completed transaction.",
        "Meera points out the outgoing payment label.",
        "Rahul connects approval with money leaving his account.",
        "Meera explains that a UPI PIN is not required to receive money.",
        "Rahul declines and opens his official app independently.",
        "The transaction history shows no incoming refund and no payment made.",
        "Meera suggests verifying through a contact already known to Rahul.",
        "The shop confirms the request was fake.",
        "They return to the tea joke after the avoided loss.",
    )
    plan["chapters"] = [[{"seconds": 6, "opening": actions[index], "action": actions[index],
                         "cast": ["Rahul", "Meera"], "pilot_camera": camera,
                         "pilot_phone": phone, "transition": "cut",
                         "dialogue": [{"speaker": name, "line": text, "emotion": emotion}]}
                        for index, (name, text, emotion, camera, phone) in enumerate(PILOT_BEATS)]]
    plan["shot_lengths"] = [6] * len(PILOT_BEATS)
    plan["chapter_lengths"] = [plan["shot_lengths"][:]]
    plan["spec"]["duration"] = sum(plan["shot_lengths"])
    plan["spec"]["research"] = {
        "status": "sourced", "notes": "NPCI explains that a UPI PIN is used to make a payment, not to receive money.",
        "sources": [{"title": "NPCI fraud awareness", "url": "https://www.npci.org.in/fraud-awareness"}],
    }
    plan["quality_review"] = {"status": "passed", "method": "authored",
                              "checks": ["refund claim", "outgoing-payment warning", "avoided loss",
                                         "decline", "check official transaction history", "verify independently"]}
    return plan


def load_art(root):
    art = art_tools.artwork(root)
    return {"rahul": art["hero"], "meera": art["friend"], "hand": art["hand"], "street": art["street"].convert("RGBA"), "interior": art["interior"].convert("RGBA")}


def frame(art, plates, index, t, windows, cues, seed, rain_seeds, cache):
    scene = SCENES[index]
    progress = art_tools.ease(t / scene.seconds)
    trigger = art_tools.reveal(cues, scene.phrase, scene.seconds * .48)
    action = art_tools.ease((t - trigger + .30) / 1.05)
    canvas = motion.backdrop(plates[scene.set_name], progress, 1 if index % 2 == 0 else -1)
    if scene.set_name == "street":
        motion.rain(canvas, t + index * 6, rain_seeds)
    # Draw one stable pose per character per shot, exactly as in the restored renderer.
    close = index in {2, 4}
    placement = (("Rahul", 146, 1),) if close else (("Rahul", 146, 1), ("Meera", 406, -1))
    for name, center, flip in placement:
        moving = index == 0 and name == "Rahul"
        height = (685 if name == "Rahul" else 469) if close else (550 if name == "Rahul" else 526)
        x = center + 19 * action * flip - (34 * (1 - progress) if moving else 0)
        floor = 893 if close and name == "Rahul" else 809
        motion.animated_puppet(canvas, art[name.casefold()], name.casefold(), x, floor, height, t,
                               12 * math.sin(progress * math.pi) if moving else 0,
                               flip * 12 * action, 5 * action,
                               motion.speech_amount(name, t, windows, cues), cache)
    if index < 5:
        states = (("refund", "refund"), ("refund", "request"), ("request", "request"),
                  ("request", "official"), ("request", "cancelled"))
        state = states[index][int(t >= trigger)]
        phone = art_tools.handheld_phone(state, t)
        size = (191, 306) if close else (137, 216)
        phone = phone.resize(size, Image.Resampling.LANCZOS)
        turn = -10 + 5 * action
        phone = phone.rotate(turn, expand=True, resample=Image.Resampling.BICUBIC)
        x = 283 - round(37 * action)
        y = (353 if close else 435) + (round(130 * action) if index == 4 else 0)
        canvas.alpha_composite(phone, (x, y))
        if index == 2:
            reach = art_tools.ease((t - trigger + 1.25) / .85)
            retreat = art_tools.ease((t - trigger - .10) / .75)
            amount = reach * (1 - retreat)
            hand = art["hand"]
            width = 174
            hand = hand.resize((width, round(width * hand.height / hand.width)), Image.Resampling.BICUBIC)
            hand = hand.rotate(9 - 13 * amount, expand=True, resample=Image.Resampling.BICUBIC)
            canvas.alpha_composite(hand, (round(x + 147 - amount * 65), round(y + 179 - amount * 34)))
    if index == 0 and t < 2.6:
        alpha = round(247 * art_tools.ease(t * 3) * (1 - art_tools.ease((t - 1.8) * 1.4)))
        art_tools.put_hindi(canvas, TITLE, (motion.W / 2, 137), 39, (255, 232, 202, alpha), centered=True)
    return canvas
