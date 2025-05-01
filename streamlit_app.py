import streamlit as st
import streamlit.components.v1 as components
import requests, traceback, time

# ── CONFIG ──────────────────────────────────────────────
st.set_page_config(page_title="Vrtly Bug Cutter", layout="wide")

# ── AUTH ────────────────────────────────────────────────
query = st.query_params.to_dict()
if "access_token" in query:
    st.session_state["access_token"] = query["access_token"]
    components.html(
        "<script>history.replaceState(null,null,window.location.pathname)</script>",
        height=0,
    )

if "access_token" not in st.session_state:
    st.warning("🔐 Not logged in.  [Login with Jira](https://bug-cutter-backend.onrender.com/auth/start)")
    st.stop()

token = st.session_state["access_token"]
st.markdown("✅ **Logged in via Jira**")

# ── STATIC LISTS PER SPEC ───────────────────────────────
BUG_CATEGORIES = ["Web UI", "App", "Back End", "Admin", "Other"]
STANDARD_PRIORITIES = ["Lowest", "Low", "Medium", "High", "Highest"]

# ── FETCH COMPONENTS & PRIORITIES (Jira) ────────────────
try:
    r = requests.get(
        "https://bug-cutter-backend.onrender.com/options",
        params={"token": token},
        timeout=5,
    )
    r.raise_for_status()
    opt = r.json()
    priorities  = opt.get("priorities", []) or STANDARD_PRIORITIES
    components_opts = opt.get("components", [])
except Exception:
    priorities      = STANDARD_PRIORITIES
    components_opts = []

# ── TITLE ───────────────────────────────────────────────
st.title("🐞 Vrtly Bug Cutter")

# ── ASSIGNEE SEARCH HELPER ─────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def search_assignees(query_text: str):
    if len(query_text) < 3:
        return []
    try:
        r = requests.get(
            "https://bug-cutter-backend.onrender.com/search_users",
            params={"q": query_text, "token": token},
            timeout=5,
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        return []

# ── BUG FORM ────────────────────────────────────────────
with st.form("bug_form"):
    col1, col2 = st.columns(2)
    with col1:
        summary = st.text_input("Summary", max_chars=150)
        priority = st.selectbox("Priority", priorities, index=priorities.index("Medium") if "Medium" in priorities else 0)
        bug_cat  = st.selectbox("Bug Category", BUG_CATEGORIES)
    with col2:
        description = st.text_area("Description")

    component = st.selectbox("Jira Component", ["-- none --"] + components_opts)
    
    # assignee search
    query_name = st.text_input("Search assignee (min 3 chars)")
    assignees  = search_assignees(query_name)
    assignee_display = st.selectbox(
        "Select Assignee", ["-- none --"] + [u["displayName"] for u in assignees]
    )
    assignee_id = ""
    if assignee_display != "-- none --":
        # map back to accountId
        assignee_id = next((u["accountId"] for u in assignees if u["displayName"] == assignee_display), "")

    subtasks = st.text_area("Optional Subtasks (one per line)")
    image    = st.file_uploader("Optional Screenshot", type=["png", "jpg", "jpeg"])
    confirm  = st.checkbox("Confirm and submit")
    submitted = st.form_submit_button("✂️ Cut Bug")

# ── SUBMIT BUG ──────────────────────────────────────────
if submitted:
    if not confirm:
        st.error("Please confirm before submitting.")
    elif not summary or not description:
        st.error("Summary and Description are required.")
    else:
        with st.spinner("Submitting bug…"):
            files = {"files": image} if image else None
            payload = {
                "summary":     summary,
                "description": description,
                "priority":    priority,
                "category":    bug_cat,
                "assignee":    assignee_id,
                "components":  "" if component == "-- none --" else component,
                "subtasks":    subtasks,
                "token":       token,
            }
            try:
                r = requests.post("https://bug-cutter-backend.onrender.com/submit_bug/", data=payload, files=files)
                r.raise_for_status()
                key = r.json()["issue_key"]
                st.success(f"✅ Bug created! [{key}](https://vrtlyai.atlassian.net/browse/{key})")
            except Exception:
                st.error("❌ Submission failed.")
                st.text(traceback.format_exc())

# ── DUPLICATE CHECK (optional) ──────────────────────────
if st.checkbox("Check for Similar Bugs"):
    if summary:
        try:
            r = requests.get(
                "https://bug-cutter-backend.onrender.com/search_bugs",
                params={"q": summary, "token": token},
                timeout=5,
            )
            r.raise_for_status()
            matches = r.json().get("results", [])
            if matches:
                st.warning("Similar bugs:")
                for m in matches:
                    st.markdown(f"- [{m['key']}] {m['summary']}")
            else:
                st.success("No similar bugs found.")
        except Exception:
            st.error("Error during duplicate check.")
            st.text(traceback.format_exc())
    else:
        st.info("Enter a summary first.")
