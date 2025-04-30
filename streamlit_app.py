import streamlit as st
import requests

st.set_page_config(page_title="Vrtly Bug Template", layout="centered")

BACKEND_URL = "https://bug-cutter-backend.onrender.com"
query_params = st.query_params

if "access_token" not in st.session_state and "access_token" in query_params:
    st.session_state["access_token"] = query_params["access_token"]

st.title("Vrtly Bug Template")
st.markdown("File bugs with all the bells and whistles: Slack, autocomplete, screenshots.")

priority_options = ["Medium"]
category_options = []
component_options = []

if "access_token" not in st.session_state:
    st.markdown(f"[🔗 Click here to connect Jira]({BACKEND_URL}/auth/start)")
else:
    access_token = st.session_state["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        cloud_resp = requests.get("https://api.atlassian.com/oauth/token/accessible-resources", headers=headers)
        cloud_resp.raise_for_status()
        cloud_id = cloud_resp.json()[0]["id"]

        me_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself"
        me_resp = requests.get(me_url, headers=headers)
        me_resp.raise_for_status()
        email = me_resp.json().get("emailAddress", "Unknown user")
        st.success(f"🔐 Logged in as {email}")

        opt_resp = requests.get(f"{BACKEND_URL}/options", params={"token": access_token})
        if opt_resp.ok:
            opt_data = opt_resp.json()
            priority_options = opt_data.get("priorities", priority_options)
            category_options = opt_data.get("categories", category_options)

        comp_resp = requests.get(f"{BACKEND_URL}/autocomplete/components", params={"token": access_token})
        if comp_resp.ok:
            component_options = comp_resp.json().get("results", [])

        st.subheader("🪓 Submit a Bug")

        with st.form("bug_submit_form", clear_on_submit=False):
            summary = st.text_input("📝 Summary", placeholder="Required")
            default_desc = "Org Name: \nOrg ID: \nIssue: \nExpected Behavior:"
            description = st.text_area("🗒 Description", value=default_desc, height=150)

            priority = st.selectbox("🔥 Priority", priority_options)

            if category_options:
                category = st.selectbox("📁 Bug Category", category_options)
            else:
                st.warning("⚠️ No categories from Jira. Using fallback input.")
                category = st.text_input("📁 Bug Category")

            assignee_query = st.text_input("👤 Search Assignee")
            assignee = ""
            if assignee_query:
                a_resp = requests.get(f"{BACKEND_URL}/autocomplete/assignees", params={
                    "token": access_token,
                    "q": assignee_query
                })
                results = a_resp.json().get("results", []) if a_resp.ok else []
                assignee_options = [
                    m.get("name") or m.get("displayName") for m in results
                    if m.get("name") or m.get("displayName")
                ]
                if assignee_options:
                    assignee = st.selectbox("🔎 Select Assignee", assignee_options)

            selected_components = st.multiselect("🏷 Components", options=component_options)
            components = ", ".join(selected_components)

            subtasks = st.text_area("📌 Subtasks (one per line)", height=100)
            uploaded_files = st.file_uploader("📎 Attach files", accept_multiple_files=True)

            if uploaded_files:
                for f in uploaded_files:
                    if f.type.startswith("image/"):
                        st.image(f, caption=f.name, use_container_width=True)

            confirm = st.checkbox("✅ I confirm this is a real bug and not a test or duplicate.")
            submit = st.form_submit_button("🚀 Cut Bug")

        if submit:
            if not confirm:
                st.error("Please confirm before cutting a bug.")
            elif not summary.strip():
                st.error("Summary is required.")
            elif not description.strip() or description == default_desc:
                st.error("Please fill in the description.")
            else:
                with st.spinner("Creating bug..."):
                    files = [("files", (f.name, f.read())) for f in uploaded_files] if uploaded_files else []
                    payload = {
                        "summary": summary,
                        "description": description,
                        "priority": priority,
                        "category": category,
                        "assignee": assignee,
                        "components": components,
                        "subtasks": subtasks,
                        "token": access_token,
                    }
                    try:
                        response = requests.post(f"{BACKEND_URL}/submit_bug/", data=payload, files=files or None)
                        if response.status_code == 200:
                            st.success(f"✅ Bug created: {response.json().get('issue_key')}")
                        elif response.status_code == 409:
                            st.warning(f"⚠️ Duplicate bug: {response.json().get('message')}")
                        else:
                            st.error(f"❌ Error: {response.status_code}")
                            st.text(response.text)
                    except Exception as e:
                        st.error(f"Request failed: {e}")

    except Exception as e:
        st.error("⚠️ Login succeeded, but Jira API failed.")
        st.text(str(e))

st.markdown("---")
st.caption("Built with ❤️ by the Bug Cutter team.")
