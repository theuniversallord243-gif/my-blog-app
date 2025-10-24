import subprocess
import sys
import webbrowser
import time
import threading
import json
import requests

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
    
    # Try localtunnel (no auth required)
    try:
        print("Creating public tunnel...")
        
        # Install localtunnel if not installed
        try:
            subprocess.run(["npx", "--version"], check=True, capture_output=True)
        except:
            print("Installing Node.js tools...")
            
        # Create tunnel
        process = subprocess.Popen(
            ["npx", "localtunnel", "--port", "5000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for URL
        time.sleep(5)
        
        # Try to get the URL from output
        try:
            output = process.stdout.readline()
            if "https://" in output:
                public_url = output.strip().split()[-1]
                
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
                    process.terminate()
            else:
                raise Exception("Could not get public URL")
                
        except Exception as e:
            print(f"Localtunnel error: {e}")
            print("\nAlternative: Use local network access")
            print("Your blog is running on:")
            print("http://localhost:5000")
            print("Share your local IP for network access")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping...")
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nFallback: Local server running")
        print("Access at: http://localhost:5000")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")

if __name__ == "__main__":
    main()