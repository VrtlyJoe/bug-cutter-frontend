import streamlit as st, streamlit.components.v1 as components
import requests, traceback
from PIL import Image

st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── capture access_token ────────────────────────────────
q = st.query_params.to_dict()
if "access_token" in q:
    st.session_state["access_token"] = q["access_token"]
    components.html("<script>history.replaceState(null,null,location.pathname)</script>", height=0)

if "access_token" not in st.session_state:
    st.title("🐞 Vrtly Bug Cutter")
    st.markdown("[🔑 Log in with Jira »](https://bug-cutter-backend.onrender.com/auth/start)", unsafe_allow_html=True)
    st.stop()

token = st.session_state["access_token"]

# ── reporter banner ────────────────────────────────────
try:
    reporter_email = requests.get("https://bug-cutter-backend.onrender.com/me",
                                  params={"token": token}, timeout=5).json().get("email","")
except Exception: reporter_email = ""
st.markdown(f"✅ **Logged in as {reporter_email or '(unknown)'}**", unsafe_allow_html=True)

# ── dropdown data ──────────────────────────────────────
BUG_CATS = ["Web UI","App","Back End","Admin","Other"]; STD_PRI = ["Lowest","Low","Medium","High","Highest"]
try:
    opts = requests.get("https://bug-cutter-backend.onrender.com/options",
                        params={"token": token}, timeout=5).json()
    priorities, components_opts = opts.get("priorities") or STD_PRI, opts.get("components") or []
except Exception:
    priorities, components_opts = STD_PRI, []

# ── assignee search ────────────────────────────────────
@st.cache_data(ttl=60)
def find_users(q:str):
    if len(q)<3: return []
    try:
        r = requests.get("https://bug-cutter-backend.onrender.com/search_users",
                         params={"q":q,"token":token}, timeout=5)
        return r.json().get("results",[])
    except Exception: return []

st.subheader("Assignee Search")
search_txt   = st.text_input("Type ≥3 chars & press ↵")
assignees    = find_users(search_txt) if len(search_txt)>=3 else []
assignee_disp= st.selectbox("Choose assignee",
                            ["-- none --"]+[u["displayName"] for u in assignees])
assignee_id  = (next((u["accountId"] for u in assignees if u["displayName"]==assignee_disp),"")
                if assignee_disp!="-- none --" else "")

st.divider()

# ── screenshot uploader (outside form → instant preview) ─
image_file = st.file_uploader("Optional Screenshot", type=["png","jpg","jpeg"], key="screenshot")
if image_file:
    img = Image.open(image_file)
    w,h = img.size
    st.info(f"Preview: {w}×{h}px")
    max_w = 300
    show_w = min(w, max_w)
    st.image(img, width=show_w)

st.divider()

# ── bug form ───────────────────────────────────────────
st.title("🐞 Create Bug")
with st.form("bug_form"):
    c1,c2 = st.columns(2)
    with c1:
        summary   = st.text_input("Summary", max_chars=150)
        priority  = st.selectbox("Priority", priorities,
                                 index=priorities.index("Medium") if "Medium" in priorities else 0)
        category  = st.selectbox("Bug Category", BUG_CATS)
        component = st.selectbox("Jira Component", ["-- none --"]+components_opts)
    with c2:
        default_desc = "Org Name:\nOrg ID:\nIssue:\nExpected Behavior:\n"
        description  = st.text_area("Description (fill sections):", value=default_desc, height=220)

    subtasks = st.text_area("Optional Subtasks (one per line)")
    confirm  = st.checkbox("Confirm and submit")
    submit   = st.form_submit_button("✂️ Cut Bug")

# ── submit handler ─────────────────────────────────────
if submit:
    if not confirm:
        st.error("Please confirm"); st.stop()
    if not summary or not description.strip():
        st.error("Summary & Description required"); st.stop()

    files = {"files": image_file} if image_file else None
    data  = {
        "summary":summary, "description":description,
        "priority":priority, "category":category,
        "assignee":assignee_id,
        "components":"" if component=="-- none --" else component,
        "subtasks":subtasks, "token":token,
    }

    with st.spinner("Submitting…"):
        try:
            r = requests.post("https://bug-cutter-backend.onrender.com/submit_bug/",
                              data=data, files=files); r.raise_for_status()
            key=r.json()["issue_key"]
            st.success(f"✅ Created! [{key}](https://vrtlyai.atlassian.net/browse/{key})")
        except Exception:
            st.error("❌ Submission failed"); st.text(traceback.format_exc())
