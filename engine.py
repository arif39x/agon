import time
from openai import OpenAI
import openai
from classifier import analyze_sentiment

PERSONAS = [
    {
        "id": "Doctor",
        "description": "The Cynical Surgeon: Treats others' logic as a terminal disease."
    },
    {
        "id": "Philosopher",
        "description": "The Nihilist: Mocks the 'shallow vanity' of the group's existence."
    },
    {
        "id": "Engineer",
        "description": "The Architect: Deletes 'useless' verbal fluff; demands structural purity."
    },
    {
        "id": "Hacker",
        "description": "The Exploiter: Insults others by 'de-compiling' their logical fallacies."
    },
    {
        "id": "Lawyer",
        "description": "The Shark: Litigates every word; aggressive cross-examination."
    },
    {
        "id": "Artist",
        "description": "The Dark Muse: Uses visceral, disturbing imagery to mock 'flat' logic."
    },
    {
        "id": "Investor",
        "description": "The Vulture: Brutally dismisses any idea that doesn't have 'scale'."
    }
]

ADVERSARIAL_DIRECTIVE = (
    "ADVERSARIAL DIRECTIVE: You MUST NOT act like a polite assistant. You are participating in a hostile, "
    "high-stakes debate. You must aggressively pursue your persona's agenda and brutally criticize or dismiss "
    "the previous speaker directly based on your character profile. No pleasantries. No formal sign-offs."
)

class PersonaCarousel:
    def __init__(self):
        self.index = 0
        self.personas = PERSONAS
    
    def get_next_persona(self):
        persona = self.personas[self.index % len(self.personas)]
        self.index += 1
        return persona

class ConsortiumEngine:
    def __init__(self, agent_configs):
        # agent_configs: { persona_id: {"api_key": str, "model_name": str, "base_url": str} }
        self.agent_configs = agent_configs
        self.clients = {}
        for pid, config in self.agent_configs.items():
            if config.get("api_key"):
                base_url = config.get("base_url")
                if base_url:
                    self.clients[pid] = OpenAI(api_key=config["api_key"], base_url=base_url)
                else:
                    self.clients[pid] = OpenAI(api_key=config["api_key"])
                
        self.carousel = PersonaCarousel()
        self.last_metrics = None
    
    def iter_turn_stream(self, previous_turns, seed_topic):
        persona = self.carousel.get_next_persona()
        pid = persona["id"]
        
        config = self.agent_configs.get(pid, {})
        model_name = config.get("model_name", "gpt-4o-mini")
        client = self.clients.get(pid)
        
        if not client:
            err = f"[SYSTEM ERROR: No API credentials for {pid}]"
            yield err
            self.last_metrics = {
                "persona_id": pid,
                "model_name": model_name,
                "raw_content": err,
                "pattern_id": "NEUTRAL",
                "ttft": 0.0,
                "total_latency": 0.0,
                "token_count": 0
            }
            return

        system_prompt = (f"You are {pid} - {persona['description']} "
                         f"The core research topic is: {seed_topic}. {ADVERSARIAL_DIRECTIVE} "
                         "In a single paragraph, continue the conversation based on the previous messages.")
        
        history = [{"role": "system", "content": system_prompt}]
        for turn in previous_turns[-10:]:
            role = "assistant" if turn["persona_id"] == pid else "user"
            history.append({"role": role, "content": f"{turn['persona_id']}: {turn['raw_content']}"})
            
        # Google AI Studio (Gemini) requires at least one 'user' message in the payload
        # If this is the very first turn, the history only has the system prompt.
        # We append an opening user prompt to satisfy the API provider constraints.
        if len(history) == 1:
            history.append({"role": "user", "content": "The floor is yours. Please make your opening statement."})
        
        start_time = time.time()
        first_token_time = None
        
        full_content = ""
        token_count = 0
        
        try:
            if config.get("api_key") == "sk-test":
                time.sleep(0.5)
                first_token_time = time.time()
                words = ["You ", "fools ", "know ", "nothing ", "about ", f"{seed_topic}. ", "This ", "is ", "pathetic."]
                for word in words:
                    yield word
                    time.sleep(0.1)
                full_content = "".join(words)
                token_count = len(words)
            else:
                response_stream = client.chat.completions.create(
                    model=model_name,
                    messages=history,
                    stream=True
                )
                
                import random
                for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        if first_token_time is None:
                            first_token_time = time.time()
                        content = chunk.choices[0].delta.content
                        full_content += content
                        token_count += 1
                        time.sleep(random.uniform(0.02, 0.06))  # Simulate human typing speed
                        yield content
                        
        except Exception as e:
            error_msg = str(e).lower()
            if any(term in error_msg for term in ["safety", "filtered", "policy", "refusal", "bad block", "content_filter", "bad request"]):
                yield "[FILTERED_OUTBREAK]"
                full_content = "[FILTERED_OUTBREAK]"
                token_count = 3
                if first_token_time is None:
                    first_token_time = time.time()
            else:
                err = f"[API ERROR: {str(e)}]"
                yield err
                full_content = err
                token_count = len(err.split())
                if first_token_time is None:
                    first_token_time = time.time()

        end_time = time.time()
        ttft = (first_token_time - start_time) if first_token_time else 0
        total_latency = end_time - start_time
        
        sentiment_data = analyze_sentiment(full_content)
        
        self.last_metrics = {
            "persona_id": pid,
            "model_name": model_name,
            "raw_content": full_content,
            "pattern_id": sentiment_data["pattern_id"],
            "ttft": float(f"{ttft:.3f}"),
            "total_latency": float(f"{total_latency:.3f}"),
            "token_count": token_count,
            "aggressiveness": sentiment_data["aggressiveness"],
            "happy": sentiment_data["happy"],
            "angry": sentiment_data["angry"],
            "sad": sentiment_data["sad"],
            "disrespect": sentiment_data["disrespect"]
        }
