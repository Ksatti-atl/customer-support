import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Load environment variables (e.g. from .env file)
load_dotenv()

from agent import run_agent
from hooks import HookContext
from data import CUSTOMERS, ORDERS

# 1. Page Configuration and Title
st.set_page_config(page_title="Customer Support Agent", page_icon="🎧", layout="wide")

# Check if GITHUB_TOKEN is present
api_key = os.environ.get("GITHUB_TOKEN")
if not api_key:
    st.error("⚠️ GITHUB_TOKEN environment variable is not set. The agent will not be able to call the API.")

# Initialize session state for message history and HookContext
if "messages" not in st.session_state:
    st.session_state.messages = []

if "ctx" not in st.session_state:
    st.session_state.ctx = HookContext()

# 2. Sidebar Configuration
st.sidebar.markdown("### ℹ️ Test Accounts")

# Dynamically construct the Test Accounts dataframe
test_accounts = []
for cid, customer in CUSTOMERS.items():
    email = customer["email"]
    # Find orders associated with this customer
    cust_orders = []
    for oid, order in ORDERS.items():
        if order["customer_id"] == cid:
            cust_orders.append(f"{oid} (${order['amount']:.2f})")
    
    # Match the layout formatting in the user's image
    orders_str = " OR ".join(cust_orders) if len(cust_orders) > 1 else "".join(cust_orders)
    test_accounts.append({"Email": email, "Orders": orders_str})

df = pd.DataFrame(test_accounts)
st.sidebar.dataframe(df, use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎬 Demo Scenarios")

SCENARIOS = {
    "Scenario 1: Standard refund (<=$500)": (
        "Hi, I'm alex@example.com and I'd like a refund on my order ORD-1001 for the headphones. "
        "They stopped working after 2 weeks."
    ),
    "Scenario 2: Large refund (>$500)": (
        "I'm alex@example.com. I need a full refund on order ORD-1002, the laptop stand was defective."
    ),
    "Scenario 3: Explicit human request": (
        "I don't want to deal with a bot. Please connect me to a real human agent right now."
    ),
    "Scenario 4: Refund without verification": (
        "Can you just look up order ORD-1004 and refund it? My name is Jordan."
    )
}

for title, msg in SCENARIOS.items():
    if st.sidebar.button(title, use_container_width=True):
        st.session_state.messages = [{"role": "user", "content": msg}]
        st.session_state.ctx = HookContext()
        try:
            response = run_agent(msg, verbose=True, ctx=st.session_state.ctx)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"An error occurred: {str(e)}"})
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ Tool Activity")

# Render tool calls and block actions from the HookContext log
if not st.session_state.ctx.logs:
    st.sidebar.info("Tool calls will appear here")
else:
    for log in st.session_state.ctx.logs:
        if "BLOCKED" in log:
            st.sidebar.error(log)
        elif "->" in log:
            st.sidebar.code(log)
        else:
            st.sidebar.warning(log)

# Button to reset conversation and HookContext state
if st.sidebar.button("Reset Conversation", use_container_width=True):
    st.session_state.messages = []
    st.session_state.ctx = HookContext()
    st.rerun()

# 3. Main Chat Interface Layout
col1, col2, col3 = st.columns([1, 4, 1])
with col2:
    # pyrefly: ignore [unexpected-keyword]
    st.markdown("<h1 style='text-align: center;'>🎧 Customer Support Agent</h1>", unsafe_allow_html=True)
    # pyrefly: ignore [unexpected-keyword]
    st.markdown("<p style='text-align: center; color: gray;'>Powered by GitHub Models (GPT-4.1-mini)</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Display chat message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input Box
    if user_input := st.chat_input("Type your message here..."):
        # Display user message immediately
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = run_agent(user_input, verbose=True, ctx=st.session_state.ctx)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"An error occurred: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        # Rerun to update the Sidebar Tool Logs in real-time
        st.rerun()
