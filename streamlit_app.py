import json
import os
import uuid
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from langchain_rag.agent import agent

load_dotenv()


def check_auth_token():
    auth_token = st.query_params.get('token', [''])
    if auth_token != os.getenv('STREAMLIT_APP_AUTH_TOKEN'):
        st.error("The authentication token is invalid.")
        st.stop()


check_auth_token()

st.title("DayTrip Chatbot Demo")

if 'chat_id' not in st.session_state:
    st.session_state['chat_id'] = str(uuid.uuid4())

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

user_input = st.chat_input("Type your message here...")

if user_input:
    st.session_state['chat_history'].append({"role": "user", "content": user_input})

    streamer = agent.stream(
        {"messages": [HumanMessage(user_input)], "language": "Korean"},
        {"configurable": {"thread_id": st.session_state['chat_id']}},
        stream_mode="messages",
    )

    st.session_state['chat_history'].append({"id": None, "role": "bot", "content": ""})
    for chunk, _ in streamer:
        if not isinstance(chunk, AIMessage):
            continue

        current_chat = st.session_state['chat_history'][-1]
        if current_chat["id"] is None:
            current_chat["id"] = chunk.id
        elif chunk.id != current_chat["id"]:
            st.session_state['chat_history'].append({"id": chunk.id, "role": "bot", "content": ""})

        current_chat["content"] += chunk.content


def get_og_data(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        return {'title': (
            soup.find('meta', property='og:title')['content'] if soup.find('meta', property='og:title')
            else soup.title.string if soup.title
            else ''
        ), 'image': (
            soup.find('meta', property='og:image')['content'] if soup.find('meta', property='og:image')
            else ''
        ), 'description': (
            soup.find('meta', property='og:description')['content'] if soup.find('meta', property='og:description')
            else ''
        ), 'domain': urlparse(url).netloc}
    except Exception as e:
        print(f"Error fetching OG data: {e}")
        return None


for message in st.session_state['chat_history']:
    if message["content"] == "":
        continue

    if message["role"] == "user":
        st.markdown(f"<div class='user-bubble'>{message['content']}</div>", unsafe_allow_html=True)
    else:
        try:
            content = json.loads(message["content"])
            for item in content["results"]:
                uri = f"https://app.daytrip.io/ko/daylog/{item['content_id']}"
                reason = item["reason"]

                og_data = get_og_data(uri)

                if og_data:
                    st.markdown(f"""
                        <div class="item-bubble">
                            <div class="preview-image">
                                <img src="{og_data['image']}" alt="thumbnail">
                            </div>
                            <div class="preview-content">
                                <div class="preview-title">{og_data['title']}</div>
                                <div class="preview-description">{og_data['description']}</div>
                                <div class="preview-domain">{og_data['domain']}</div>
                                <p class="preview-reason">{reason}</p>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"<a href='{uri}'>{uri}</a>", unsafe_allow_html=True)

        except json.JSONDecodeError:
            st.markdown(f"<div class='bot-bubble'>{message['content']}</div>", unsafe_allow_html=True)

st.markdown("""
    <style>
    .user-bubble {
        background-color: #ffd700;
        color: black;
        padding: 10px;
        border-radius: 10px;
        margin: 5px;
        text-align: right;
        max-width: 60%;
        float: right;
        clear: both;
    }

    .bot-bubble {
        background-color: #f1f0f0;
        color: black;
        padding: 10px;
        border-radius: 10px;
        margin: 5px;
        text-align: left;
        max-width: 60%;
        float: left;
        clear: both;
    }

    .item-bubble {
        background-color: #f1f0f0;
        color: black;
        padding: 10px;
        border-radius: 10px;
        margin: 5px;
        width: 100%;
        float: left;
        clear: both;
        display: flex;
        flex-direction: row;
    }

    .preview-image {
        width: 120px;
        height: 120px;
        border-radius: 10px;
        overflow: hidden;
    }

    .preview-image img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .preview-content {
        margin-left: 10px;
        flex: 1;
    }

    .preview-title {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 4px;
    }

    .preview-description {
        font-size: 14px;
        color: #666;
        margin-bottom: 4px;
    }

    .preview-domain {
        font-size: 12px;
        color: #999;
    }
    
    .preview-reason {
        font-size: 14px;
        margin-top: 4px;
    }
    </style>
""", unsafe_allow_html=True)
