import streamlit as st, streamlit.components.v1 as components
import requests, traceback, textwrap
from PIL import Image

st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── token capture ───────────────────────────────────────
qs = st.query_params.to_dict()
if "access_token" in qs:
    st.session_state["access_token"] = qs["access_token"]
    components.html("<script>history.replaceState(null,null,location.pathname)</script>", height=0)

if "access_token" not in st.session_state:
    st.title("🐞 Vrtly Bug Cutter")
    st.markdown("[Log in with Jira](https://bug-cutter-backend.onrender.com/auth/start)", unsafe_allow_html=True)
    st.stop()

token = st.session_state["access_token"]

# ── banner ──────────────────────────────────────────────
try:
    reporter_email = requests.get("https://bug-cutter-backend.onrender.com/me",
                                  params={"token": token}, timeout=5).json().get("email","")
except Exception: reporter_email = ""
st.markdown(f"✅ **Logged in as {reporter_email or '(unknown)'}**", unsafe_allow_html=True)

BUG_CATS = ["Web UI","App","Back End","Admin","Other"]
PRIORITY = ["Lowest","Low","Medium","High","Highest"]

st.title("🐞 Vrtly Bug Cutter")

# ────────────────── MAIN FORM ───────────────────────────
with st.form("bug_form"):
    summary = st.text_input("Summary / Title")

    default_desc = textwrap.dedent("""\
        Org Name:
        Org ID:
        Issue:
        Expected Behavior:
    """)
    description = st.text_area("Description", value=default_desc, height=220)

    priority  = st.selectbox("Priority", PRIORITY, index=PRIORITY.index("Medium"))
    category  = st.selectbox("Bug Category", BUG_CATS)

    confirm   = st.checkbox("Confirm and submit")
    submitted = st.form_submit_button("✂️ Cut Bug")

# ───────────── Screenshot uploader + preview ───────────
st.subheader("Screenshot (optional)")
image_file = st.file_uploader("Upload PNG / JPG", type=["png","jpg","jpeg"])
if image_file:
    img = Image.open(image_file)
    w, h = img.size
    st.info(f"Preview: {w}×{h}px")
    st.image(img, width=min(w, 300))

# ───────────── Assignee search block ───────────────────
@st.cache_data(ttl=60)
def search_users(q:str):
    if len(q) < 3: return []
    try:
        r = requests.get("https://bug-cutter-backend.onrender.com/search_users",
                         params={"q": q, "token": token}, timeout=5)
        return r.json().get("results", [])
    except Exception: return []

st.subheader("Assign to (optional)")
search_txt = st.text_input("Search Jira users (≥3 chars)")
users = search_users(search_txt) if len(search_txt)>=3 else []
assignee_disp = st.selectbox("Choose assignee",
                             ["-- none --"] + [u["displayName"] for u in users])
assignee_id = (next((u["accountId"] for u in users if u["displayName"]==assignee_disp),"")
               if assignee_disp!="-- none --" else "")

# ───────────── Submit handler ──────────────────────────
if submitted:
    if not confirm:
        st.error("Please confirm before submitting."); st.stop()
    if not summary or not description.strip():
        st.error("Summary & Description required."); st.stop()

    data = {
        "summary": summary,
        "description": description,
        "priority": priority,
        "category": category,
        "assignee": assignee_id,
        "components": "",      # components removed per MVP
        "subtasks": "",
        "token": token,
    }
    files = {"files": image_file} if image_file else None

    with st.spinner("Submitting…"):
        try:
            r = requests.post("https://bug-cutter-backend.onrender.com/submit_bug/",
                              data=data, files=files)
            r.raise_for_status()
            key = r.json()["issue_key"]
            st.success(f"✅ Created!  [{key}](https://vrtlyai.atlassian.net/browse/{key})")
        except Exception:
            st.error("❌ Submission failed"); st.text(traceback.format_exc())
