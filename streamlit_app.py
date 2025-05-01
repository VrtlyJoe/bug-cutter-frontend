import streamlit as st, streamlit.components.v1 as components
import requests, traceback
from PIL import Image

st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── token capture ───────────────────────────────────────
params = st.query_params.to_dict()
if "access_token" in params:
    st.session_state["access_token"] = params["access_token"]
    components.html("<script>history.replaceState(null,null,location.pathname)</script>", height=0)

if "access_token" not in st.session_state:
    st.title("🐞 Vrtly Bug Cutter")
    st.markdown("[🔑 Log in with Jira »](https://bug-cutter-backend.onrender.com/auth/start)", unsafe_allow_html=True)
    st.stop()

token = st.session_state["access_token"]

# ── “logged in as” banner ──────────────────────────────
try:
    reporter_email = requests.get("https://bug-cutter-backend.onrender.com/me",
                                  params={"token": token}, timeout=5).json().get("email","")
except Exception: reporter_email = ""
st.markdown(f"✅ **Logged in as {reporter_email or '(unknown)'}**", unsafe_allow_html=True)

# ── static dropdown data ───────────────────────────────
BUG_CATS = ["Web UI","App","Back End","Admin","Other"]
PRIO     = ["Lowest","Low","Medium","High","Highest"]

# ── screenshot uploader (outside form → instant preview) ─
st.subheader("Screenshot (optional)")
image_file = st.file_uploader("Upload PNG / JPG", type=["png","jpg","jpeg"])
if image_file:
    img = Image.open(image_file)
    w,h = img.size
    st.info(f"Preview: {w}×{h}px")
    st.image(img, width=min(w, 300))

st.divider()

# ── bug form in requested order ────────────────────────
st.title("🐞 Vrtly Bug Cutter")
with st.form("bug_form"):
    summary      = st.text_input("Summary / Title")
    description  = st.text_area("Description", height=220)
    priority     = st.selectbox("Priority", PRIO, index=PRIO.index("Medium"))
    category     = st.selectbox("Bug Category", BUG_CATS)

    confirm      = st.checkbox("Confirm and submit")
    submitted    = st.form_submit_button("✂️ Cut Bug")

# ── submission flow ────────────────────────────────────
if submitted:
    if not confirm:
        st.error("Please confirm"); st.stop()
    if not summary or not description.strip():
        st.error("Summary & Description required"); st.stop()

    data  = {
        "summary": summary, "description": description,
        "priority": priority, "category": category,
        "token": token,
        "assignee": "",           # no assignee search in current spec
        "components": "",         # removed per spec
        "subtasks": "",
    }
    files = {"files": image_file} if image_file else None

    with st.spinner("Submitting…"):
        try:
            r = requests.post("https://bug-cutter-backend.onrender.com/submit_bug/",
                              data=data, files=files); r.raise_for_status()
            key = r.json()["issue_key"]
            st.success(f"✅ Created!  [{key}](https://vrtlyai.atlassian.net/browse/{key})")
        except Exception:
            st.error("❌ Submission failed"); st.text(traceback.format_exc())
