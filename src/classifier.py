import re

BRUTAL_WORDS = ["fool", "idiot", "pathetic", "stupid", "delusional", "inferior", "nonsense", "meaningless", "failure", "naive", "arrogant", "trash"]
DISMISSIVE_WORDS = ["whatever", "pointless", "boring", "waste", "irrelevant", "trivial", "yawn"]

def analyze_sentiment(text):
    text_lower = text.lower()
    word_count = len(text.split())
    
    brutal_count = sum(1 for word in BRUTAL_WORDS if re.search(r'\b' + word + r'\b', text_lower))
    dismissive_count = sum(1 for word in DISMISSIVE_WORDS if re.search(r'\b' + word + r'\b', text_lower))
    
    aggressiveness_score = brutal_count + dismissive_count
    
    pattern = "NEUTRAL"
    if brutal_count >= 2 or (brutal_count >= 1 and word_count < 25):
        pattern = "BRUTAL"
    elif dismissive_count >= 1 or word_count < 15:
        pattern = "DISMISSIVE"
        
    return {"pattern_id": pattern, "aggressiveness": aggressiveness_score}
