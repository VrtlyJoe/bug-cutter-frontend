import streamlit as st
import streamlit.components.v1 as components
import requests, traceback

# ── CONFIG & TOKEN CAPTURE ─────────────────────────────
st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")
query = st.query_params.to_dict()
if "access_token" in query:
    st.session_state["access_token"] = query["access_token"]
    components.html("<script>history.replaceState(null,null,window.location.pathname)</script>", height=0)

# ── LANDING PAGE ───────────────────────────────────────
if "access_token" not in st.session_state:
    st.title("🐞 Vrtly Bug Cutter")
    st.markdown("**Welcome!**  \n[🔑 Log in with Jira »](https://bug-cutter-backend.onrender.com/auth/start)", unsafe_allow_html=True)
    st.stop()

token = st.session_state["access_token"]
st.markdown("✅ **Logged in via Jira**")

# ── FETCH OPTIONS ─────────────────────────────────────-
BUG_CATEGORIES = ["Web UI", "App", "Back End", "Admin", "Other"]
STD_PRIORITIES = ["Lowest", "Low", "Medium", "High", "Highest"]

try:
    r = requests.get("https://bug-cutter-backend.onrender.com/options", params={"token": token}, timeout=5)
    r.raise_for_status()
    data_opts = r.json()
    priorities = data_opts.get("priorities") or STD_PRIORITIES
    components_opts = data_opts.get("components") or []
except Exception:
    priorities = STD_PRIORITIES
    components_opts = []

# ── ASSIGNEE SEARCH CACHE ─────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def search_assignees(text: str):
    if len(text) < 3:
        return []
    try:
        r = requests.get(
            "https://bug-cutter-backend.onrender.com/search_users",
            params={"q": text, "token": token},
            timeout=5,
        )
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

    assignee_query = st.text_input("Search assignee (≥3 chars)")
    assignees = search_assignees(assignee_query) if assignee_query else []
    assignee_disp = st.selectbox("Select assignee", ["-- none --"] + [u["displayName"] for u in assignees])
    assignee_id = next((u["accountId"] for u in assignees if u["displayName"] == assignee_disp), "") if assignee_disp != "-- none --" else ""

    subtasks = st.text_area("Optional Subtasks (one per line)")
    image    = st.file_uploader("Optional Screenshot", type=["png", "jpg", "jpeg"])
    confirm  = st.checkbox("Confirm and submit")
    submitted = st.form_submit_button("✂️ Cut Bug")

# ── SUBMIT ─────────────────────────────────────────────
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
