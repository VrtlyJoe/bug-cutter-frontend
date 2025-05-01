import streamlit as st, streamlit.components.v1 as components
import requests, traceback, base64, pathlib, uuid

BACKEND_URL = "https://bug-cutter-backend.onrender.com"
st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

def header_inline(img: str, h: int = 36):
    b64 = base64.b64encode(pathlib.Path(img).read_bytes()).decode()
    st.markdown(
        f"""<div style="display:flex;align-items:center;margin-bottom:8px">
        <img src="data:image/png;base64,{b64}" height="{h}" style="margin-right:10px">
        <span style="font-size:1.9rem;font-weight:700;">Vrtly&nbsp;Bug&nbsp;Cutter</span>
        </div>""", unsafe_allow_html=True)

header_inline("vrtly_logo.png")

# ── OAuth capture ─────────────────────────────────────────────────────────────
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
st.markdown(f"**Logged in as:** {me.get('emailAddress','(unknown)')}")
st.divider()

# ── Form fields ───────────────────────────────────────────────────────────────
summary  = st.text_input("Summary / Title")
description = st.text_area("Description",
    "Org Name:\nOrg ID:\nIssue:\nExpected Behavior:", height=160)
priority = st.selectbox("Priority", ["Lowest","Low","Medium","High","Highest"])
category = st.selectbox("Bug Category", ["Web UI","App","Back End","Admin","Other"])

assignee_query = st.text_input("Search assignee (type ≥2 chars, press Enter)")
users, assignee_id, assignee_name = [], "", ""
if assignee_query and len(assignee_query) >= 2 and st.session_state.get("assignee_trigger") != assignee_query:
    st.session_state["assignee_trigger"] = assignee_query
    try:
        resp = requests.get(f"{BACKEND_URL}/search_users",
                            params={"q": assignee_query, "token": token}, timeout=8)
        if resp.ok:
            users = resp.json()
    except Exception:
        users = []

if users:
    options = [u["displayName"] for u in users]
    choose  = st.selectbox("Select assignee", options, key=uuid.uuid4().hex)
    assignee_name = choose
    assignee_id   = next(u["accountId"] for u in users if u["displayName"] == choose)

uploads = st.file_uploader(
    "Screenshot / Video (optional)",
    type=["png","jpg","jpeg","mp4","mpeg4"],
    accept_multiple_files=True
)
for u in uploads:
    if u.type.startswith("image"):
        st.image(u, caption=u.name, width=320)

st.divider()

# ── Review + submit ───────────────────────────────────────────────────────────
if "review_mode" not in st.session_state:
    st.session_state["review_mode"] = False

if not st.session_state["review_mode"]:
    if st.button("Review Bug"):  # primary button
        st.session_state["review_mode"] = True
        st.experimental_rerun()
    st.stop()

st.subheader("Review Bug")
st.write(f"**Summary:** {summary or '*blank*'}")
st.write(f"**Priority:** {priority}   **Category:** {category}")
st.write(f"**Assignee:** {assignee_name or '—'}")
st.write("**Description:**"); st.code(description, language="markdown")
if uploads:
    st.write("**Attachments Preview:**")
    cols = st.columns(min(len(uploads),3))
    for i,u in enumerate(uploads):
        if u.type.startswith("image"):
            cols[i%3].image(u,caption=u.name,width=220)
        else:
            cols[i%3].markdown(f"📎 {u.name}")

c1,c2 = st.columns(2)
if c2.button("Cancel"): st.session_state["review_mode"]=False; st.experimental_rerun()
if c1.button("Confirm Submit", type="primary"):
    try:
        payload=dict(summary=summary,description=description,priority=priority,
                     category=category,assignee=assignee_id,components="",
                     subtasks="",token=token)
        files=[("files",(u.name,u.getvalue(),u.type)) for u in uploads]
        r=requests.post(f"{BACKEND_URL}/submit_bug/",data=payload,files=files, timeout=30)
        r.raise_for_status()
        st.success(f"Bug {r.json()['issue_key']} created.")
        st.session_state["review_mode"]=False
    except Exception:
        st.error(f"Error:\n{traceback.format_exc()}")
