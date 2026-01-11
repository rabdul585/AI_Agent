"""
Agent Orchestration Module for Content Generation

This module defines the agent team configuration and orchestration logic for the 
Agentic Content Writer system. It includes:

- Search Agent: Performs web research using SerpApi
- Writer Agent: Generates content based on research
- Content Critic Agent: Evaluates content quality (grammar, clarity, etc.)
- SEO Critic Agent: Evaluates SEO optimization
- Email Agent: Sends final content via SMTP

The system uses AutoGen AgentChat framework with a SelectorGroupChat for coordination.

Dependencies:
- autogen-agentchat
- autogen-ext
- serpapi
- python-dotenv
- smtplib
- pydantic
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TerminatedException, TerminationCondition
from autogen_agentchat.messages import StopMessage
from autogen_agentchat.base import TaskResult
from autogen_core import Component
from autogen_core import CancellationToken
from pydantic import BaseModel
import asyncio
from typing import List
import os
from dotenv import load_dotenv
from serpapi import GoogleSearch
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables from the same directory as this script
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

import json
import re

# --- Tools ---
def search_topic(query: str) -> str:
    """Searches the web for the given topic using SerpApi and returns top results."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "Error: SERPAPI_API_KEY not found in environment variables."
    
    try:
        params = {
            "q": query,
            "api_key": api_key,
            "num": 5
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "organic_results" not in results:
             return "No organic results found."

        formatted_results = ""
        for i, result in enumerate(results["organic_results"]):
            formatted_results += f"Source {i+1}:\nTitle: {result.get('title')}\nSnippet: {result.get('snippet')}\nURL: {result.get('link')}\n\n"
        return formatted_results
    except Exception as e:
        return f"Error performing search: {str(e)}"

def send_email(recipient: str, subject: str, body: str) -> str:
    """Sends an email to the recipient with the given subject and body."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("SMTP_USERNAME")
    sender_password = os.getenv("SMTP_PASSWORD")
    
    if not sender_email or not sender_password:
        return "Error: SMTP_USERNAME or SMTP_PASSWORD not found in environment variables."
        
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject

        # Use markdown for the body
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return f"SUCCESS: Email sent successfully to {recipient}"
    except Exception as e:
        return f"Error sending email: {str(e)}"

# --- Helper for Parsing ---
def parse_critic_json(content: str):
    """Parses JSON from agent output, handling potential markdown blocks and normalizing keys."""
    try:
        # Try to find json block
        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if match:
            raw_data = json.loads(match.group(1))
        else:
            # Fallback to finding anything that looks like JSON
            match_any = re.search(r'\{.*\}', content, re.DOTALL)
            if match_any:
                raw_data = json.loads(match_any.group(0))
            else:
                raw_data = json.loads(content)
        
        # Normalize keys to lowercase with underscores
        normalized_data = {}
        if isinstance(raw_data, dict):
            for k, v in raw_data.items():
                norm_k = str(k).lower().replace(" ", "_")
                normalized_data[norm_k] = v
        return normalized_data
    except:
        return None

def teamConfig(min_score_thresh: int = 80, user_email: str = "example@test.com", topic: str = "Research"):
    """
    Configure and return the agent team for content generation.
    
    Args:
        min_score_thresh (int): Minimum score threshold for content approval (0-100)
        user_email (str): Email address to send final content to
        topic (str): The content topic/request
        
    Returns:
        SelectorGroupChat: Configured agent team ready for orchestration
        
    The team consists of:
    - Search Agent: Web research using SerpApi
    - Writer Agent: Content generation
    - Content Critic: Quality evaluation (grammar, clarity, style, originality, freshness)
    - SEO Critic: SEO optimization evaluation
    - Email Agent: Final delivery via SMTP
    """
    model = OpenAIChatCompletionClient(
        model=os.getenv('OPENAI_MODEL_NAME', 'gpt-4'),
        api_key=os.getenv('OPENAI_API_KEY'),
    )

    search_agent = AssistantAgent(
        name="search_agent",
        description="A researcher agent that searches the web for information.",
        system_message="You are a research agent. Your goal is to find up-to-date and relevant information using the search tool. Provide a summary of your findings to the writer.",
        model_client=model,
        tools=[search_topic]
    )

    writer_agent = AssistantAgent(
        name="writer_agent",
        description="A writer agent that writes content based on a given topic.",
        system_message=(
            "You are a professional content writer. "
            "1. First, wait for the search agent to provide information on the topic. "
            "2. Use the search results to write high-quality, original, and fresh content in markdown format. "
            "3. You must also generate a specific 'SEO Content' section at the end. "
            "4. Collaborate with the content-critic and seo-critic agents. "
            f"If both critics approve (look at their scores in the history), say ONLY 'CONTENT_APPROVED'."
        ),
        model_client=model
    )

    content_critic_agent = AssistantAgent(
        name="content_critic_agent",
        description="A content-critic agent that provides feedback on the content written by the writer agent.",
        system_message=(
            "You are a content-critic agent. Analyze the provided text and output your evaluation in EXPLICIT JSON format. "
            "JSON structure: "
            "{\n"
            "  \"grammar_score\": int,\n"
            "  \"clarity_score\": int,\n"
            "  \"style_score\": int,\n"
            "  \"originality_value_score\": int,\n"
            "  \"content_freshness_score\": int,\n"
            "  \"to_do\": \"string\"\n"
            "}\n"
            "Use a 0-100 scale. Provide a to-do list for improvements. "
            "Ensure keys are EXACTLY as shown above: grammar_score, clarity_score, style_score, originality_value_score, content_freshness_score, to_do."
            f"If all scores are {min_score_thresh} or above, leave 'to_do' empty."
        ),
        model_client=model
    )

    seo_critic_agent = AssistantAgent(
        name="seo_critic_agent",
        description="An SEO-critic agent that provides feedback on the SEO of the content.",
        system_message=(
            "You are an SEO-critic agent. Evaluate the content and the 'SEO Content' section. "
            "Output your evaluation in EXPLICIT JSON format. "
            "JSON structure: "
            "{\n"
            "  \"seo_score\": int,\n"
            "  \"seo_title\": \"string\",\n"
            "  \"seo_description\": \"string\",\n"
            "  \"seo_keywords\": \"string\",\n"
            "  \"to_do\": \"string\"\n"
            "}\n"
            "Use a 0-100 scale. Provide a to-do list for improvements. "
            "Ensure keys are EXACTLY as shown above: seo_score, seo_title, seo_description, seo_keywords, to_do."
            f"If the score is {min_score_thresh} or above, leave 'to_do' empty."
        ),
        model_client=model
    )

    email_agent = AssistantAgent(
        name="email_agent",
        description="An email agent that sends the final approved content to the user.",
        system_message=(
            "You are an email agent. "
            "Wait for the writer_agent to say 'CONTENT_APPROVED'. "
            "Once you see 'CONTENT_APPROVED', find the last research report from the writer. "
            f"Send it to {user_email} using the 'send_email' tool. "
            "Crucial: If the tool returns an error, try to fix it or report it. "
            "If the tool returns a SUCCESS message, then and ONLY THEN output 'TERMINATE'."
        ),
        model_client=model,
        tools=[send_email]
    )

    selector_prompt = """You are in a team of content generation agents.
    Roles:
    {roles}

    Task:
    1. Search Agent searches.
    2. Writer Agent writes.
    3. Critics evaluate (JSON).
    4. Writer improves based on JSON feedback.
    5. VERY IMPORTANT: Once the Writer says 'CONTENT_APPROVED', the next speaker MUST be 'email_agent'.
    
    Current Conversation:
    {history}

    Select the next role from {participants} to speak. Only return the role.
    """
    
    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(25)

    team = SelectorGroupChat(
        participants=[search_agent, writer_agent, content_critic_agent, seo_critic_agent, email_agent],
        model_client=model,
        selector_prompt=selector_prompt,
        termination_condition=termination
    )
    return team

async def orchestrate(team, task):
    """
    Orchestrate the agent team execution and yield formatted messages.
    
    Args:
        team: The configured SelectorGroupChat team
        task (str): The content generation task/prompt
        
    Yields:
        str: Formatted messages from each agent for UI display
        
    This function runs the team asynchronously and formats agent outputs
    for display in the Streamlit interface, including parsed JSON from critics.
    """
    async for message in team.run_stream(task=task):
        if isinstance(message, TaskResult):
            print(msg:=f'**Termination**: {message.stop_reason}')
            yield msg
        else:
            print('--'*20)
            if message.source == "search_agent":
                print(msg:=f'**Search Agent**: {message.content}')
                yield msg
            elif message.source == "writer_agent":
                print(msg:=f'**Writer**: {message.content}')
                yield msg
            elif message.source == "content_critic_agent":
                data = parse_critic_json(message.content)
                if data:
                    print(msg:=f'**Content Critic**:\n\n'
                            f'**Grammar**: {data.get("grammar_score", "N/A")}/100\n'
                            f'**Clarity**: {data.get("clarity_score", "N/A")}/100\n'
                            f'**Style**: {data.get("style_score", "N/A")}/100\n'
                            f'**Originality**: {data.get("originality_value_score", "N/A")}/100\n'
                            f'**Freshness**: {data.get("content_freshness_score", "N/A")}/100\n\n'
                            f'**To Do**: {data.get("to_do", "No feedback provided")}')
                    yield msg
                else:
                    print(msg:=f'**Content Critic**: {message.content}')
                    yield msg
            elif message.source == "seo_critic_agent":
                data = parse_critic_json(message.content)
                if data:
                    print(msg:=f'**SEO Critic**:\n\n'
                            f'**SEO Score**: {data.get("seo_score", "N/A")}/100\n\n'
                            f'**Extracted SEO Data**:\n'
                            f'- Title: {data.get("seo_title", "N/A")}\n'
                            f'- Desc: {data.get("seo_description", "N/A")}\n'
                            f'- Keywords: {data.get("seo_keywords", "N/A")}\n\n'
                            f'**To Do**: {data.get("to_do", "No feedback provided")}')
                    yield msg
                else:
                    print(msg:=f'**SEO Critic**: {message.content}')
                    yield msg
            elif message.source == "email_agent":
                print(msg:=f'**Email Agent**: {message.content}')
                yield msg
            elif message.source == "user":
                print(msg:=f'**User**:\n\n{message.content}')
                yield msg
        

async def main():
    task = "Write a short paragraph about the importance of AI in modern technology. "
    team = teamConfig(min_score_thresh=80)
    async for message in orchestrate(team, task):
        pass
    

if __name__ == "__main__":
    asyncio.run(main())
