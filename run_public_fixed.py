import subprocess
import sys
import time
import threading
import webbrowser
from pyngrok import ngrok
import qrcode
from io import BytesIO

def install_packages():
    packages = ['pyngrok', 'qrcode[pil]', 'requests']
    for package in packages:
        try:
            if package == 'pyngrok':
                import pyngrok
            elif package == 'qrcode[pil]':
                import qrcode
            elif package == 'requests':
                import requests
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

def check_flask_running():
    """Check if Flask app is running"""
    try:
        import requests
        response = requests.get('http://localhost:5000', timeout=2)
        return True
    except:
        return False

def main():
    # Install required packages
    install_packages()
    
    print("🚀 Starting Blog App with Public Access...")
    print("🔄 Auto-reconnect enabled - tunnel will restart if disconnected")
    
    # Start Flask app in background thread
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Wait for Flask to start
    print("⏳ Starting Flask app...")
    for i in range(10):
        if check_flask_running():
            print("✅ Flask app is running!")
            break
        time.sleep(1)
        print(f"Waiting... {i+1}/10")
    else:
        print("❌ Flask app failed to start")
        return
    
    public_url = None
    tunnel_active = False
    first_time = True
    
    try:
        while True:
            try:
                if not tunnel_active:
                    print("\n🔗 Creating ngrok tunnel...")
                    # Kill any existing ngrok processes
                    try:
                        ngrok.kill()
                    except:
                        pass
                    
                    # Create new tunnel
                    public_url = ngrok.connect(5000)
                    tunnel_active = True
                    
                    print("\n" + "="*60)
                    print("🎉 BLOG APP IS NOW LIVE!")
                    print("="*60)
                    print(f"📱 Public URL: {public_url}")
                    print(f"🌐 Anyone can access: {public_url}")
                    print("="*60)
                    print("📋 Share this link with anyone!")
                    print("📱 For MOBILE: Scan QR code below")
                    print("🔄 Auto-reconnect: ON")
                    print("🛑 Press Ctrl+C to stop")
                    print("="*60)
                    
                    # Generate QR code
                    print("\n📱 QR CODE FOR MOBILE:")
                    print("-" * 40)
                    if generate_qr_code(str(public_url)):
                        print("-" * 40)
                        print("📷 Scan with phone camera!")
                    
                    # Auto-open in Chrome (only first time)
                    if first_time:
                        print("\n🚀 Opening in Chrome...")
                        try:
                            chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
                            webbrowser.get(chrome_path).open(str(public_url))
                        except:
                            webbrowser.open(str(public_url))
                        print("✅ Chrome opened!")
                        first_time = False
                
                # Check tunnel status every 5 seconds
                time.sleep(5)
                
                # Test if tunnel is still active
                try:
                    import requests
                    response = requests.get(str(public_url), timeout=5)
                    if response.status_code != 200:
                        raise Exception("Tunnel not responding")
                except:
                    print("⚠️ Tunnel disconnected, reconnecting...")
                    tunnel_active = False
                    continue
                    
            except KeyboardInterrupt:
                print("\n🛑 Shutting down...")
                try:
                    if public_url:
                        ngrok.disconnect(public_url)
                    ngrok.kill()
                except:
                    pass
                break
                
            except Exception as e:
                print(f"❌ Tunnel error: {e}")
                print("🔄 Retrying in 5 seconds...")
                tunnel_active = False
                time.sleep(5)
                
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print("💡 Solutions:")
        print("  1. Check internet connection")
        print("  2. Run: pip install pyngrok qrcode[pil] requests")
        print("  3. Try restarting the script")

if __name__ == "__main__":
    main()