# streamlit_app.py – Vrtly Bug Cutter (header fix + robust assignee search)
import streamlit as st, streamlit.components.v1 as components
import requests, traceback, base64, pathlib

BACKEND_URL = "https://bug-cutter-backend.onrender.com"
st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ───────── header (inline logo + title) ───────────────────────────────────────
def header_inline(png: str, h: int = 36):
    b64 = base64.b64encode(pathlib.Path(png).read_bytes()).decode()
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;margin-bottom:8px">
          <img src="data:image/png;base64,{b64}" height="{h}" style="margin-right:10px">
          <span style="font-size:1.9rem;font-weight:700;">Vrtly&nbsp;Bug&nbsp;Cutter</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

header_inline("vrtly_logo.png")

# ───────── Jira auth boilerplate ──────────────────────────────────────────────
qp = st.query_params.to_dict()
if (tok := qp.get("access_token")):
    st.session_state["access_token"] = tok
    st.success("Logged in via Jira")
    components.html("<script>history.replaceState(null,null,window.location.pathname)</script>", height=0)

token = st.session_state.get("access_token")
if not token:
    st.markdown(f"[Log in with Jira]({BACKEND_URL}/auth/start)", unsafe_allow_html=True)
    st.stop()

me = requests.get(f"{BACKEND_URL}/me", params={"token": token}).json()
reporter_email = me.get("email", "(unknown)")
st.markdown(f"**Logged in as:** {reporter_email}")
st.divider()

# ───────── ticket inputs (same order) ────────────────────────────────────────
summary = st.text_input("Summary / Title")
description = st.text_area(
    "Description",
    "Org Name:\nOrg ID:\nIssue:\nExpected Behavior:",
    height=160,
)
priority  = st.selectbox("Priority",     ["Lowest", "Low", "Medium", "High", "Highest"])
category  = st.selectbox("Bug Category", ["Web UI", "App", "Back End", "Admin", "Other"])

# -- assignee search (robust) --------------------------------------------------
assignee_search = st.text_input("Search assignee")
assignee_id, assignee_name = "", ""
if assignee_search:
    res = requests.get(f"{BACKEND_URL}/search_users",
                       params={"q": assignee_search, "token": token})
    if res.ok:
        data = res.json()
        if isinstance(data, list) and data:                 # ← guard against bad response
            names = [u["displayName"] for u in data]
            chosen = st.selectbox("Select assignee", names, key="assignee_box")
            assignee_name = chosen
            assignee_id   = next(u["accountId"] for u in data if u["displayName"] == chosen)
        else:
            st.warning("No users found or search service unavailable")

# -- uploader & previews -------------------------------------------------------
uploads = st.file_uploader("Screenshot / Video (optional)",
                           type=["png", "jpg", "jpeg", "mp4", "mpeg4"],
                           accept_multiple_files=True, key="file_up")
for up in uploads:
    if up.type.startswith("image"):
        st.image(up, caption=up.name, width=320)

st.divider()

# ───────── review overlay / confirm-submit (unchanged) ───────────────────────
if "review_mode" not in st.session_state:
    st.session_state["review_mode"] = False

if not st.session_state["review_mode"]:
    if st.button("Review Bug"):
        st.session_state["review_mode"] = True
        st.experimental_rerun()
    st.stop()

st.subheader("Review Bug")
st.write(f"**Summary:** {summary or '*blank*'}")
st.write(f"**Priority:** {priority} &nbsp;&nbsp; **Category:** {category}")
st.write(f"**Assignee:** {assignee_name or '—'}")
st.write("**Description:**"); st.code(description, language="markdown")

if uploads:
    st.write("**Attachments Preview:**")
    cols = st.columns(min(len(uploads), 3))
    for i, up in enumerate(uploads):
        if up.type.startswith("image"):
            cols[i % 3].image(up, caption=up.name, width=220)
        else:
            cols[i % 3].markdown(f"📎 {up.name}")

colA, colB = st.columns([1, 1])
confirm = colA.button("Confirm Submit", key="confirm_btn")
cancel  = colB.button("Cancel",          key="cancel_btn")

if cancel:
    st.session_state["review_mode"] = False
    st.experimental_rerun()

if confirm:
    try:
        payload = dict(
            summary=summary,
            description=description,
            priority=priority,
            category=category,
            assignee=assignee_id,
            components="",
            subtasks="",
            token=token,
        )
        files = [("files", (u.name, u.getvalue(), u.type)) for u in uploads]
        resp  = requests.post(f"{BACKEND_URL}/submit_bug/", data=payload, files=files)
        resp.raise_for_status()
        st.success(f"Bug {resp.json()['issue_key']} created.")
        st.session_state["review_mode"] = False
    except Exception:
        st.error(f"Error:\n{traceback.format_exc()}")
