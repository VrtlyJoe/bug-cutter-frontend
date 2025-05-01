import streamlit as st, streamlit.components.v1 as components
import requests, traceback

st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── token capture ───────────────────────────────────────
q = st.query_params.to_dict()
if "access_token" in q:
    st.session_state["access_token"] = q["access_token"]
    components.html("<script>history.replaceState(null,null,location.pathname)</script>", height=0)

if "access_token" not in st.session_state:
    st.title("🐞 Vrtly Bug Cutter")
    st.markdown("[🔑 Log in with Jira »](https://bug-cutter-backend.onrender.com/auth/start)", unsafe_allow_html=True)
    st.stop()

token = st.session_state["access_token"]

# fetch email for banner
try:
    reporter_email = requests.get("https://bug-cutter-backend.onrender.com/me", params={"token": token}, timeout=5).json().get("email","")
except Exception:
    reporter_email = ""

st.markdown(f"✅ **Logged in as {reporter_email or '(unknown)'}**", unsafe_allow_html=True)

# options
BUG_CATS = ["Web UI","App","Back End","Admin","Other"]; STD_PRI = ["Lowest","Low","Medium","High","Highest"]
try:
    opts = requests.get("https://bug-cutter-backend.onrender.com/options", params={"token": token}, timeout=5).json()
    priorities = opts.get("priorities") or STD_PRI
    components_opts = opts.get("components") or []
except Exception:
    priorities, components_opts = STD_PRI, []

@st.cache_data(ttl=60)
def search_users(txt):
    if len(txt)<3: return []
    try:
        r = requests.get("https://bug-cutter-backend.onrender.com/search_users", params={"q":txt,"token":token}, timeout=5)
        return r.json().get("results",[])
    except Exception: return []

# form
st.title("🐞 Vrtly Bug Cutter")
with st.form("bug"):
    c1,c2 = st.columns(2)
    with c1:
        summary  = st.text_input("Summary", max_chars=150)
        priority = st.selectbox("Priority", priorities, index=priorities.index("Medium") if "Medium" in priorities else 0)
        category = st.selectbox("Bug Category", BUG_CATS)
        component= st.selectbox("Jira Component", ["-- none --"]+components_opts)
    with c2:
        default = "**Org Name:**\n\n**Org ID:**\n\n**Issue:**\n\n**Expected Behavior:**\n"
        description = st.text_area("Description (template provided):", value=default, height=220)

    qname = st.text_input("Search assignee (≥3 chars)")
    userlist = search_users(qname) if qname else []
    ass_display = st.selectbox("Select assignee", ["-- none --"]+[u["displayName"] for u in userlist])
    ass_id = next((u["accountId"] for u in userlist if u["displayName"]==ass_display),"") if ass_display!="-- none --" else ""

    image = st.file_uploader("Optional Screenshot", type=["png","jpg","jpeg"])
    if image: st.image(image, caption="Preview", use_container_width=True)

    subtasks = st.text_area("Optional Subtasks (one per line)")
    confirm  = st.checkbox("Confirm and submit")
    submitted = st.form_submit_button("✂️ Cut Bug")

if submitted:
    if not confirm:
        st.error("Confirm before submitting"); st.stop()
    if not summary or not description.strip():
        st.error("Summary and Description required"); st.stop()

    with st.spinner("Submitting…"):
        files = {"files": image} if image else None
        payload = {
            "summary":summary, "description":description, "priority":priority,
            "category":category, "assignee":ass_id,
            "components":"" if component=="-- none --" else component,
            "subtasks":subtasks, "token":token,
        }
        try:
            r = requests.post("https://bug-cutter-backend.onrender.com/submit_bug/", data=payload, files=files)
            r.raise_for_status(); key=r.json()["issue_key"]
            st.success(f"✅ Created! [{key}](https://vrtlyai.atlassian.net/browse/{key})")
        except Exception:
            st.error("❌ Submit failed"); st.text(traceback.format_exc())
