import streamlit as st, streamlit.components.v1 as components
import requests, traceback

st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── TOKEN CAPTURE ───────────────────────────────────────
q = st.query_params.to_dict()
if "access_token" in q:
    st.session_state["access_token"] = q["access_token"]
    components.html("<script>history.replaceState(null,null,location.pathname)</script>", height=0)

# ── LANDING PAGE ───────────────────────────────────────
if "access_token" not in st.session_state:
    st.title("🐞 Vrtly Bug Cutter")
    st.markdown("[🔑 Log in with Jira »](https://bug-cutter-backend.onrender.com/auth/start)", unsafe_allow_html=True)
    st.stop()

token = st.session_state["access_token"]

# fetch Jira email for banner
try:
    reporter_email = requests.get("https://bug-cutter-backend.onrender.com/me",
                                  params={"token": token}, timeout=5).json().get("email","")
except Exception: reporter_email = ""
st.markdown(f"✅ **Logged in as {reporter_email or '(unknown)'}**", unsafe_allow_html=True)

# ── OPTIONS ────────────────────────────────────────────
BUG_CATS = ["Web UI","App","Back End","Admin","Other"]; STD_PRI = ["Lowest","Low","Medium","High","Highest"]
try:
    opts = requests.get("https://bug-cutter-backend.onrender.com/options",
                        params={"token": token}, timeout=5).json()
    priorities      = opts.get("priorities")  or STD_PRI
    components_opts = opts.get("components") or []
except Exception:
    priorities, components_opts = STD_PRI, []

@st.cache_data(ttl=60)
def search_users(txt:str):
    if len(txt)<3: return []
    try:
        r = requests.get("https://bug-cutter-backend.onrender.com/search_users",
                         params={"q":txt,"token":token}, timeout=5)
        return r.json().get("results",[])
    except Exception: return []

# ── FORM ───────────────────────────────────────────────
st.title("🐞 Vrtly Bug Cutter")
with st.form("bug"):
    c1,c2 = st.columns(2)
    with c1:
        summary  = st.text_input("Summary", max_chars=150)
        priority = st.selectbox("Priority", priorities,
                                index=priorities.index("Medium") if "Medium" in priorities else 0)
        category = st.selectbox("Bug Category", BUG_CATS)
        component= st.selectbox("Jira Component", ["-- none --"]+components_opts)
    with c2:
        default_desc = (
            "Org Name:\n"
            "Org ID:\n"
            "Issue:\n"
            "Expected Behavior:\n"
        )
        description = st.text_area("Description (fill the sections below):",
                                   value=default_desc, height=220)

    # assignee
    qname = st.text_input("Search assignee (≥3 chars)")
    users = search_users(qname) if qname else []
    assignee_disp = st.selectbox("Select assignee",
                                 ["-- none --"]+[u["displayName"] for u in users])
    assignee_id = next((u["accountId"] for u in users
                        if u["displayName"]==assignee_disp),"") if assignee_disp!="-- none --" else ""

    image = st.file_uploader("Optional Screenshot", type=["png","jpg","jpeg"])
    if image: st.image(image, caption="Preview", use_container_width=True)

    subtasks = st.text_area("Optional Subtasks (one per line)")
    confirm  = st.checkbox("Confirm and submit")
    submitted= st.form_submit_button("✂️ Cut Bug")

# ── SUBMIT ─────────────────────────────────────────────
if submitted:
    if not confirm: st.error("Please confirm before submitting."); st.stop()
    if not summary or not description.strip(): st.error("Summary & Description required"); st.stop()

    with st.spinner("Submitting…"):
        files = {"files": image} if image else None
        data = {
            "summary":summary, "description":description,
            "priority":priority, "category":category,
            "assignee":assignee_id,
            "components":"" if component=="-- none --" else component,
            "subtasks":subtasks, "token":token,
        }
        try:
            r = requests.post("https://bug-cutter-backend.onrender.com/submit_bug/",
                              data=data, files=files); r.raise_for_status()
            key = r.json()["issue_key"]
            st.success(f"✅ Created! [{key}](https://vrtlyai.atlassian.net/browse/{key})")
        except Exception:
            st.error("❌ Submission failed"); st.text(traceback.format_exc())
