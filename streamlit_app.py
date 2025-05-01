import streamlit as st, streamlit.components.v1 as components
import requests, traceback, base64, pathlib

BACKEND_URL = "https://bug-cutter-backend.onrender.com"
st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── header ────────────────────────────────────────────────────────────────────
def header_inline(img: str, h: int = 36):
    b64 = base64.b64encode(pathlib.Path(img).read_bytes()).decode()
    st.markdown(
        f'''
        <div style="display:flex;align-items:center;margin-bottom:8px">
          <img src="data:image/png;base64,{b64}" height="{h}" style="margin-right:10px">
          <span style="font-size:1.9rem;font-weight:700;">Vrtly&nbsp;Bug&nbsp;Cutter</span>
        </div>
        ''', unsafe_allow_html=True)

header_inline("vrtly_logo.png")

# ── oauth capture ─────────────────────────────────────────────────────────────
qp = st.query_params.to_dict()
if (t := qp.get("access_token")):
    st.session_state["access_token"] = t
    st.success("Logged in via Jira")
    components.html("<script>history.replaceState(null,null,window.location.pathname)</script>", height=0)

token = st.session_state.get("access_token")
if not token:
    st.markdown(f"[Log in with Jira]({BACKEND_URL}/auth/start)", unsafe_allow_html=True)
    st.stop()

me = requests.get(f"{BACKEND_URL}/me", params={"token": token}).json()
st.markdown(f"**Logged in as:** {me.get('email','(unknown)')}"); st.divider()

# ── fields ────────────────────────────────────────────────────────────────────
summary  = st.text_input("Summary / Title")
description = st.text_area("Description", "Org Name:\nOrg ID:\nIssue:\nExpected Behavior:", height=160)
priority = st.selectbox("Priority", ["Lowest","Low","Medium","High","Highest"])
category = st.selectbox("Bug Category", ["Web UI","App","Back End","Admin","Other"])

# assignee search: type ≥2 chars ➔ press Enter ➔ dropdown appears
assignee_search = st.text_input("Search assignee")
assignee_id   = ""
assignee_name = ""
users = []
if assignee_search and len(assignee_search) >= 2:
    resp = requests.get(f"{BACKEND_URL}/search_users", params={"q": assignee_search, "token": token})
    users = resp.json() if resp.ok and isinstance(resp.json(), list) else []
if users:
    names  = [u["displayName"] for u in users]
    chosen = st.selectbox("Select assignee", names, key="assignee_box")
    assignee_name = chosen
    assignee_id   = next(u["accountId"] for u in users if u["displayName"] == chosen)

uploads = st.file_uploader("Screenshot / Video (optional)", type=["png","jpg","jpeg","mp4","mpeg4"], accept_multiple_files=True)
for u in uploads:
    if u.type.startswith("image"): st.image(u, caption=u.name, width=320)

st.divider()

# ── review -> confirm flow ────────────────────────────────────────────────────
if "review_mode" not in st.session_state: st.session_state["review_mode"]=False

if not st.session_state["review_mode"]:
    if st.button("Review Bug"):
        st.session_state["review_mode"]=True; st.rerun()
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
            cols[i%3].image(u, caption=u.name, width=220)
        else:
            cols[i%3].markdown(f"📎 {u.name}")

c1,c2 = st.columns([1,1])
confirm = c1.button("Confirm Submit")
cancel  = c2.button("Cancel")
if cancel:
    st.session_state["review_mode"]=False; st.rerun()

if confirm:
    try:
        payload = dict(summary=summary, description=description, priority=priority,
                       category=category, assignee=assignee_id, components="",
                       subtasks="", token=token)
        files=[("files",(u.name,u.getvalue(),u.type)) for u in uploads]
        r=requests.post(f"{BACKEND_URL}/submit_bug/",data=payload,files=files); r.raise_for_status()
        st.success(f"Bug {r.json()['issue_key']} created."); st.session_state["review_mode"]=False
    except Exception: st.error(f"Error:\n{traceback.format_exc()}")
