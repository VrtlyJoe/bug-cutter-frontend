# streamlit_app.py  |  Vrtly Bug Cutter – all business
import streamlit as st, streamlit.components.v1 as components
import requests, traceback, base64, pathlib

BACKEND_URL = "https://bug-cutter-backend.onrender.com"
st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ═══ Header: logo + title (left-aligned) ══════════════════════════════════════
def header_inline(png_file: str, h: int = 36):
    b64 = base64.b64encode(pathlib.Path(png_file).read_bytes()).decode()
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

# ═══ Jira OAuth token capture ═════════════════════════════════════════════════
qp = st.query_params.to_dict()
if (tok := qp.get("access_token")):
    st.session_state["access_token"] = tok
    st.success("Logged in via Jira")
    components.html(
        "<script>history.replaceState(null,null,window.location.pathname)</script>",
        height=0,
    )

token = st.session_state.get("access_token")
if not token:
    st.markdown(f"[Log in with Jira]({BACKEND_URL}/auth/start)", unsafe_allow_html=True)
    st.stop()

# reporter identity
me = requests.get(f"{BACKEND_URL}/me", params={"token": token}).json()
reporter_email = me.get("email", "(unknown)")
st.markdown(f"**Logged in as:** {reporter_email}")
st.divider()

# ═══ Ticket fields (straight order) ═══════════════════════════════════════════
summary = st.text_input("Summary / Title")
description = st.text_area(
    "Description",
    "Org Name:\nOrg ID:\nIssue:\nExpected Behavior:",
    height=160,
)
priority = st.selectbox("Priority", ["Lowest", "Low", "Medium", "High", "Highest"])
category = st.selectbox("Bug Category", ["Web UI", "App", "Back End", "Admin", "Other"])

# ── Assignee search: fires after 2+ chars, dropdown after ENTER ──────────────
assignee_search = st.text_input("Search assignee")
assignee_id, assignee_name = "", ""
if assignee_search and len(assignee_search) >= 2:
    r = requests.get(
        f"{BACKEND_URL}/search_users", params={"q": assignee_search, "token": token}
    )
    users = r.json() if r.ok and isinstance(r.json(), list) else []
    if users:
        names = [u["displayName"] for u in users]
        chosen = st.selectbox("Select assignee", names, key="assignee_box")
        assignee_name = chosen
        assignee_id = next(u["accountId"] for u in users if u["displayName"] == chosen)
    else:
        st.warning("No Jira users found.")

# ── File uploader & previews (multiple) ───────────────────────────────────────
uploads = st.file_uploader(
    "Screenshot / Video (optional)",
    type=["png", "jpg", "jpeg", "mp4", "mpeg4"],
    accept_multiple_files=True,
    key="file_up",
)
for up in uploads:
    if up.type.startswith("image"):
        st.image(up, caption=up.name, width=320)

st.divider()

# ═══ Review / Confirm workflow ═══════════════════════════════════════════════
if "review_mode" not in st.session_state:
    st.session_state["review_mode"] = False

# Step 1 – Review button
if not st.session_state["review_mode"]:
    if st.button("Review Bug"):
        st.session_state["review_mode"] = True
        st.rerun()
    st.stop()

# Step 2 – Summary overlay
st.subheader("Review Bug")
st.write(f"**Summary:** {summary or '*blank*'}")
st.write(f"**Priority:** {priority}   **Category:** {category}")
st.write(f"**Assignee:** {assignee_name or '—'}")
st.write("**Description:**")
st.code(description, language="markdown")

if uploads:
    st.write("**Attachments Preview:**")
    cols = st.columns(min(len(uploads), 3))
    for i, up in enumerate(uploads):
        if up.type.startswith("image"):
            cols[i % 3].image(up, caption=up.name, width=220)
        else:
            cols[i % 3].markdown(f"📎 {up.name}")

col_ok, col_cancel = st.columns([1, 1])
confirm = col_ok.button("Confirm Submit", key="confirm_btn")
cancel  = col_cancel.button("Cancel",          key="cancel_btn")

if cancel:
    st.session_state["review_mode"] = False
    st.rerun()

# Step 3 – Final push to backend
if confirm:
    try:
        payload = {
            "summary": summary,
            "description": description,
            "priority": priority,
            "category": category,
            "assignee": assignee_id,
            "components": "",
            "subtasks": "",
            "token": token,
        }
        files = [("files", (u.name, u.getvalue(), u.type)) for u in uploads]
        resp = requests.post(f"{BACKEND_URL}/submit_bug/", data=payload, files=files)
        resp.raise_for_status()
        st.success(f"Bug {resp.json()['issue_key']} created.")
        st.session_state["review_mode"] = False
    except Exception:
        st.error(f"Error:\n{traceback.format_exc()}")
