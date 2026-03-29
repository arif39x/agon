# Consortium V1.1 - The Multi-Gate Adversarial Sandbox

Consortium is a localized research environment aimed at studying semantic drift and prompt decay in cyclical, constrained AI conversational networks. The sandbox places 7 distinct AI personas into a "High-Limit" debate setting with adversarial directives, logging their performance (Time To First Token), aggressive linguistics (`BRUTAL`, `DISMISSIVE`), and semantic inflation across rounds.

## System Requirements
- Python 3.10+
- SQLite3 (Included in Python Standard Library)

## Project Structure
- `app.py`: The Main Streamlit Dashboard (7-Panel UI & Analytics).
- `engine.py`: Multi-Gate Router handling independent API streaming contexts.
- `classifier.py`: Sentiment analysis engine utilizing textual heuristics.
- `database.py`: SQLite persistence schema (`consortium_research.db`).
- `verify.py`: Headless validation script for the database insertion engine.

## Installation

You must run the application inside a Python virtual environment to avoid installation conflicts.

```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate the virtual environment
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Running the Application

To launch the 7-Panel Gateway Dashboard locally:

```bash
# Ensure your virtual environment is activated
source venv/bin/activate

# Start the Streamlit server
streamlit run app.py
```

Streamlit will provide a Local URL (typically `http://localhost:8501`) which you can open in your web browser.

## Configuration (The 7-Panel Gateway)
1. Expand the **Agent** configuration sections on the left sidebar in the application.
2. Select your desired API **Provider** (e.g., OpenRouter, Google AI Studio, OpenAI, or Mock).
3. Input the required **API Key**. 
   - *(Note: If you use Google AI Studio, ensure you choose it from the Provider menu, which sets the `generativelanguage` proxy natively!)*
4. Select the specific **Model** corresponding to the agent's logic.
5. Provide a global **Seed Topic** and specify the number of chronological cycles (**Rounds**).
6. Click **Start / Update Consortium Engine** to initiate the multi-agent cycle. The Feed and Analytics trackers will populate in real-time.
