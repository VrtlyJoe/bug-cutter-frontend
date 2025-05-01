# streamlit_app.py  –  Vrtly Bug Cutter
import streamlit as st, streamlit.components.v1 as components
import requests, traceback

BACKEND_URL = "https://bug-cutter-backend.onrender.com"   # change if needed

st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ────────── header: logo + title ──────────────────────────────────────────────
st.image("vrtly_logo.png", width=220)   # <-- use your PNG logo here
st.title("Vrtly Bug Cutter")

# ────────── capture ?access_token=... ─────────────────────────────────────────
query_params = st.query_params.to_dict()
if (tok := query_params.get("access_token")):
    st.session_state["access_token"] = tok
    st.success("Logged in via Jira")
    # scrub token from address bar
    components.html(
        "<script>history.replaceState(null,null,window.location.pathname)</script>",
        height=0,
    )

token = st.session_state.get("access_token")

# ────────── if not logged-in show Jira link & stop ────────────────────────────
if not token:
    st.markdown(
        f"[Log in with Jira]({BACKEND_URL}/auth/start)",
        unsafe_allow_html=True,
    )
    st.stop()

# ────────── show reporter e-mail ──────────────────────────────────────────────
me = requests.get(f"{BACKEND_URL}/me", params={"token": token}).json()
reporter_email = me.get("email") or "(unknown)"
st.markdown(f"**Logged in as:** {reporter_email}")
st.divider()

# ────────── bug-form ──────────────────────────────────────────────────────────
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
        priority = st.selectbox(
            "Priority", ["Lowest", "Low", "Medium", "High", "Highest"]
        )
        category = st.selectbox(
            "Bug Category", ["Web UI", "App", "Back End", "Admin", "Other"]
        )

        # ── assignee search ─────────────────────────────
        assignee_search = st.text_input("Search assignee")
        assignee_id = ""
        if assignee_search:
            r = requests.get(
                f"{BACKEND_URL}/search_users",
                params={"q": assignee_search, "token": token},
            )
            if r.ok and r.json():
                users = r.json()
                names = [u["displayName"] for u in users]
                selected = st.selectbox("Select assignee", names)
                assignee_id = next(
                    u["accountId"]
                    for u in users
                    if u["displayName"] == selected
                )

    # ───────── file upload + preview ───────────────────
    file_up = st.file_uploader(
        "Screenshot / Video (optional)", type=["png", "jpg", "jpeg", "mp4"]
    )
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
            files = (
                {"files": (file_up.name, file_up.getvalue(), file_up.type)}
                if file_up
                else {}
            )

            resp = requests.post(f"{BACKEND_URL}/submit_bug/", data=data, files=files)
            resp.raise_for_status()
            st.success(f"Bug {resp.json()['issue_key']} created.")
        except Exception:
            st.error(f"Error:\n{traceback.format_exc()}")
