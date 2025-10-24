import subprocess
import sys
import webbrowser
import socket
import time
import threading

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def run_flask_app():
    """Run Flask app"""
    import app
    app.app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)

def main():
    print("🚀 Starting Blog App...")
    
    # Get local IP
    local_ip = get_local_ip()
    
    # Start Flask in background
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Wait for Flask to start
    time.sleep(3)
    
    print("\n" + "="*50)
    print("🎉 BLOG APP IS RUNNING!")
    print("="*50)
    print(f"🖥️  Computer: http://localhost:5000")
    print(f"📱 Mobile/Others: http://{local_ip}:5000")
    print("="*50)
    print("📋 Mobile access ke liye:")
    print("   1. Same WiFi network pe hona chahiye")
    print("   2. Windows Firewall allow karna pad sakta hai")
    print("🛑 Press Ctrl+C to stop")
    print("="*50)
    
    # Open in browser
    webbrowser.open("http://localhost:5000")
    print("✅ Opened in browser!")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")

if __name__ == "__main__":
    main()