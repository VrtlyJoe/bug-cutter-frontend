import streamlit as st
import requests

st.set_page_config(page_title="Bug Cutter", layout="centered")

BACKEND_URL = "https://bug-cutter-backend.onrender.com"
query_params = st.query_params
if "access_token" in query_params:
    st.session_state["access_token"] = query_params["access_token"]

st.title("🐞 Bug Cutter Dashboard")
st.markdown("Welcome to the Bug Cutter App. Cut bugs. Add subtasks. Connect with Jira.")

st.subheader("🔐 Jira Authentication")

if "access_token" not in st.session_state:
    st.markdown(f"[🔗 Click here to connect Jira]({BACKEND_URL}/auth/start)")
else:
    st.success("🔐 Logged in with Jira")
    st.write("Access Token:", st.session_state["access_token"])

st.subheader("🪓 Submit a Bug")

with st.form("bug_submit_form"):
    summary = st.text_input("📝 Summary")
    description = st.text_area("🗒 Description")
    priority = st.selectbox("🔥 Priority", ["High", "Medium", "Low"])
    category = st.text_input("📁 Category")
    assignee = st.text_input("👤 Assignee (optional)", placeholder="jira.username")
    components = st.text_input("🏷 Components (optional, comma-separated)")
    subtasks = st.text_area("📌 Subtasks (one per line)", height=100)
    uploaded_files = st.file_uploader("📎 Attach files", accept_multiple_files=True)

    submit = st.form_submit_button("🚀 Submit Bug")

if submit:
    if "access_token" not in st.session_state:
        st.error("Please log in to Jira first.")
    elif not summary or not description or not priority or not category:
        st.warning("Please fill out all required fields.")
    else:
        with st.spinner("Creating bug..."):
            files = [("files", (f.name, f.read())) for f in uploaded_files] if uploaded_files else []
            payload = {
                "summary": summary,
                "description": description,
                "priority": priority,
                "category": category,
                "assignee": assignee,
                "components": components,
                "subtasks": subtasks,
                "token": st.session_state["access_token"],
            }
            try:
                response = requests.post(
                    f"{BACKEND_URL}/submit_bug/",
                    data=payload,
                    files=files if files else None,
                )
                if response.status_code == 200:
                    st.success(f"✅ Bug created: {response.json().get('issue_key')}")
                else:
                    st.error(f"❌ Error: {response.status_code}")
                    st.text(response.text)
            except Exception as e:
                st.error(f"Request failed: {e}")

st.markdown("---")
st.caption("🛠 Powered by Bug Cutter, Atlassian, Slack, and Streamlit.")