
import streamlit as st
import requests
import time  # For any polling if needed

# Shared Helper: Runtime API Base Resolution (as per your update)
def get_api_base():
    return st.session_state.get('adv19_api_base', 'http://localhost:8000')  # Fallback to DJANGO_API_URL equivalent

# Shared Helper: Safe API Call (resolves base at runtime, with error handling)
def safe_api_call(method, endpoint, payload=None, timeout=5):
    base = get_api_base()
    url = f"{base}{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"API call failed: {str(e)}")
        return None

# Shared Helper: Live Data Status Indicator
def display_live_status():
    base = get_api_base()
    try:
        test_response = requests.get(f"{base}/api/v1/feed/equity/series", timeout=3)
        if test_response.status_code == 200 and test_response.json().get('points'):
            st.success("✓ Live data flowing (equity series available)")
        else:
            st.warning("⚠️ Awaiting feed (fallback to local breadcrumb)")
    except:
        st.error("❌ API unreachable - check base override")

# Shared Helper: Render Whisper with Ack/Act Buttons
def render_whisper(whisper):
    st.markdown(f"**{whisper['ts']} - {whisper['severity']}:** {whisper['message']}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ack", key=f"ack_{whisper['id']}_{time.time()}"):  # Unique key to avoid re-run issues
            payload = {"id": whisper['id'], "reason": "Acknowledged"}
            result = safe_api_call('POST', '/api/pulse/whisper/ack', payload)
            if result:
                st.toast("Whisper acknowledged! 🎉")
    with col2:
        action = st.selectbox("Action", ["Reduce Size", "Close Position", "Review Rules"], key=f"act_select_{whisper['id']}")
        if st.button("Act", key=f"act_{whisper['id']}_{time.time()}"):
            payload = {"id": whisper['id'], "action": action}
            result = safe_api_call('POST', '/api/pulse/whisper/act', payload)
            if result:
                st.toast(f"Action '{action}' applied! ⚡")
                # Optional: Refresh equity trajectory or whispers here

# --- Page 06: The Whisperer (Full Dashboard) Updates ---
# Insert after existing whisper fetching logic (e.g., whispers = safe_api_call('GET', '/api/v1/feed/whispers'))
st.header("The Whisperer - Live Feed")
display_live_status()  # Add status at top

# Assuming 'whispers' is fetched; loop and render with buttons
for whisper in whispers:
    render_whisper(whisper)

# Equity Trajectory (already live per your update)
st.subheader("Live Equity Trajectory")
equity_data = safe_api_call('GET', '/api/v1/feed/equity/series')
if equity_data and equity_data['points']:
    # Render chart (e.g., using st.line_chart or Altair)
    st.line_chart(equity_data['points'])  # Simplified; expand as needed
else:
    st.info("Fallback to local breadcrumb - no closed trades yet.")

# --- Page 04: Light Dashboard Updates ---
# Insert after existing placeholders/trajectory
st.header("Light Dashboard - Essentials")
display_live_status()  # Add status at top

# Whisper section (lighter: show last 3)
st.subheader("Recent Whispers")
whispers = safe_api_call('GET', '/api/v1/feed/whispers?limit=3')
if whispers:
    for whisper in whispers:
        render_whisper(whisper)
else:
    st.info("Awaiting whispers...")

# Equity Trajectory
st.subheader("Equity Trajectory")
equity_data = safe_api_call('GET', '/api/v1/feed/equity/series')
if equity_data and equity_data['points']:
    st.line_chart(equity_data['points'])
else:
    st.info("Awaiting feed - produce/close a trade to populate.")

# Optional: Add a refresh button for manual polling
if st.button("Refresh Data"):
    st.rerun()
