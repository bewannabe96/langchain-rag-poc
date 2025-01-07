from bs4 import BeautifulSoup
import requests

def is_naver_blog_url(url):
    return url.startswith('https://blog.naver.com')

def extract_naver_blog_iframe_src(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    iframe = soup.find('iframe', {'id': 'mainFrame'})
    if iframe and 'src' in iframe.attrs:
        base_url = 'https://blog.naver.com'
        iframe_url = base_url + iframe['src']
        return iframe_url
    
    return None

def get_original_url(url):
    if is_naver_blog_url(url):
        return extract_naver_blog_iframe_src(url)

    return url

def get_content(url):
    actual_url = get_original_url(url)
    if not actual_url:
        return None
    
    response = requests.get(actual_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    new_soup = BeautifulSoup('', 'html.parser')
    body_tag = new_soup.new_tag('div')
    
    for element in soup.find_all(True):
        if element.name in ['script', 'style', 'link', 'meta', 'iframe', 'header', 'footer', 'nav']:
            continue

        elif element.string and element.string.strip():
            p_tag = new_soup.new_tag('p')
            p_tag.string = element.string.strip()
            body_tag.append(p_tag)
            
        elif element.name == 'img' and element.get('src'):
            img_tag = new_soup.new_tag('img')
            img_tag['src'] = element['src']
            if element.get('alt'):
                img_tag['alt'] = element['alt']
            body_tag.append(img_tag)
            
        elif element.name == 'video' and element.get('src'):
            video_tag = new_soup.new_tag('video')
            video_tag['src'] = element['src']
            video_tag['controls'] = ''
            body_tag.append(video_tag)
    
    # Create clean HTML document
    clean_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    </head>
    {str(body_tag)}
    </html>
    """
    
    return clean_html

# iframe_src = get_original_url("https://blog.naver.com/goringkerr/223705215715")
# print(f"iframe source URL: {iframe_src}")

# Save content to file
url = "https://hangamja.tistory.com/2147"
content = get_content(url)

from urllib.parse import urlparse
parsed_url = urlparse(url)
filename = f"content_{parsed_url.netloc.replace('.', '_')}_{parsed_url.path.strip('/').replace('/', '_')}.html"
    
with open(filename, 'w', encoding='utf-8') as f:
    f.write(content)