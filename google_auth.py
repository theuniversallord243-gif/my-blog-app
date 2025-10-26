import os
from authlib.integrations.flask_client import OAuth
from flask import url_for

def init_oauth(app):
    oauth = OAuth(app)
    
    google = oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    
    return oauth, google
