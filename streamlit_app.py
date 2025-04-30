import streamlit as st
import requests
import streamlit.runtime.scriptrunner.script_run_context as script_context

st.set_page_config(page_title="Vrtly Bug Template")

# ✅ Extract token from URL fragment
def parse_fragment_token():
    ctx = script_context.get_script_run_ctx()
    if not ctx or not ctx.query_string:
        return None
    fragment = ctx.query_string  # e.g., token=abc123
    if fragment.startswith("token="):
        return fragment.split("=", 1)[1]
    return None

token_from_url = parse_fragment_token()

if token_from_url:
    st.session_state["token"] = token_from_url

token = st.session_state.get("token")

if not token:
    st.info("🔐 Waiting for authentication...")
    st.stop()

# Config
BACKEND_URL = "https://bug-cutter-backend.onrender.com"

st.title("Vrtly Bug Template")
st.caption("File bugs with all the bells and whistles: Slack, autocomplete, and screenshots.")

st.markdown(f"🔐 Logged in with token ending in `{token[-6:]}`")

# Form
with st.form("bug_form"):
    summary = st.text_input("📝 Summary", help="Required")
    description = st.text_area("🗒 Description", value="Org Name:\nOrg ID:\nIssue:\nExpected Behavior:")

    options = requests.get(f"{BACKEND_URL}/options", params={"token": token}).json()
    priorities = options.get("priorities", [])
    categories = options.get("categories", [])

    priority = st.selectbox("🔥 Priority", priorities or ["Highest", "Medium", "Lowest"])

    if categories:
        category = st.selectbox("📁 Bug Category", categories)
    else:
        st.warning("⚠️ No categories from Jira. Using fallback input.")
        category = st.text_input("📁 Bug Category (manual)")

    assignee = st.text_input("👤 Assignee (type to search)")
    components = st.multiselect(
        "🏷 Components",
        options=requests.get(f"{BACKEND_URL}/autocomplete/components", params={"token": token}).json()
    )
    subtasks = st.text_area("📌 Subtasks (one per line)")
    uploaded_files = st.file_uploader("📎 Attach files", accept_multiple_files=True)

    confirm = st.checkbox("I confirm this bug is ready to be submitted.")
    submit = st.form_submit_button("Cut Bug")

    if submit:
        if not confirm:
            st.error("Please confirm the bug is ready.")
            st.stop()
        if not summary or not description:
            st.error("Summary and description are required.")
            st.stop()

        with st.spinner("🪓 Cutting bug..."):
            files = [("files", (f.name, f.getvalue())) for f in uploaded_files] if uploaded_files else []
            response = requests.post(
                f"{BACKEND_URL}/submit_bug/",
                data={
                    "summary": summary,
                    "description": description,
                    "priority": priority,
                    "category": category,
                    "assignee": assignee,
                    "components": ",".join(components),
                    "subtasks": subtasks,
                    "token": token
                },
                files=files
            )

        if response.status_code == 200:
            st.success(f"✅ Bug created: {response.json()['issue_key']}")
        elif response.status_code == 409:
            st.warning(f"⚠️ Duplicate bug detected: {response.json().get('message')}")
        else:
            st.error(f"❌ Failed to create bug: {response.text}")

st.markdown("Built with HEART by the Bug Cutter team.")
