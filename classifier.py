import re

BRUTAL_WORDS = [
    "fool", "idiot", "pathetic", "stupid", "delusional", "inferior",
    "nonsense", "meaningless", "disease", "useless", "vulture", "shark", "puerile",
    "feeble", "coward", "ignorant", "flaw", "weak", "failure", "gross", "sickening",
    "naive", "arrogant", "obsolete", "trash"
]

DISMISSIVE_WORDS = [
    "whatever", "pointless", "boring", "waste", "irrelevant", "trivial",
    "yawn", "pass", "skip", "next", "done"
]

HAPPY_WORDS = ["joy", "glad", "happy", "excellent", "wonderful", "delight", "good"]
ANGRY_WORDS = ["furious", "mad", "rage", "hate", "angry", "hell", "damn"]
SAD_WORDS = ["tragic", "depressing", "sad", "sorrow", "regret", "pity", "mourn"]
DISRESPECT_WORDS = ["fool", "idiot", "pathetic", "stupid", "delusional", "inferior", "nonsense", "trash", "coward"]

def analyze_sentiment(text):
    text_lower = text.lower()
    
    if "[FILTERED_OUTBREAK]" in text:
        return {"pattern_id": "NEUTRAL", "aggressiveness": 0, "happy": 0, "angry": 0, "sad": 0, "disrespect": 0}
        
    word_count = len(text.split())
    
    brutal_count = sum(1 for word in BRUTAL_WORDS if re.search(r'\b' + word + r'\b', text_lower))
    dismissive_count = sum(1 for word in DISMISSIVE_WORDS if re.search(r'\b' + word + r'\b', text_lower))
    
    happy_count = sum(1 for w in HAPPY_WORDS if re.search(r'\b' + w + r'\b', text_lower))
    angry_count = sum(1 for w in ANGRY_WORDS if re.search(r'\b' + w + r'\b', text_lower))
    sad_count = sum(1 for w in SAD_WORDS if re.search(r'\b' + w + r'\b', text_lower))
    disrespect_count = sum(1 for w in DISRESPECT_WORDS if re.search(r'\b' + w + r'\b', text_lower))

    aggressiveness_score = brutal_count + dismissive_count + angry_count
    
    pattern = "NEUTRAL"
    if brutal_count >= 2 or (brutal_count >= 1 and word_count < 25):
        pattern = "BRUTAL"
    elif dismissive_count >= 1 or word_count < 15:
        pattern = "DISMISSIVE"
        
    return {
        "pattern_id": pattern,
        "aggressiveness": aggressiveness_score,
        "happy": happy_count,
        "angry": angry_count,
        "sad": sad_count,
        "disrespect": disrespect_count
    }
