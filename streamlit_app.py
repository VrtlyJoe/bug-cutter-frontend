# streamlit_app.py
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import urlparse, parse_qs
import requests  # in case your app needs backend calls
import traceback

# --- GLOBAL APP CONFIG ---
st.set_page_config(page_title="Bug Cutter", layout="wide")

# --- DEBUG: PAGE LOAD TRACKING ---
st.write("🌀 App loaded")

# --- QUERY PARAM + AUTH HANDLING ---
query_params = st.query_params.to_dict()
access_token = query_params.get("access_token", None)
st.write("🔍 Query parameters:", query_params)

if access_token:
    st.session_state["access_token"] = access_token
    st.success("✅ Access token captured")
    
    # Cleanup URL
    components.html("""
        <script>
            const newUrl = window.location.origin + window.location.pathname;
            window.history.replaceState(null, null, newUrl);
        </script>
    """, height=0)
else:
    st.warning("⚠️ No access token found in query params.")

# --- SESSION DEBUGGING ---
st.subheader("🧪 Session Debug")
st.write(st.session_state)

# --- UI HEADER ---
st.title("🐛 Bug Cutter App")

# --- PLACEHOLDER: DUPLICATE CHECK (SAFE) ---
if st.checkbox("Run Duplicate Ticket Check"):
    try:
        st.info("🔍 Checking for duplicates...")
        # Replace with real logic
        # Example dummy check
        # response = requests.get("https://your-backend/api/check-duplicate", headers={"Authorization": f"Bearer {access_token}"})
        # result = response.json()
        result = {"status": "ok", "duplicate": False}  # dummy result
        st.success(f"✅ Duplicate check complete: {result}")
    except Exception as e:
        st.error(f"❌ Error during duplicate check:\n{traceback.format_exc()}")

# --- PLACEHOLDER: MAIN APP CONTENT ---
st.write("📋 Bug cutting form or interface will go here.")
