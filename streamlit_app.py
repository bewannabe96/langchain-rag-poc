import uuid

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from langchain_rag import agent

load_dotenv()

st.title("Demo")

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
        stream_mode="messages"
    )

    st.session_state['chat_history'].append({"role": "chat", "content": ""})
    for chunk, metadata in streamer:
        if isinstance(chunk, AIMessage):
            st.session_state['chat_history'][-1]["content"] += chunk.content

# 채팅 기록 출력
for message in st.session_state['chat_history']:
    if message["role"] == "user":
        st.markdown(f"<div class='user-bubble'>{message['content']}</div>", unsafe_allow_html=True)
    else:
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
    </style>
""", unsafe_allow_html=True)
