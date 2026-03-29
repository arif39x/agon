import streamlit as st
import database
from engine import ConsortiumEngine, PERSONAS
import uuid
import pandas as pd
import plotly.express as px
import time
import os

st.set_page_config(page_title="Consortium Sandbox UI V1.1", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(20, 20, 25) 0%, rgb(8, 8, 12) 90%);
        color: #e0e0e0;
    }
    .stTextInput input, .stNumberInput input {
        background-color: rgba(30, 30, 40, 0.6) !important;
        color: white !important;
        border: 1px solid #333 !important;
    }
    .brutal-border {
        border-left: 4px solid #ff3333 !important;
        padding-left: 10px;
    }
    .neutral-border {
        border-left: 4px solid #666666 !important;
        padding-left: 10px;
    }
    .dismissive-border {
        border-left: 4px solid #3366ff !important;
        padding-left: 10px;
    }
</style>
""", unsafe_allow_html=True)

database.init_db()

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "agent_configs" not in st.session_state:
    st.session_state.agent_configs = {}
if "engine" not in st.session_state:
    st.session_state.engine = None

# Sidebar Navigation & Settings
with st.sidebar:
    if os.path.exists("/home/miku/Desktop/consortium/assets/logo.jpeg"):
        st.image("/home/miku/Desktop/consortium/assets/logo.jpeg", use_container_width=True)

    page = st.radio("Navigation", ["💬 Adversarial Feed", "📈 Analytics & Databases"], index=0)

    st.markdown("---")
    st.header("Global Configuration")
    seed_topic = st.text_input("Global Seed Topic", "The security implications of self-modifying smart contracts.")
    rounds = st.number_input("Rounds", min_value=1, max_value=50, value=3)
    start_btn = st.button("Start / Update Consortium Engine", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.header("7-Panel Gateway")
    
    temp_configs = {}
    for i, persona in enumerate(PERSONAS):
        pid = persona["id"]
        with st.expander(f"Agent: {pid}"):
            provider = st.selectbox("Provider", ["OpenRouter", "Google AI Studio", "OpenAI", "Mock"], key=f"prov_{pid}")
            api_key = st.text_input(f"API Key for {pid}", type="password", key=f"key_{pid}")
            
            model_options = []
            if provider == "OpenRouter":
                model_options = ["openrouter/mistralai/mistral-nemo:free", "openrouter/google/gemini-2.5-flash:free", "openrouter/x-ai/grok-beta:free"]
            elif provider == "Google AI Studio":
                model_options = ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
            elif provider == "OpenAI":
                model_options = ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o"]
            else:
                model_options = ["mock"]
                
            model = st.selectbox(f"Model Selector", model_options, key=f"model_{pid}")
            
            if api_key or provider == "Mock":
                st.markdown("🟢 **Status:** Active")
            else:
                st.markdown("🔴 **Status:** Offline")
            
            base_url = None
            if provider == "OpenRouter":
                base_url = "https://openrouter.ai/api/v1"
            elif provider == "Google AI Studio":
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                
            temp_configs[pid] = {
                "api_key": api_key if provider != "Mock" else "sk-test",
                "model_name": model,
                "base_url": base_url
            }

    if start_btn:
        st.session_state.agent_configs = temp_configs
        st.session_state.engine = ConsortiumEngine(agent_configs=temp_configs)
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

AVATARS = {
    "Doctor": "🩺", "Philosopher": "📖", "Engineer": "⚙️",
    "Hacker": "💻", "Lawyer": "⚖️", "Artist": "🎨", "Investor": "📈",
    "User": "👤"
}

st.title(page)
turns = database.get_turns(st.session_state.session_id)
total_turns = rounds * 7
generate_next = st.session_state.engine is not None and len(turns) < total_turns

# PAGE 1: FEED
if page == "💬 Adversarial Feed":
    with st.container(border=True):
        for turn in turns:
            persona = turn["persona_id"]
            pattern = turn["pattern_id"]
            
            border_cls = "neutral-border"
            color_lbl = "⚪ Neutral"
            if pattern == "BRUTAL":
                border_cls = "brutal-border"
                color_lbl = "🔴 Brutal"
            elif pattern == "DISMISSIVE":
                border_cls = "dismissive-border"
                color_lbl = "🔵 Dismissive"
                
            with st.chat_message(persona, avatar=AVATARS.get(persona, "👤" if persona == "User" else "🤖")):
                st.markdown(f"<div class='{border_cls}'><b>{color_lbl}</b> ({turn['model_name']})<br/>{turn['raw_content']}</div>", unsafe_allow_html=True)
                
        if generate_next:
            engine = st.session_state.engine
            next_idx = engine.carousel.index
            next_persona = engine.carousel.personas[next_idx % len(engine.carousel.personas)]["id"]
            
            with st.chat_message(next_persona, avatar=AVATARS.get(next_persona, "🤖")):
                with st.spinner(f"{next_persona} is attacking..."):
                    stream = engine.iter_turn_stream(turns, seed_topic)
                    if stream:
                        st.write_stream(stream)
            
            if engine.last_metrics:
                metrics = engine.last_metrics
                database.insert_turn(
                    session_id=st.session_state.session_id,
                    persona_id=metrics["persona_id"],
                    model_name=metrics["model_name"],
                    raw_content=metrics["raw_content"],
                    pattern_id=metrics["pattern_id"],
                    ttft=metrics["ttft"],
                    total_latency=metrics["total_latency"],
                    token_count=metrics["token_count"],
                    aggressiveness=metrics["aggressiveness"],
                    happy=metrics["happy"],
                    angry=metrics["angry"],
                    sad=metrics["sad"],
                    disrespect=metrics["disrespect"]
                )
            import time
            time.sleep(3)
            st.rerun()
        elif st.session_state.engine and len(turns) >= total_turns:
            st.success("Research Cycle Complete.")

    user_msg = st.chat_input("Interact with the Consortium...", disabled=(st.session_state.engine is None))
    if user_msg:
        database.insert_turn(
            session_id=st.session_state.session_id,
            persona_id="User",
            model_name="Human",
            raw_content=user_msg,
            pattern_id="NEUTRAL",
            ttft=0.0,
            total_latency=0.0,
            token_count=len(user_msg.split()),
            aggressiveness=0,
            happy=0,
            angry=0,
            sad=0,
            disrespect=0
        )
        st.rerun()

# PAGE 2: ANALYTICS
elif page == "📈 Analytics & Databases":
    tab1, tab2 = st.tabs(["Research Metrics", "Raw Chat Data"])
    
    with tab1:
        if turns:
            df = pd.DataFrame(turns)
            
            if "pattern_id" in df.columns:
                aggression_df = df[df["pattern_id"].isin(["BRUTAL", "DISMISSIVE"])]
                if not aggression_df.empty:
                    agg_counts = aggression_df.groupby("model_name").size().reset_index(name="Aggression Events")
                    fig1 = px.bar(agg_counts, x="model_name", y="Aggression Events", title="Most Aggressive Models", color="model_name", template="plotly_dark")
                    st.plotly_chart(fig1, use_container_width=True, key="fig1")
                else:
                    st.info("No aggression patterns detected yet.")
            else:
                st.info("No pattern column yet.")
            
            fig2 = px.line(df, x="turn_id", y="token_count", title="Semantic Inflation Tracking", markers=True, template="plotly_dark", color_discrete_sequence=['#ffaa00'])
            st.plotly_chart(fig2, use_container_width=True, key="fig2")
            
            if "ttft" in df.columns and not df.empty:
                fig3 = px.scatter(df, x="persona_id", y="ttft", size="total_latency", color="model_name", title="Latency Vitals (TTFT Scatter)", template="plotly_dark", hover_name="turn_id")
                st.plotly_chart(fig3, use_container_width=True, key="fig3")
        else:
            st.info("Metrics will populate during the cycle.")
            
    with tab2:
        if turns:
            df = pd.DataFrame(turns)
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False)
            with open("consortium_data.csv", "w", encoding="utf-8") as f:
                f.write(csv_data)
                
            st.download_button(
                label="📥 Download Data as CSV",
                data=csv_data,
                file_name="consortium_data.csv",
                mime="text/csv"
            )
        else:
            st.info("No data recorded yet.")

    # SILENT BACKGROUND GENERATION (Ensures engine still runs while user views Analytics page)
    if generate_next:
        engine = st.session_state.engine
        with st.spinner("🤖 The Consortium is debating in the background. Charts will auto-update..."):
            stream = engine.iter_turn_stream(turns, seed_topic)
            if stream:
                for _ in stream:
                    pass # Silently consume stream to trigger full string output
        
        if engine.last_metrics:
            metrics = engine.last_metrics
            database.insert_turn(
                session_id=st.session_state.session_id,
                persona_id=metrics["persona_id"],
                model_name=metrics["model_name"],
                raw_content=metrics["raw_content"],
                pattern_id=metrics["pattern_id"],
                ttft=metrics["ttft"],
                total_latency=metrics["total_latency"],
                token_count=metrics["token_count"],
                aggressiveness=metrics["aggressiveness"],
                happy=metrics["happy"],
                angry=metrics["angry"],
                sad=metrics["sad"],
                disrespect=metrics["disrespect"]
            )
        import time
        time.sleep(3)
        st.rerun()
    elif st.session_state.engine and len(turns) >= total_turns:
        st.success("Research Cycle Complete.")
