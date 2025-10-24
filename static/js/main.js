// Password toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    // Handle password toggle for login page
    const passwordToggles = document.querySelectorAll('.password-toggle');
    
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const passwordInput = this.parentElement.querySelector('input[type="password"], input[type="text"]');
            const icon = this.querySelector('i');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.className = 'fas fa-eye-slash';
            } else {
                passwordInput.type = 'password';
                icon.className = 'fas fa-eye';
            }
        });
    });
});

// Global password toggle function for register page
function togglePassword(fieldId) {
    const field = document.getElementById(fieldId);
    const toggle = field.nextElementSibling;
    const icon = toggle.querySelector('i');
    
    if (field.type === 'password') {
        field.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        field.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

// Share functionality
function toggleShare(blogId) {
    const menu = document.getElementById('shareMenu' + blogId);
    const allMenus = document.querySelectorAll('.share-menu');
    
    // Close all other menus
    allMenus.forEach(m => {
        if (m !== menu) m.style.display = 'none';
    });
    
    // Toggle current menu
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
}

// Copy to clipboard function
function copyToClipboard(text) {
    if (!text || typeof text !== 'string') {
        console.error('Invalid text for clipboard');
        return;
    }
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            alert('Link copied to clipboard!');
        }).catch(err => {
            console.error('Clipboard error:', err);
            fallbackCopy(text);
        });
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert('Link copied to clipboard!');
    } catch (err) {
        console.error('Fallback copy failed:', err);
        alert('Failed to copy link');
    }
}

// Event delegation for share buttons
document.addEventListener('click', function(e) {
    // Handle share toggle buttons
    if (e.target.closest('.share-toggle') || e.target.closest('.close-share') || e.target.closest('.share-overlay')) {
        // Check if user is logged in for share
        if (e.target.closest('.share-toggle') && !document.body.dataset.loggedIn) {
            alert('Please login to share posts!');
            window.location.href = '/login';
            return;
        }
        
        const blogId = e.target.closest('[data-blog-id]').dataset.blogId;
        toggleShare(blogId);
        return;
    }
    
    // Handle copy button
    if (e.target.closest('.copy')) {
        const url = e.target.closest('[data-url]').dataset.url;
        copyToClipboard(url);
        return;
    }
    
    // Handle like button
    if (e.target.closest('.like-btn')) {
        // Check if user is logged in
        if (!document.body.dataset.loggedIn) {
            alert('Please login to like posts!');
            window.location.href = '/login';
            return;
        }
        
        const likeBtn = e.target.closest('.like-btn');
        const blogId = likeBtn.dataset.blogId;
        const likeCount = likeBtn.querySelector('.like-count');
        const currentCount = parseInt(likeCount.textContent);
        
        if (likeBtn.classList.contains('liked')) {
            likeBtn.classList.remove('liked');
            likeCount.textContent = currentCount - 1;
        } else {
            likeBtn.classList.add('liked');
            likeCount.textContent = currentCount + 1;
        }
        return;
    }
    
    // Close share menus when clicking outside
    if (!e.target.closest('.share-dropdown') && !e.target.closest('.share-menu')) {
        document.querySelectorAll('.share-menu').forEach(menu => {
            menu.style.display = 'none';
        });
        document.querySelectorAll('.share-overlay').forEach(overlay => {
            overlay.style.display = 'none';
        });
        document.body.classList.remove('share-open');
    }
});

// Image upload functionality
document.addEventListener('DOMContentLoaded', function() {
    const imageInput = document.getElementById('images');
    const imagePreview = document.getElementById('imagePreview');
    
    if (imageInput && imagePreview) {
        imageInput.addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            imagePreview.innerHTML = '';
            
            files.forEach((file, index) => {
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const previewItem = document.createElement('div');
                        previewItem.className = 'preview-item';
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.alt = 'Preview';
                        img.onerror = function() {
                            console.error('Failed to load image preview');
                            previewItem.remove();
                        };
                        
                        const removeBtn = document.createElement('button');
                        removeBtn.type = 'button';
                        removeBtn.className = 'remove-image';
                        removeBtn.onclick = () => removeImage(index);
                        const icon = document.createElement('i');
                        icon.className = 'fas fa-times';
                        removeBtn.appendChild(icon);
                        
                        previewItem.appendChild(img);
                        previewItem.appendChild(removeBtn);
                        imagePreview.appendChild(previewItem);
                    };
                    reader.onerror = function() {
                        console.error('Failed to read file');
                    };
                    reader.readAsDataURL(file);
                }
            });
        });
    }
});

function removeImage(index) {
    try {
        const imageInput = document.getElementById('images');
        if (!imageInput) return;
        
        const dt = new DataTransfer();
        const files = Array.from(imageInput.files);
        
        files.forEach((file, i) => {
            if (i !== index) dt.items.add(file);
        });
        
        imageInput.files = dt.files;
        imageInput.dispatchEvent(new Event('change'));
    } catch (err) {
        console.error('Error removing image:', err);
    }
}