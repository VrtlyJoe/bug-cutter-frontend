import streamlit as st
import streamlit.components.v1 as components
import requests
import traceback

# --- CONFIG ---
st.set_page_config(page_title="Bug Cutter", layout="wide")
st.write("🌀 Bug Cutter Loaded")

# --- QUERY PARAM + ACCESS TOKEN HANDLING ---
query_params = st.query_params.to_dict()
access_token = query_params.get("access_token", None)
st.write("🔍 Query parameters:", query_params)

if access_token:
    st.session_state["access_token"] = access_token
    st.success("✅ Jira access token captured from URL")
    # Clean the URL
    components.html("""
        <script>
            const newUrl = window.location.origin + window.location.pathname;
            window.history.replaceState(null, null, newUrl);
        </script>
    """, height=0)

# --- LOGIN PROMPT ---
if "access_token" not in st.session_state:
    st.warning("🔐 You are not logged in with Jira.")
    st.markdown("[Click here to login with Jira](https://bug-cutter-backend.onrender.com/auth/start)")
    st.stop()
else:
    token = st.session_state["access_token"]
    st.info("🔐 Jira token is active. You may now cut bugs.")

# --- MAIN FORM ---
st.title("🐛 Cut a New Bug")

with st.form("bug_form"):
    summary = st.text_input("📝 Summary", max_chars=150)
    description = st.text_area("📄 Description")
    priority = st.selectbox("🔥 Priority", ["Lowest", "Low", "Medium", "High", "Highest"])
    category = st.selectbox("🐞 Bug Category", ["UI", "Backend", "Performance", "Integration", "Other"])
    assignee = st.text_input("👤 Assignee (Jira username)")
    components = st.text_input("📦 Component(s), comma-separated")
    subtasks = st.text_area("🪜 Optional Subtasks (one per line)")
    image = st.file_uploader("📷 Optional Screenshot", type=["png", "jpg", "jpeg"])
    confirm = st.checkbox("✅ Confirm and submit")
    submitted = st.form_submit_button("✂️ Cut Bug")

if submitted:
    if not confirm:
        st.error("Please confirm before submitting.")
    elif not summary or not description:
        st.error("Summary and Description are required.")
    else:
        try:
            with st.spinner("Submitting bug to backend..."):
                files = {"files": image} if image else None
                data = {
                    "summary": summary,
                    "description": description,
                    "priority": priority,
                    "category": category,
                    "assignee": assignee,
                    "components": components,
                    "subtasks": subtasks,
                    "token": token
                }
                response = requests.post("https://bug-cutter-backend.onrender.com/submit_bug/", data=data, files=files)
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ Bug cut successfully! Jira Key: {result['issue_key']}")
                    st.markdown(f"[View in Jira](https://vrtlyai.atlassian.net/browse/{result['issue_key']})")
                else:
                    st.error(f"❌ Backend error: {response.status_code}")
                    st.text(response.text)
        except Exception:
            st.error("Exception occurred during bug submission.")
            st.text(traceback.format_exc())

# --- DUPLICATE CHECK ---
if st.checkbox("🔁 Check for Similar Bugs"):
    try:
        st.info("Checking for similar bugs in Jira...")
        query = summary or ""
        response = requests.get("https://bug-cutter-backend.onrender.com/search_bugs", params={"q": query, "token": token})
        if response.status_code == 200:
            matches = response.json()["results"]
            if matches:
                st.warning("🚨 Similar bugs found:")
                for m in matches:
                    st.markdown(f"- [{m['key']}] {m['summary']}")
            else:
                st.success("✅ No similar bugs found.")
        else:
            st.error(f"❌ Error searching: {response.status_code}")
            st.text(response.text)
    except Exception:
        st.error("Exception occurred during duplicate check.")
        st.text(traceback.format_exc())
