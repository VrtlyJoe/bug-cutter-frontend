# streamlit_app.py  –  Vrtly Bug Cutter  (header fix only)
import streamlit as st, streamlit.components.v1 as components
import requests, traceback, base64, pathlib

BACKEND_URL = "https://bug-cutter-backend.onrender.com"    # adjust if needed
st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ────────── header (logo inline with title, no emojis) ────────────────────────
def inline_header(png_path: str, height: int = 36) -> None:
    b64 = base64.b64encode(pathlib.Path(png_path).read_bytes()).decode()
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;margin-bottom:8px">
          <img src="data:image/png;base64,{b64}" height="{height}"
               style="margin-right:10px">
          <span style="font-size:1.9rem;font-weight:700;">Vrtly&nbsp;Bug&nbsp;Cutter</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

inline_header("vrtly_logo.png")

# ────────── access-token capture ──────────────────────────────────────────────
query = st.query_params.to_dict()
if (tok := query.get("access_token")):
    st.session_state["access_token"] = tok
    st.success("Logged in via Jira")
    components.html(
        "<script>history.replaceState(null,null,window.location.pathname)</script>",
        height=0,
    )

token = st.session_state.get("access_token")

# show Jira login link if needed
if not token:
    st.markdown(f"[Log in with Jira]({BACKEND_URL}/auth/start)", unsafe_allow_html=True)
    st.stop()

# ────────── reporter info ─────────────────────────────────────────────────────
me = requests.get(f"{BACKEND_URL}/me", params={"token": token}).json()
st.markdown(f"**Logged in as:** {me.get('email', '(unknown)')}")
st.divider()

# ────────── form (unchanged) ─────────────────────────────────────────────────
with st.form("bug_form"):
    col1, col2 = st.columns(2)

    with col1:
        summary = st.text_input("Summary / Title")
        description = st.text_area(
            "Description",
            "Org Name:\nOrg ID:\nIssue:\nExpected Behavior:",
            height=160,
        )

    with col2:
        priority = st.selectbox("Priority", ["Lowest", "Low", "Medium", "High", "Highest"])
        category = st.selectbox("Bug Category", ["Web UI", "App", "Back End", "Admin", "Other"])

        # assignee search (unchanged)
        assignee_search = st.text_input("Search assignee")
        assignee_id = ""
        if assignee_search:
            r = requests.get(f"{BACKEND_URL}/search_users",
                             params={"q": assignee_search, "token": token})
            if r.ok and r.json():
                users = r.json()
                names = [u["displayName"] for u in users]
                selected = st.selectbox("Select assignee", names)
                assignee_id = next(u["accountId"] for u in users if u["displayName"] == selected)

    # file upload + immediate preview (unchanged)
    file_up = st.file_uploader("Screenshot / Video (optional)",
                               type=["png", "jpg", "jpeg", "mp4"])
    if file_up and file_up.type.startswith("image"):
        st.image(file_up, caption=file_up.name, width=320)

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
            files = {"files": (file_up.name, file_up.getvalue(), file_up.type)} if file_up else {}
            r = requests.post(f"{BACKEND_URL}/submit_bug/", data=data, files=files)
            r.raise_for_status()
            st.success(f"Bug {r.json()['issue_key']} created.")
        except Exception:
            st.error(f"Error:\n{traceback.format_exc()}")
