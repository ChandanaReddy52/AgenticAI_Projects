#app.py
import streamlit as st
from chat_controller import ChatController
from feedback_logger import log_feedback

st.set_page_config(
    page_title="Vehicle Support Assistant",
    layout="wide"
)

st.title("🚗 Hyundai Vehicle Support Assistant")

@st.cache_resource
def load_chat():
    return ChatController()

if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "chat" not in st.session_state:
    st.session_state.chat = load_chat()

user_input = st.chat_input("Ask a question about your vehicle")

if user_input:

    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    answer = st.session_state.chat.ask(user_input)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )

for i, msg in enumerate(st.session_state.messages):

    with st.chat_message(msg["role"]):
        st.write(msg["content"])

        if msg["role"] == "assistant":

            col1, col2 = st.columns(2)

            with col1:
                if st.button("👍 Helpful", key=f"up_{i}"):

                    log_feedback(
                        st.session_state.messages[i-1]["content"],
                        msg["content"],
                        "up"
                    )

                    st.success("Feedback recorded")

            with col2:
                if st.button("👎 Not Helpful", key=f"down_{i}"):

                    log_feedback(
                        st.session_state.messages[i-1]["content"],
                        msg["content"],
                        "down"
                    )

                    st.warning("Feedback recorded")