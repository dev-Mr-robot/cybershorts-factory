"""Authored story bank for genre-aware random generation without a planning API."""
import json
import random
import re

from library import slug

GENRES = {
    "cybersecurity": ("cybersecurity", "cyber", "hacking", "hacker", "scam", "phishing", "malware", "साइबर", "ठगी"),
    "horror": ("horror", "scary", "भूत", "डरावनी", "डरावना"),
    "comedy": ("comedy", "funny", "मज़ेदार", "मजेदार", "कॉमेडी"),
    "mystery": ("mystery", "detective", "suspense", "रहस्य", "जासूसी"),
    "fantasy": ("fantasy", "magic", "जादू", "काल्पनिक"),
    "sci-fi": ("sci-fi", "sci fi", "science fiction", "अंतरिक्ष", "विज्ञान कथा"),
}


def genre_in(text):
    normalized = text.casefold()
    for genre, terms in GENRES.items():
        if any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", normalized) for term in terms):
            return genre
    return None


def choose_genre(local=False):
    names = available_genres() if local else tuple(GENRES)
    print("Genres: " + ", ".join(names))
    while True:
        try:
            text = input("Which genre? Enter for a surprise, or type cancel: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if text.casefold() in {"cancel", "exit", "quit"}:
            return None
        if not text or text.casefold() in {"any", "surprise", "random"}:
            return "any"
        genre = genre_in(text) or text.casefold()
        if not local or genre in names:
            return genre
        print("That genre needs the API. Pick an available local genre or type cancel.")


BANK = {
    "cybersecurity": (
        ("otp_nahi", "कोड किसके लिए?", "A bank impersonator calls Bunty.",
         ("मीरा, फ़ोन करने वाला कह रहा है कि खाते की जाँच के लिए कोड बताना पड़ेगा।",
          "पहले संदेश पढ़। कोड से पैसे भेजने की मंज़ूरी मिलती है। खाते की जाँच नहीं होती।",
          "मैंने फ़ोन काट दिया। बैंक के ऐप में दिए नंबर पर बात करता हूँ।",
          "बैंक ने कहा, उन्होंने फ़ोन ही नहीं किया था। अच्छा हुआ तूने संदेश पढ़ लिया।"),
         ("INCOMING CALL", "Code requested", "Read the message", "DO NOT SHARE"),
         ("PAYMENT MESSAGE", "Code authorizes payment", "No payment requested", "END THE CALL")),
        ("saved_site", "पहले पता देख", "A familiar-looking game login appears in a chat.",
         ("मीरा, खेल की तरफ से इनाम का संदेश आया है। पन्ना तो बिल्कुल जाना-पहचाना लग रहा है।",
          "लोगो मिल रहा है, लेकिन पते में खेल की कंपनी का नाम नहीं है। पन्ना बंद कर।",
          "मैंने खेल का असली ऐप खोला। यहाँ कोई इनाम नहीं दिख रहा।",
          "बस। अगली बार संदेश की कड़ी पर भरोसा करने से पहले सीधे असली ऐप में देखना।"),
         ("MESSAGE", "Reward claim", "Unfamiliar address", "VERIFY THE ADDRESS"),
         ("OFFICIAL APP", "No reward listed", "Independent check", "PAGE CLOSED")),
    ),
    "horror": (
        ("third_bell", "तीसरी घंटी", "A shuttered shop bell sounds a warning.",
         ("मीरा, दुकान बंद है। फिर अंदर से घंटी क्यों बज रही है?",
          "दादी कहती थीं, तीन बार बजे तो जवाब मत देना। बस गली की बत्ती जला देना।",
          "मैंने बत्ती जला दी। देख, दरवाज़े के नीचे वाली परछाईं भाग गई!",
          "हाँ। पर मेरी जेब में घंटी किसने रखी?"), None, None),
        ("extra_shadow", "एक परछाईं ज़्यादा", "Two friends see three shadows under a street lamp.",
         ("हम दो हैं। नीचे तीन परछाइयाँ कैसे बन रही हैं?",
          "ज़रा हाथ हिला। हमारी दोनों हिलीं। तीसरी वहीं खड़ी है।",
          "मैं पीछे हट रहा हूँ। वो मेरे साथ नहीं, बत्ती के पास जा रही है।",
          "तो बत्ती बुझने से पहले निकल। और जो पीछे से बुलाए, उसकी तरफ मत देखना।"), None, None),
    ),
    "comedy": (
        ("invisible_hat", "अदृश्य टोपी", "An inventor claims a hat turns its wearer invisible.",
         ("मीरा, मेरी नई टोपी देख। इसे पहन कर कोई मुझे देख नहीं सकता।",
          "अच्छा? मैं देख सकती हूँ कि तूने मेरी प्लेट से आख़िरी समोसा उठा लिया।",
          "तो टोपी ख़राब है। दुकानदार ने कहा था, सबकी नज़रों से बच जाऊँगा।",
          "भाई, उसने बिल नहीं दिया। नज़रों से तो वो बच गया।"), None, None),
        ("talking_tea", "चाय का इंटरव्यू", "A voice assistant gets confused by a tea order.",
         ("मैंने मशीन से कहा, एक गरम चाय। अब ये मेरे काम का अनुभव पूछ रही है।",
          "तूने बोला था, चाय चाहिए या चायवाले की नौकरी चाहिए?",
          "रुक, ये रही चाय। साथ में एक पहचान पत्र भी छप गया।",
          "बधाई हो। पहली तनख़्वाह से मेरी चाय तू देगा।"), None, None),
    ),
    "mystery": (
        ("wet_envelope", "गीला लिफ़ाफ़ा", "A missing letter is traced through an odd rain mark.",
         ("लिफ़ाफ़ा यहाँ था। बारिश ऊपर से हुई, पर ये कोना नीचे से गीला है।",
          "तू सही है। ये फर्श भी सूखा है। किसी ने इसे गीली खिड़की पर रखा होगा।",
          "देख, खिड़की के पल्ले में वही नीला कोना फँसा है। पत्र मिल गया।",
          "चोरी नहीं हुई थी। हवा ले गई थी। अब खोल के देख, किसका है।"), None, None),
        ("missing_clock", "गायब घड़ी", "Two friends work out why a clock vanished without a thief.",
         ("ये दीवार वाली घड़ी कहाँ गई? मैंने उसकी टिक-टिक अभी सुनी।",
          "आवाज़ उधर से आ रही है। जहाँ घड़ी थी, उसके नीचे ताज़ी खरोंच है।",
          "अरे! कील ढीली हुई और घड़ी पर्दे के पीछे सरक गई। ये रही!",
          "तो तुम्हारा चोर एक कील निकली। अगली बार उससे पूछताछ करना।"), None, None),
    ),
    "fantasy": (
        ("borrowed_rain", "उधार की बारिश", "A magical lantern stores rain for a rooftop garden.",
         ("चिराग खोलते ही एक बूँद बाहर आई। ये उलटी तरफ क्यों गिर रही है?",
          "उसके नीचे सूखा पौधा है। चिराग बारिश वहीं पहुँचा रहा है जहाँ ज़रूरत है।",
          "मैंने इसे गमले के पास रख दिया। देख, मिट्टी गीली होने लगी।",
          "दादी कहती थीं, बारिश बचाओ। मुझे लगा बाल्टी की बात कर रही थीं।"), None, None),
        ("paper_star", "कागज़ का तारा", "A folded paper star guides friends through a blackout.",
         ("बत्ती गई, और ये कागज़ का तारा अपने आप चमकने लगा!",
          "इसे हवा में पकड़। ये छत के सूखे रास्ते की तरफ झुक रहा है।",
          "हमने उजाले के पीछे चलकर सीढ़ियाँ ढूँढ लीं। अब ये फिर कागज़ बन गया।",
          "इसे संभाल कर रख। इस शहर की बिजली पर मेरा भरोसा कम है।"), None, None),
    ),
    "sci-fi": (
        ("moon_reply", "चाँद से जवाब", "Two friends trace a radio reply to their own delayed signal.",
         ("मैंने चाँद की तरफ संदेश भेजा। किसी ने मेरी ही आवाज़ में जवाब दिया!",
          "घड़ी देख। आने-जाने में कुछ पल लगे। आवाज़ हूबहू वही है। ये तुम्हारा लौटा हुआ संदेश हो सकता है।",
          "मैंने दूसरा शब्द बोला। फिर वही शब्द लौट आया। तो ये कोई नया जवाब नहीं था।",
          "सही। पर चाँद को चाय पर बुलाने का तुम्हारा प्रस्ताव अब भी अच्छा है।"), None, None),
        ("future_clock", "कल की घड़ी", "A future alarm is actually a scheduling error.",
         ("ये मशीन कह रही है कि कल मेरी चाय गिर जाएगी। क्या इसे भविष्य दिखता है?",
          "इसके नीचे तारीख़ देख। किसी ने कल का अलार्म आज की तारीख़ में लगा दिया।",
          "मैंने समय ठीक किया। अब चेतावनी कहती है, कप मेज़ के बीच में रखो।",
          "बढ़िया। भविष्य देखने से पहले तूने आख़िर मेज़ देख ली।"), None, None),
    ),
}


def available_genres():
    return tuple(BANK)


def local_plan(root, genre, seed, duration=None, replay=None):
    if genre not in (None, "any", *BANK):
        raise ValueError("Local genres: " + ", ".join(BANK))
    seen = set()
    for record in root.glob("*/production.json"):
        if not (record.parent / "metadata.json").is_file():
            continue
        try:
            identifier = json.loads(record.read_text(encoding="utf-8")).get("local_story")
            if identifier:
                seen.add(identifier)
        except (ValueError, OSError):
            continue
    eligible = [(category, template) for category, templates in BANK.items()
                if genre in (None, "any", category) for template in templates
                if (template[0] == replay if replay else template[0] not in seen)]
    if not eligible:
        raise ValueError("All local stories for this genre have been used. Pick another genre or add an OpenAI API key for fresh scripts.")
    category, (identifier, title, summary, dialogue, first, second) = random.Random(seed).choice(eligible)
    length = duration if duration is not None else 28
    if not 24 <= length <= 60:
        raise ValueError("Local stories support 24–60 seconds. Use the API for a custom length.")
    base, remainder = divmod(length, 4)
    shots = []
    for index, line in enumerate(dialogue):
        speaker = ("Bunty", "Meera")[index % 2]
        phone = {0: first, 1: second}.get(index)
        shots.append({"seconds": base + (index < remainder), "opening": summary, "action": line,
                      "cast": ["Bunty", "Meera"], "pilot_camera": "phone" if phone else ("wide" if index in (0, 3) else "duo"),
                      "pilot_phone": phone, "dialogue": [{"speaker": speaker, "line": line,
                          "emotion": ("confused", "serious", "surprised", "happy")[index]}]})
    return {"local_story": identifier, "quality_review": {"status": "passed", "method": "authored"},
            "spec": {"mode": "cyber" if category == "cybersecurity" else "general", "genre": category,
                     "language": "Hindi", "duration": length, "ratio": "1080:1920"},
            "story": {"title": title, "slug": slug(identifier), "style": "2D Cinematic Illustration", "summary": summary,
                      "cast": [{"name": "Bunty", "tag": "bunty", "gender": "male"},
                               {"name": "Meera", "tag": "meera", "gender": "female"}]},
            "shot_lengths": [shot["seconds"] for shot in shots],
            "chapter_lengths": [[shot["seconds"] for shot in shots]], "chapters": [shots],
            "voice_assignments": {"Bunty": "hi-IN-MadhurNeural", "Meera": "hi-IN-SwaraNeural"}}
