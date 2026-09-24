import json
import uuid
import httpx
import streamlit as st

# Configure page
st.set_page_config(
    page_title="AI Mentor - Testing Studio",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished aesthetics
st.markdown(
    """
    <style>
    .main {
        background-color: #0e1117;
    }
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 12px;
    }
    .suggested-btn {
        background-color: #1e293b;
        color: #38bdf8;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 6px 12px;
        margin-right: 8px;
        margin-bottom: 8px;
        display: inline-block;
        cursor: pointer;
    }
    .mentor-badge {
        background: linear-gradient(135deg, #6366f1, #a855f7);
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}"

if "user_id" not in st.session_state:
    st.session_state.user_id = "test_user_01"

if "suggested_prompts" not in st.session_state:
    st.session_state.suggested_prompts = [
        "How can I tailor my CV for a Senior Python Developer role?",
        "What are the best projects to prepare for Machine Learning interviews?",
        "Recommend entry-level backend jobs for someone with FastAPI experience.",
    ]

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# Sidebar configuration
with st.sidebar:
    st.title("⚙️ AI Mentor Settings")
    st.markdown("Configure endpoint & session parameters")

    api_base = st.text_input(
        "API Base URL",
        value="http://127.0.0.1:8001",
        help="Base URL of the running FastAPI server",
    )
    endpoint_path = st.text_input(
        "Endpoint Path",
        value="/api/v1/mentor/chat/stream",
        help="FastAPI SSE streaming route",
    )
    stream_url = f"{api_base.rstrip('/')}/{endpoint_path.lstrip('/')}"

    api_key = st.text_input(
        "Service API Key (optional)",
        type="password",
        value="",
        help="Sent as X-API-Key and Authorization Bearer header if provided",
    )

    st.divider()

    st.subheader("Session Details")
    st.session_state.user_id = st.text_input("User ID", value=st.session_state.user_id)
    st.session_state.conversation_id = st.text_input(
        "Conversation ID", value=st.session_state.conversation_id
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(" New Chat", use_container_width=True):
            st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
            st.session_state.messages = []
            st.session_state.suggested_prompts = [
                "Review my CV strengths and weaknesses",
                "Generate a 30-day learning roadmap for Data Engineering",
                "What behavioral questions should I prepare for a tech lead interview?",
            ]
            st.rerun()

    with col2:
        if st.button(" Clear", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Health Check Indicator
    st.divider()
    try:
        health_resp = httpx.get(f"{api_base.rstrip('/')}/health", timeout=5.0)
        if health_resp.status_code == 200:
            st.success("🟢 FastAPI Backend Online")
        else:
            st.warning(f"🟡 Backend returned {health_resp.status_code}")
    except Exception:
        st.error("🔴 Backend Offline (Ensure uvicorn is running)")

# Main Header
st.title("🎓 AI Mentor Interactive Playground")
st.caption("Powered by CrewAI, LangChain, SQLite Memory, and FastAPI SSE streaming")

# Display chat history
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    agent_name = msg.get("agent")

    with st.chat_message(role):
        if agent_name and role == "assistant":
            st.markdown(f"<span class='mentor-badge'>{agent_name}</span>", unsafe_allow_html=True)
        st.markdown(content)

# Suggested Prompts (Chips)
if st.session_state.suggested_prompts:
    st.markdown("##### 💡 Suggested Follow-ups")
    cols = st.columns(len(st.session_state.suggested_prompts))
    for idx, prompt_text in enumerate(st.session_state.suggested_prompts):
        if cols[idx].button(f"👉 {prompt_text}", key=f"sug_{idx}", use_container_width=True):
            st.session_state.pending_prompt = prompt_text
            st.rerun()

# User input Handling
chat_input_val = st.chat_input("Ask your mentor anything...")
query_to_send = st.session_state.pending_prompt or chat_input_val

if query_to_send:
    st.session_state.pending_prompt = None

    # Append and display user message
    st.session_state.messages.append({"role": "user", "content": query_to_send})
    with st.chat_message("user"):
        st.markdown(query_to_send)

    # Prepare streaming assistant response
    with st.chat_message("assistant"):
        agent_placeholder = st.empty()
        response_placeholder = st.empty()
        full_response = ""
        active_agent = "AI Mentor"
        new_prompts = []

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "message": query_to_send,
            "conversation_id": st.session_state.conversation_id,
            "user_id": st.session_state.user_id,
        }

        with st.spinner("Mentor is analyzing and orchestrating agents..."):
            try:
                with httpx.Client(timeout=120.0) as client:
                    with client.stream("POST", stream_url, json=payload, headers=headers) as stream:
                        if stream.status_code != 200:
                            err_body = stream.read().decode("utf-8", errors="ignore")
                            response_placeholder.error(
                                f"Server returned status {stream.status_code}: {err_body}"
                            )
                        else:
                            for line in stream.iter_lines():
                                if not line:
                                    continue
                                line = line.strip()
                                if line.startswith("data:"):
                                    data_str = line[5:].strip()
                                    if data_str == "[DONE]":
                                        break
                                    try:
                                        event = json.loads(data_str)
                                        event_type = event.get("type")

                                        if event_type == "token":
                                            content = event.get("content", "")
                                            full_response += content
                                            response_placeholder.markdown(full_response + "▌")

                                        elif event_type == "suggested_prompts":
                                            new_prompts = event.get("prompts", [])
                                            if event.get("agent"):
                                                active_agent = event.get("agent")
                                                agent_placeholder.markdown(
                                                    f"<span class='mentor-badge'>{active_agent}</span>",
                                                    unsafe_allow_html=True,
                                                )

                                        elif event_type == "error":
                                            response_placeholder.error(f"Error: {event.get('content')}")
                                    except json.JSONDecodeError:
                                        pass

                            # Final render without cursor
                            response_placeholder.markdown(full_response)
                            if active_agent:
                                agent_placeholder.markdown(
                                    f"<span class='mentor-badge'>{active_agent}</span>",
                                    unsafe_allow_html=True,
                                )

                if not full_response:
                    full_response = " No response received from mentor. Please check backend logs."

                # Save assistant turn to chat state
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": full_response,
                        "agent": active_agent,
                    }
                )
                if new_prompts:
                    st.session_state.suggested_prompts = new_prompts
                st.rerun()

            except httpx.ConnectError:
                response_placeholder.error(
                    f"Could not connect to {stream_url}. Please ensure the FastAPI server is running."
                )
            except Exception as e:
                response_placeholder.error(f"Unexpected error: {str(e)}")
