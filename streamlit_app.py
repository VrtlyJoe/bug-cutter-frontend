import streamlit as st
import requests

st.set_page_config(page_title="Vrtly Bug Template", layout="centered")

BACKEND_URL = "https://bug-cutter-backend.onrender.com"
query_params = st.query_params

if "access_token" not in st.session_state and "access_token" in query_params:
    st.session_state["access_token"] = query_params["access_token"]

st.title("Vrtly Bug Template")
st.markdown("Quick test: Just send summary, description, and optional priority.")

priority_options = ["Medium", "High", "Highest", "Low"]

if "access_token" not in st.session_state:
    st.markdown(f"[🔗 Click here to connect Jira]({BACKEND_URL}/auth/start)")
else:
    access_token = st.session_state["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        # Get Jira user for confirmation
        cloud_resp = requests.get("https://api.atlassian.com/oauth/token/accessible-resources", headers=headers)
        cloud_resp.raise_for_status()
        cloud_id = cloud_resp.json()[0]["id"]

        me_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself"
        me_resp = requests.get(me_url, headers=headers)
        me_resp.raise_for_status()
        email = me_resp.json().get("emailAddress", "Unknown user")
        st.success(f"🔐 Logged in as {email}")

        # Minimal bug form
        st.subheader("🚨 Minimal Bug Submit")

        with st.form("basic_bug_form"):
            summary = st.text_input("📝 Summary")
            description = st.text_area("🗒 Description")
            priority = st.selectbox("🔥 Priority", priority_options)
            submit = st.form_submit_button("🚀 Submit Bug")

        if submit:
            with st.spinner("Creating bug..."):
                payload = {
                    "summary": summary,
                    "description": description,
                    "priority": priority,
                    "token": access_token,
                }
                try:
                    response = requests.post(f"{BACKEND_URL}/submit_bug/", data=payload)
                    if response.status_code == 200:
                        st.success(f"✅ Bug created: {response.json().get('issue_key')}")
                    else:
                        st.error(f"❌ Error: {response.status_code}")
                        st.text(response.text)
                except Exception as e:
                    st.error(f"Request failed: {e}")

    except Exception as e:
        st.error("⚠️ Login succeeded, but Jira call failed.")
        st.text(str(e))

st.markdown("---")
st.caption("🧪 Minimal test mode — bug creation only.")
