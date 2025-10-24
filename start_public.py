import subprocess
import sys
import webbrowser
import time
import threading
from pyngrok import ngrok

def run_flask_app():
    """Run Flask app"""
    import app
    app.app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)

def main():
    print("Starting Public Blog App...")
    
    # Start Flask in background
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Wait for Flask to start
    time.sleep(3)
    
    # Create ngrok tunnel
    try:
        public_tunnel = ngrok.connect(5000)
        public_url = public_tunnel.public_url
        
        print("\n" + "="*60)
        print("BLOG IS NOW LIVE ON INTERNET!")
        print("="*60)
        print(f"Public Link: {public_url}")
        print("="*60)
        print("Share this link with anyone, anywhere!")
        print("Press Ctrl+C to stop")
        print("="*60)
        
        # Open in browser
        webbrowser.open(public_url)
        print("Opened in browser!")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            ngrok.disconnect(public_tunnel.public_url)
            
    except Exception as e:
        print(f"Error: {e}")
        print("Install ngrok: pip install pyngrok")

if __name__ == "__main__":
    main()