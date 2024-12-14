from flask import Flask, render_template, request, send_from_directory
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse, urljoin
import re
from collections import defaultdict
import json
from time import sleep
import validators
from typing import Dict, List, Any
from ssl import SSLContext
import socket
from pyld import jsonld

app = Flask(__name__, static_folder='static')

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def scrape_page(url, soup):
    from urllib.parse import urljoin
    # Remove jsonld import

    data = defaultdict(list)
    
    # Initialize sources as a dict with list values
    data['sources'] = {
        'scripts': [],
        'styles': [],
        'images': [],
        'fonts': [],
        'videos': [],
        'audio': [],
        'iframes': [],
        'analytics': [],
        'third_party': []
    }
    
    # Initialize structured data correctly
    data.update({
        'seo_data': {
            'title': '',
            'description': '',
            'keywords': [],
            'og_tags': {},
            'twitter_cards': {},
            'canonical': '',
            'robots': '',
            'viewport': '',
            'favicon': '',
        },
        'security': {
            'csp_headers': [],
            'ssl_info': {},
            'security_headers': {},
        },
        'performance': {
            'resource_count': defaultdict(int),
            'total_size': 0,
            'external_resources': [],
        },
        'accessibility': {
            'aria_labels': [],
            'alt_texts': [],
            'form_labels': [],
            'color_contrast': [],
        },
        'structured_data': [],
        'text_content': {
            'paragraphs': [],
            'quotes': [],
            'code_blocks': [],
            'lists': [],
        },
        'media': {
            'images': [],
            'videos': [],
            'audio': [],
            'svg': [],
            'canvas': [],
        },
        'links': [],
        'images': [],
        'headings': [],
        'meta': [],
        'emails': [],
        'social_media': [],
        'forms': [],
        'phones': [],
    })

    # Special handling for vercel apps
    if 'vercel.app' in url:
        # Attempt to find SPA content
        main_content = soup.find('div', id='__next') or soup.find('div', id='root')
        if (main_content):
            # Process main content first
            data['main_content'] = main_content.text.strip()
            
            # Extract specific sections from the SPA
            sections = main_content.find_all(['section', 'div'], class_=lambda x: x and ('section' in x.lower() or 'container' in x.lower()))
            for section in sections:
                section_id = section.get('id', '').lower()
                if section_id:
                    data['sections'].append({
                        'id': section_id,
                        'content': section.text.strip(),
                        'html': str(section)
                    })

    # Scrape links
    for link in soup.find_all('a', href=True):
        title = link.text.strip()
        href = link['href']
        if not href.startswith(('http://', 'https://')):
            href = requests.compat.urljoin(url, href)
        data['links'].append({'title': title, 'url': href})

    # Scrape images
    for img in soup.find_all('img', src=True):
        src = img['src']
        if not src.startswith(('http://', 'https://')):
            src = requests.compat.urljoin(url, src)
        alt = img.get('alt', '')
        data['images'].append({'src': src, 'alt': alt})

    # Scrape headings
    for i in range(1, 7):
        for heading in soup.find_all(f'h{i}'):
            text = heading.text.strip()
            if text:
                data['headings'].append({'level': i, 'text': text})

    # Scrape meta information
    for meta in soup.find_all('meta'):
        name = meta.get('name', '') or meta.get('property', '')
        content = meta.get('content', '')
        if name and content:
            data['meta'].append({'name': name, 'content': content})

    # Extract emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, soup.text)
    data['emails'] = list(set(emails))  # Remove duplicates

    # Scrape social media links
    social_patterns = {
        'facebook': r'facebook\.com',
        'twitter': r'twitter\.com|x\.com',
        'linkedin': r'linkedin\.com',
        'instagram': r'instagram\.com',
        'youtube': r'youtube\.com'
    }
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        for platform, pattern in social_patterns.items():
            if re.search(pattern, href, re.I):
                data['social_media'].append({'platform': platform, 'url': href})

    # Scrape scripts and stylesheets
    for script in soup.find_all('script', src=True):
        src = requests.compat.urljoin(url, script['src'])
        script_type = script.get('type', 'javascript')
        script_info = {
            'src': src,
            'type': script_type,
            'async': script.get('async', False),
            'defer': script.get('defer', False)
        }
        data['sources']['scripts'].append(script_info)
        
        # Detect analytics and third-party scripts
        if any(service in src.lower() for service in ['google-analytics', 'gtag', 'analytics', 'pixel', 'tracking']):
            data['sources']['analytics'].append(script_info)
        if not urlparse(src).netloc in urlparse(url).netloc:
            data['sources']['third_party'].append(script_info)

    # Collect stylesheet sources
    for link in soup.find_all('link', rel='stylesheet'):
        href = requests.compat.urljoin(url, link.get('href', ''))
        if href:
            style_info = {
                'href': href,
                'media': link.get('media', 'all'),
                'type': link.get('type', 'text/css')
            }
            data['sources']['styles'].append(style_info)

    # Collect font sources
    for font_link in soup.find_all('link', rel='preload'):
        if font_link.get('as') == 'font':
            data['sources']['fonts'].append({
                'href': requests.compat.urljoin(url, font_link['href']),
                'type': font_link.get('type', ''),
                'family': font_link.get('crossorigin', 'anonymous')
            })

    # Collect video sources
    for video in soup.find_all('video'):
        video_info = {
            'src': video.get('src', ''),
            'poster': video.get('poster', ''),
            'sources': []
        }
        for source in video.find_all('source'):
            video_info['sources'].append({
                'src': requests.compat.urljoin(url, source['src']),
                'type': source.get('type', '')
            })
        data['sources']['videos'].append(video_info)

    # Collect iframe sources
    for iframe in soup.find_all('iframe'):
        data['sources']['iframes'].append({
            'src': requests.compat.urljoin(url, iframe.get('src', '')),
            'title': iframe.get('title', ''),
            'width': iframe.get('width', 'auto'),
            'height': iframe.get('height', 'auto')
        })

    # Scrape forms
    for form in soup.find_all('form'):
        form_info = {
            'action': form.get('action', ''),
            'method': form.get('method', 'get').lower(),
            'inputs': []
        }
        for input_tag in form.find_all(['input', 'select', 'textarea', 'button']):
            input_info = {
                'type': input_tag.get('type', input_tag.name),
                'name': input_tag.get('name'),
                'id': input_tag.get('id'),
                'value': input_tag.get('value', ''),
                'placeholder': input_tag.get('placeholder', '')
            }
            form_info['inputs'].append(input_info)
        data['forms'].append(form_info)

    # Extract phone numbers
    phone_pattern = r'\+?\d[\d\s\-\(\)]{7,}\d'
    text = soup.get_text()
    phones = re.findall(phone_pattern, text)
    data['phones'] = list(set(phone.strip() for phone in phones))  # Remove duplicates and strip whitespace

    # SEO Data Extraction
    def extract_seo_data():
        data['seo_data'] = {
            'title': soup.title.string if soup.title else '',
            'meta_description': '',
            'meta_keywords': [],
            'og_tags': {},
            'twitter_cards': {},
            'canonical': '',
            'robots': '',
            'viewport': '',
            'language': soup.html.get('lang', ''),
        }
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            property = meta.get('property', '').lower()
            content = meta.get('content', '')

            if name == 'description':
                data['seo_data']['meta_description'] = content
            elif name == 'keywords':
                data['seo_data']['meta_keywords'] = [k.strip() for k in content.split(',')]
            elif property.startswith('og:'):
                data['seo_data']['og_tags'][property[3:]] = content
            elif property.startswith('twitter:'):
                data['seo_data']['twitter_cards'][property[8:]] = content
            elif name == 'robots':
                data['seo_data']['robots'] = content
            elif name == 'viewport':
                data['seo_data']['viewport'] = content

        canonical_link = soup.find('link', rel='canonical')
        if canonical_link:
            data['seo_data']['canonical'] = canonical_link.get('href', '')

    # Extract Security Headers
    def extract_security_info():
        data['security'] = {
            'csp': '',
            'hsts': '',
            'x_content_type_options': '',
            'x_frame_options': '',
            'x_xss_protection': '',
        }
        try:
            response = requests.get(url)
            headers = response.headers
            data['security']['csp'] = headers.get('Content-Security-Policy', '')
            data['security']['hsts'] = headers.get('Strict-Transport-Security', '')
            data['security']['x_content_type_options'] = headers.get('X-Content-Type-Options', '')
            data['security']['x_frame_options'] = headers.get('X-Frame-Options', '')
            data['security']['x_xss_protection'] = headers.get('X-XSS-Protection', '')
        except:
            pass

    # Extract Performance Metrics
    def extract_performance_metrics():
        data['performance'] = {
            'total_requests': 0,
            'total_size_kb': 0,
            'resource_types': defaultdict(int),
        }
        # Placeholder implementation

    # Analyze Accessibility Features
    def analyze_accessibility():
        data['accessibility'] = {
            'aria_labels': [],
            'alt_texts_missing': [],
            'form_labels_missing': [],
        }
        for tag in soup.find_all(True):
            if tag.has_attr('aria-label'):
                data['accessibility']['aria_labels'].append(tag['aria-label'])
            if tag.name == 'img' and not tag.get('alt'):
                data['accessibility']['alt_texts_missing'].append(tag.get('src'))
            if tag.name == 'input' and not tag.get('aria-label') and not tag.get('label'):
                data['accessibility']['form_labels_missing'].append(tag.get('name'))

    # Extract Structured Data
    def extract_structured_data():
        data['structured_data'] = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                json_content = json.loads(script.string)
                # Expand JSON-LD content
                if isinstance(json_content, dict):
                    expanded = jsonld.expand(json_content)
                    data['structured_data'].append(expanded)
                elif isinstance(json_content, list):
                    # Handle multiple JSON-LD objects
                    for item in json_content:
                        if isinstance(item, dict):
                            expanded = jsonld.expand(item)
                            data['structured_data'].append(expanded)
            except (json.JSONDecodeError, jsonld.JsonLdError):
                continue

    # Extract Text Content
    def extract_text_content():
        data['text_content'] = {
            'paragraphs': [p.get_text(strip=True) for p in soup.find_all('p')],
            'lists': [ul.get_text(strip=True) for ul in soup.find_all(['ul', 'ol'])],
            'code_blocks': [code.get_text(strip=True) for code in soup.find_all('code')],
        }

    # Extract Media Information
    def extract_media():
        data['media'] = {
            'videos': [],
            'audios': [],
        }
        for video in soup.find_all('video'):
            data['media']['videos'].append({
                'src': video.get('src'),
                'sources': [source.get('src') for source in video.find_all('source')],
            })
        for audio in soup.find_all('audio'):
            data['media']['audios'].append({
                'src': audio.get('src'),
                'sources': [source.get('src') for source in audio.find_all('source')],
            })

    # Execute all extraction functions
    extract_seo_data()
    extract_security_info()
    extract_performance_metrics()
    analyze_accessibility()
    extract_structured_data()
    extract_text_content()
    extract_media()

    return dict(data)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        
        if not url:
            return render_template('index.html', error="Please enter a URL")
        
        if not is_valid_url(url):
            return render_template('index.html', error="Please enter a valid URL")

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            scraped_data = scrape_page(url, soup)
            
            return render_template('index.html', 
                                url=url,
                                data=scraped_data,
                                page_title=soup.title.string if soup.title else "No title")
            
        except Exception as e:
            return render_template('index.html', error=f"An error occurred: {str(e)}", url=url)

    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)
