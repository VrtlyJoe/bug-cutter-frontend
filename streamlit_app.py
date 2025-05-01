import streamlit as st, streamlit.components.v1 as components
import requests, traceback, textwrap, mimetypes
from PIL import Image

st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── capture Jira token ─────────────────────────────────
if "access_token" in st.query_params:
    st.session_state["access_token"] = st.query_params["access_token"]
    components.html("<script>history.replaceState(null,null,location.pathname)</script>", height=0)

if "access_token" not in st.session_state:
    st.title("🐞 Vrtly Bug Cutter")
    st.markdown("[Log in with Jira](https://bug-cutter-backend.onrender.com/auth/start)", unsafe_allow_html=True)
    st.stop()

token = st.session_state["access_token"]

# ── user banner ────────────────────────────────────────
try:
    me = requests.get("https://bug-cutter-backend.onrender.com/me",
                      params={"token": token}, timeout=5).json()
    email = me.get("email", "")
except Exception:
    email = ""
st.markdown(f"✅ **Logged in as {email or '(unknown)'}**", unsafe_allow_html=True)

BUG_CATS = ["Web UI","App","Back End","Admin","Other"]
PRIO     = ["Lowest","Low","Medium","High","Highest"]

st.title("🐞 Vrtly Bug Cutter")

# ────────────────── main form ──────────────────────────
with st.form("bug_form"):
    summary = st.text_input("Summary / Title")

    default = textwrap.dedent("""\
        Org Name:
        Org ID:
        Issue:
        Expected Behavior:
    """)
    description = st.text_area("Description", value=default, height=220)

    priority  = st.selectbox("Priority", PRIO, index=PRIO.index("Medium"))
    category  = st.selectbox("Bug Category", BUG_CATS)

    confirm   = st.checkbox("Confirm and submit")
    submitted = st.form_submit_button("✂️ Cut Bug")

# ─────────── file upload / preview ─────────────────────
st.subheader("Screenshot / Video (optional)")
file_up = st.file_uploader("Upload PNG / JPG / JPEG / MP4",
                           type=["png", "jpg", "jpeg", "mp4"])
if file_up:
    mime, _ = mimetypes.guess_type(file_up.name)
    if mime and mime.startswith("image"):
        img = Image.open(file_up)
        w, h = img.size
        st.info(f"Image preview • {w}×{h}px")
        st.image(img, width=min(w, 300))
    elif file_up.name.lower().endswith(".mp4"):
        st.info("Video preview")
        st.video(file_up)

# ─────────── assignee search ──────────────────────────
@st.cache_data(ttl=60)
def find_users(q: str):
    if len(q) < 3: return []
    try:
        r = requests.get("https://bug-cutter-backend.onrender.com/search_users",
                         params={"q": q, "token": token}, timeout=5)
        return r.json().get("results", [])
    except Exception:
        return []

st.subheader("Assign to (optional)")
search_q = st.text_input("Search Jira users (≥3 chars)")
users = find_users(search_q) if len(search_q) >= 3 else []
disp = st.selectbox("Choose assignee",
                    ["-- none --"] + [u["displayName"] for u in users])
assignee_id = next((u["accountId"] for u in users if u["displayName"] == disp), "") \
              if disp != "-- none --" else ""

# ─────────── submit handler ───────────────────────────
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
        "components": "",
        "subtasks": "",
        "token": token,
    }
    files = {"files": file_up} if file_up else None

    with st.spinner("Submitting…"):
        try:
            r = requests.post("https://bug-cutter-backend.onrender.com/submit_bug/",
                              data=data, files=files)
            r.raise_for_status()
            key = r.json()["issue_key"]
            st.success(f"✅ Created!  [{key}](https://vrtlyai.atlassian.net/browse/{key})")
        except requests.HTTPError as e:
            st.error("❌ Backend returned:")
            st.code(e.response.text if e.response is not None else str(e))
        except Exception:
            st.error("❌ Submission failed")
            st.text(traceback.format_exc())
