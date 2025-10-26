from flask import make_response
import sqlite3
from datetime import datetime

def generate_sitemap(app):
    """Generate XML sitemap for all blog posts"""
    
    @app.route('/sitemap.xml')
    def sitemap():
        pages = []
        
        # Add static pages
        pages.append({
            'loc': 'https://my-blog-app-utli.onrender.com/',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'daily',
            'priority': '1.0'
        })
        
        pages.append({
            'loc': 'https://my-blog-app-utli.onrender.com/login',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'monthly',
            'priority': '0.5'
        })
        
        pages.append({
            'loc': 'https://my-blog-app-utli.onrender.com/register',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'monthly',
            'priority': '0.5'
        })
        
        # Add all blog posts
        try:
            with sqlite3.connect('blog_app.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, created_at FROM blogs ORDER BY created_at DESC')
                blogs = cursor.fetchall()
                
                for blog in blogs:
                    blog_id, created_at = blog
                    pages.append({
                        'loc': f'https://my-blog-app-utli.onrender.com/blog/{blog_id}',
                        'lastmod': created_at.split()[0] if created_at else datetime.now().strftime('%Y-%m-%d'),
                        'changefreq': 'weekly',
                        'priority': '0.8'
                    })
        except Exception as e:
            print(f"Error generating sitemap: {e}")
        
        # Generate XML
        sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for page in pages:
            sitemap_xml += '  <url>\n'
            sitemap_xml += f'    <loc>{page["loc"]}</loc>\n'
            sitemap_xml += f'    <lastmod>{page["lastmod"]}</lastmod>\n'
            sitemap_xml += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
            sitemap_xml += f'    <priority>{page["priority"]}</priority>\n'
            sitemap_xml += '  </url>\n'
        
        sitemap_xml += '</urlset>'
        
        response = make_response(sitemap_xml)
        response.headers['Content-Type'] = 'application/xml'
        return response
