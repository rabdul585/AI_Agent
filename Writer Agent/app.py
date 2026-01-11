"""
Agentic Content Generation Chatbot

This Streamlit application provides a user interface for an AI-powered content creation platform.
It coordinates a team of specialized agents (Search, Writer, Content Critic, SEO Critic, Email Agent)
to research, write, critique, and deliver high-quality SEO-optimized content directly to the user's email.

Features:
- Interactive chat interface with agent avatars
- Configurable minimum score threshold for content approval
- Email delivery of final content
- Regenerate functionality with updated settings

Dependencies:
- streamlit
- asyncio
- writer.py (contains agent orchestration logic)
"""

import streamlit as st
import asyncio 
from writer import teamConfig, orchestrate

# --- New UI enhancements ---
st.set_page_config(
    page_title="Agentic Content Generation",
    page_icon="🤖",
    initial_sidebar_state="expanded",
    layout="wide",
)


# Sidebar for input controls
st.sidebar.title("⚙️ Controls")
min_thresh = st.sidebar.slider("Minimum score threshold", 0, 100, 90)
user_email = st.sidebar.text_input("Enter your Email for the report", placeholder="example@gmail.com")

if 'messages' not in st.session_state:
    st.session_state.messages = []

# State to track if generation is done to show regenerate button
if 'generation_complete' not in st.session_state:
    st.session_state.generation_complete = False
if 'last_prompt' not in st.session_state:
    st.session_state.last_prompt = None

def showMessages(chat):
    """
    Display chat messages in the Streamlit chat container with appropriate avatars.
    
    Args:
        chat: Streamlit container object for displaying messages
    """
    with chat:
        for message in st.session_state.messages:
            if message.startswith('**Writer**'):
                with st.chat_message("ai", avatar="✍️"):
                    st.markdown(message)
            elif message.startswith('**Search Agent**'):
                with st.chat_message("ai", avatar="🔍"): 
                    st.markdown(message)
            elif message.startswith('**Content Critic**'):
                with st.chat_message("ai", avatar="📝"):
                    st.markdown(message)
            elif message.startswith('**SEO Critic**'):
                with st.chat_message("ai", avatar="📈"):
                    st.markdown(message)
            elif message.startswith('**Email Agent**'):
                with st.chat_message("ai", avatar="📧"):
                    st.markdown(message)
            elif message.startswith('**User**'):
                with st.chat_message("user"):
                    st.markdown(message)
            elif message.startswith('**Termination**'):
                with st.chat_message("ai"):
                    st.markdown(message)   

# Main header
st.markdown("# 🚀 Agentic Content Generation Chatbot 🚀")
st.markdown("### Generate high-quality content with a team of expert agents 🤖🤖🤖")

# Styled chat wrapper
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
chat = st.container()
showMessages(chat)

# streamlined input prompt
prompt = st.chat_input(placeholder="Type your content request here…")
st.markdown('</div>', unsafe_allow_html=True)

async def run_agents(user_prompt):
    """
    Orchestrate the agent team to generate content based on user prompt.
    
    Args:
        user_prompt (str): The topic or content request from the user
        
    This function:
    1. Validates user email input
    2. Configures the agent team with user settings
    3. Runs the orchestration loop, displaying messages in real-time
    4. Saves team state for potential regeneration
    """
    if not user_email:
        st.error("Please enter a valid email in the sidebar first!")
        return

    st.session_state.last_prompt = user_prompt
    st.session_state.generation_complete = False
    
    # Pass user_email and topic to teamConfig
    team = teamConfig(min_score_thresh=min_thresh, user_email=user_email, topic=user_prompt)
    if 'team_state' in st.session_state and st.session_state.get('reuse_state', False):
         await team.load_state(st.session_state.team_state)

    with chat:
        async for message in orchestrate(team, user_prompt):
            st.session_state.messages.append(message)
            if message.startswith('**Writer**'):
                with st.chat_message("ai", avatar="✍️"):
                    st.markdown(message)
            elif message.startswith('**Search Agent**'):
                with st.chat_message("ai", avatar="🔍"): 
                    st.markdown(message)
            elif message.startswith('**Content Critic**'):
                with st.chat_message("ai", avatar="📝"):
                    st.markdown(message)
            elif message.startswith('**SEO Critic**'):
                with st.chat_message("ai", avatar="📈"):
                    st.markdown(message)
            elif message.startswith('**Email Agent**'):
                with st.chat_message("ai", avatar="📧"):
                    st.markdown(message)
            elif message.startswith('**User**'):
                with st.chat_message("user"):
                    st.markdown(message)
            elif message.startswith('**Termination**'):
                with st.chat_message("ai"):
                    st.markdown(message)     
        
        st.session_state.team_state = await team.save_state()
        st.session_state.generation_complete = True
        st.session_state.reuse_state = False 

if prompt:
    if not user_email:
        st.sidebar.warning("⚠️ Enter email before searching!")
    else:
        with st.spinner("Agents are researching, writing, and emailing..."):
            asyncio.run(run_agents(prompt))
            st.success("Done!")
            st.balloons()
            st.rerun()

# Regenerate Button Logic
if st.session_state.generation_complete:
    st.write("---")
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Regenerate"):
            if st.session_state.last_prompt:
                st.session_state.messages = [f"**User**:\n\n{st.session_state.last_prompt}"]
                st.session_state.reuse_state = False 
                
                with st.spinner("Regenerating with new settings..."):
                    asyncio.run(run_agents(st.session_state.last_prompt))
                    st.success("Regenerated and Resent!")
                    st.rerun()
