# streamlit_app.py ── Vrtly Bug Cutter frontend
import streamlit as st, streamlit.components.v1 as components
from urllib.parse import urlparse
import requests, traceback, io, base64

BACKEND_URL = "https://bug-cutter-backend.onrender.com"

st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── header: logo + title ──────────────────────────────────────────────────────
st.image("vrtly_logo.jpg", width=220)
st.title("Vrtly Bug Cutter")

# ── auth / access-token capture ───────────────────────────────────────────────
query_params = st.query_params.to_dict()
access_token = query_params.get("access_token")

if access_token:
    st.session_state["access_token"] = access_token
    st.success("Logged in via Jira")
    components.html(
        """<script>history.replaceState(null,null,window.location.pathname)</script>""",
        height=0)
else:
    st.warning("Please log in with Jira to continue.")

token = st.session_state.get("access_token")
if not token:
    st.stop()

# ── logged-in info ────────────────────────────────────────────────────────────
me = requests.get(f"{BACKEND_URL}/me", params={"token": token}).json()
reporter_email = me.get("email") or "(unknown)"
st.markdown(f"**Logged in as:** {reporter_email}")

st.divider()

# ── form ──────────────────────────────────────────────────────────────────────
with st.form("bug_form", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        summary   = st.text_input("Summary / Title")
        description = st.text_area(
            "Description",
            "Org Name:\nOrg ID:\nIssue:\nExpected Behavior:",
            height=160)

    with col2:
        priority      = st.selectbox("Priority",
                                     ["Lowest", "Low", "Medium", "High", "Highest"])
        category      = st.selectbox("Bug Category",
                                     ["Web UI", "App", "Back End", "Admin", "Other"])
        assignee_search = st.text_input("Search Assignee (type to search)")
        assignee_id   = ""

        if assignee_search:
            r = requests.get(f"{BACKEND_URL}/search_users",
                             params={"q": assignee_search, "token": token})
            if r.ok:
                users = r.json()
                names = [u["displayName"] for u in users]
                selected = st.selectbox("Select Assignee", names)
                assignee_id = next(u["accountId"] for u in users
                                   if u["displayName"] == selected)

    st.file_uploader("Screenshot / Video (optional)",
                     type=["png", "jpg", "jpeg", "mp4"],
                     key="file_up")

    # preview if image
    if (file := st.session_state.get("file_up")) and file.type.startswith("image"):
        st.image(file, caption=file.name, width=320)

    submitted = st.form_submit_button("Submit Bug")
    if submitted:
        try:
            data = {
                "summary": summary,
                "description": description,
                "priority": priority,
                "category": category,
                "assignee": assignee_id,
                "components": "",
                "subtasks": "",
                "token": token,
            }
            files = {}
            if file:
                files["files"] = (file.name, file.getvalue(), file.type)

            resp = requests.post(f"{BACKEND_URL}/submit_bug/",
                                 data=data, files=files).json()

            if resp.get("success"):
                st.success(f"Bug {resp['issue_key']} created.")
            else:
                st.error(f"Backend returned: {resp}")
        except Exception as e:
            st.error(f"Error:\n{traceback.format_exc()}")
