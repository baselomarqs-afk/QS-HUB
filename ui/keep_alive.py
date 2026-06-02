import streamlit.components.v1 as components

def inject_keep_alive():
    """
    Injects a hidden JS iframe that pings the window every 45 seconds.
    This prevents Render/Streamlit WebSockets from timing out when the user is idle.
    """
    components.html(
        """
        <script>
        // Send a message to the parent window every 45 seconds to keep the websocket alive
        setInterval(function() {
            window.parent.postMessage({type: 'streamlit:keep-alive'}, '*');
            console.log("Keep-alive ping sent");
        }, 45000);
        </script>
        """,
        height=0,
        width=0,
    )
