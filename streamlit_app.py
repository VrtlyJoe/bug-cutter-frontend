import streamlit as st
import streamlit.components.v1 as components
import requests, traceback

# ── CONFIG ──────────────────────────────────────────────
st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── CAPTURE ACCESS TOKEN ───────────────────────────────
query = st.query_params.to_dict()
if "access_token" in query:
    st.session_state["access_token"] = query["access_token"]
    components.html(
        "<script>history.replaceState(null,null,window.location.pathname)</script>",
        height=0,
    )

# ── LANDING PAGE (not logged in) ───────────────────────
if "access_token" not in st.session_state:
    st.title("🐞 Vrtly Bug Cutter")
    st.markdown(
        """
        **Welcome!**  
        [🔑 Log in with Jira »](https://bug-cutter-backend.onrender.com/auth/start)
        """,
        unsafe_allow_html=True,
    )
    st.stop()

token = st.session_state["access_token"]
st.markdown("✅ **Logged in via Jira**")

# ── FETCH OPTIONS (priorities, components) ─────────────
STD_PRI = ["Lowest", "Low", "Medium", "High", "Highest"]
BUG_CATEGORIES = ["Web UI", "App", "Back End", "Admin", "Other"]
try:
    r = requests.get("https://bug-cutter-backend.onrender.com/options", params={"token": token}, timeout=5)
    r.raise_for_status()
    opts = r.json()
    priorities = opts.get("priorities", []) or STD_PRI
    components_opts = opts.get("components", [])
except Exception:
    priorities = STD_PRI
    components_opts = []

# ── ASSIGNEE SEARCH HELPER ─────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def search_assignees(text):
    if len(text) < 3:
        return []
    try:
        r = requests.get("https://bug-cutter-backend.onrender.com/search_users",
                         params={"q": text, "token": token}, timeout=5)
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        return []

# ── FORM ───────────────────────────────────────────────
st.title("🐞 Vrtly Bug Cutter")
with st.form("bug_form"):
    col1, col2 = st.columns(2)
    with col1:
        summary = st.text_input("Summary", max_chars=150)
        priority = st.selectbox("Priority", priorities, index=priorities.index("Medium") if "Medium" in priorities else 0)
        bug_cat  = st.selectbox("Bug Category", BUG_CATEGORIES)
        component = st.selectbox("Jira Component", ["-- none --"] + components_opts)
    with col2:
        default_desc = (
            "**Org Name:**\n\n"
            "**Org ID:**\n\n"
            "**Issue:**\n\n"
            "**Expected Behavior:**\n"
        )
        description = st.text_area("Description (use template)", value=default_desc, height=220)

    # assignee live search
    assignee_query = st.text_input("Search assignee (≥3 chars)")
    candidates = search_assignees(assignee_query) if assignee_query else []
    assignee_disp = st.selectbox("Select assignee", ["-- none --"] + [u["displayName"] for u in candidates])
    assignee_id = next((u["accountId"] for u in candidates if u["displayName"] == assignee_disp), "") if assignee_disp != "-- none --" else ""

    subtasks = st.text_area("Optional Subtasks (one per line)")
    image    = st.file_uploader("Optional Screenshot", type=["png", "jpg", "jpeg"])
    confirm  = st.checkbox("Confirm and submit")
    submitted = st.form_submit_button("✂️ Cut Bug")

if submitted:
    if not confirm:
        st.error("Please confirm before submitting.")
    elif not summary or not description.strip():
        st.error("Summary and Description are required.")
    else:
        with st.spinner("Submitting bug…"):
            files = {"files": image} if image else None
            payload = {
                "summary": summary,
                "description": description,
                "priority": priority,
                "category": bug_cat,
                "assignee": assignee_id,
                "components": "" if component == "-- none --" else component,
                "subtasks": subtasks,
                "token": token,
            }
            try:
                r = requests.post("https://bug-cutter-backend.onrender.com/submit_bug/", data=payload, files=files)
                r.raise_for_status()
                key = r.json()["issue_key"]
                st.success(f"✅ Created! [{key}](https://vrtlyai.atlassian.net/browse/{key})")
            except Exception:
                st.error("❌ Submission failed."); st.text(traceback.format_exc())
