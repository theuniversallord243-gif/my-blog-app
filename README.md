# Blog App - Complete Social Media Platform

A full-featured blog application with social media features built with Flask.

## Features

### 🔐 Authentication & Security
- User registration with security questions
- Secure password reset system
- Input sanitization and validation
- Session management

### 📝 Blog Management
- Create, edit, delete blogs
- Image upload support (PNG, JPG, JPEG, GIF, WEBP)
- Rich content with HTML support
- Search functionality

### 👥 Social Features
- Follow/Unfollow users
- Like/Unlike posts
- Comment system
- Real-time notifications
- User profiles with bio

### 📱 Mobile Friendly
- Responsive design
- Touch-friendly interface
- QR code access
- Mobile optimized UI

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the App
```bash
# Simple local version
python start_simple.py

# Or use batch file
start_simple.bat
```

### 3. Access
- **Computer:** http://localhost:5000
- **Mobile (same WiFi):** http://YOUR_IP:5000

## File Structure
```
blog_app/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── start_simple.py       # Simple local server
├── start_simple.bat      # Windows batch file
├── templates/            # HTML templates
├── static/              # CSS, JS, images
└── README.md            # This file
```

## Technologies Used
- **Backend:** Flask, SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Features:** File upload, Session management, Real-time notifications

## Security Features
- Password hashing with Werkzeug
- Input sanitization
- File type validation
- Secure session cookies
- CSRF protection

## Database Schema
- Users (with security questions)
- Blogs (with image support)
- Comments, Likes, Follows
- Notifications system

## Contributing
1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## License
Open source - feel free to use and modify!

---
**Made with ❤️ using Flask**