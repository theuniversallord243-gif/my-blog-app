import subprocess
import sys
import time
import threading
import webbrowser
from pyngrok import ngrok
import qrcode
from io import BytesIO

def install_packages():
    packages = ['pyngrok', 'qrcode[pil]']
    for package in packages:
        try:
            if package == 'pyngrok':
                import pyngrok
            elif package == 'qrcode[pil]':
                import qrcode
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"{package} installed successfully!")

def generate_qr_code(url):
    """Generate QR code for mobile access"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=2,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Generate ASCII QR code for terminal
        qr_ascii = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr_ascii.add_data(url)
        qr_ascii.make(fit=True)
        
        # Print QR code in terminal
        qr_ascii.print_ascii(invert=True)
        return True
    except Exception as e:
        print(f"QR code generation failed: {e}")
        return False

def run_flask_app():
    """Run the Flask app in a separate thread"""
    import app
    app.app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)

def main():
    # Install required packages
    install_packages()
    
    print("🚀 Starting Blog App with Public Access...")
    
    # Start Flask app in background thread
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Wait for Flask to start
    time.sleep(3)
    
    try:
        # Create ngrok tunnel
        public_url = ngrok.connect(5000)
        
        print("\n" + "="*60)
        print("🎉 BLOG APP IS NOW LIVE!")
        print("="*60)
        print(f"📱 Public URL: {public_url}")
        print(f"🌐 Anyone can access: {public_url}")
        print("="*60)
        print("📋 Share this link with anyone to access your blog!")
        print("📱 For MOBILE: Scan QR code below with phone camera")
        print("⚠️  Keep this terminal open to maintain the connection")
        print("🛑 Press Ctrl+C to stop")
        print("="*60)
        
        # Generate QR code for mobile access
        print("\n📱 QR CODE FOR MOBILE ACCESS:")
        print("-" * 40)
        if generate_qr_code(str(public_url)):
            print("-" * 40)
            print("📷 Scan this QR code with your phone camera!")
            print("🚀 Works on iPhone, Android, any phone!")
        else:
            print("⚠️ QR code generation failed, use URL directly")
        
        # Auto-open in Chrome
        print("\n🚀 Opening in Chrome...")
        try:
            # Multiple Chrome paths to try
            chrome_paths = [
                'C:/Program Files/Google/Chrome/Application/chrome.exe %s',
                'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s',
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome %s',
                'google-chrome %s',
                'chromium %s'
            ]
            
            opened = False
            for chrome_path in chrome_paths:
                try:
                    webbrowser.get(chrome_path).open(str(public_url))
                    opened = True
                    break
                except:
                    continue
            
            if not opened:
                # Fallback to default browser
                webbrowser.open(str(public_url))
                print("⚠️ Chrome not found, opened in default browser")
            
        except Exception as e:
            print(f"⚠️ Browser opening failed: {e}")
            print("📋 Please copy and paste the URL manually")
        
        print("✅ Browser opened with your blog app!")
        print("\n📱 MOBILE USERS: Just scan the QR code above!")
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            ngrok.disconnect(public_url)
            ngrok.kill()
            
    except Exception as e:
        print(f"❌ Error creating public tunnel: {e}")
        print("💡 Try running: pip install pyngrok qrcode[pil]")
        print("💡 Or check your internet connection")
        print("💡 Make sure you have internet access for ngrok")

if __name__ == "__main__":
    main()