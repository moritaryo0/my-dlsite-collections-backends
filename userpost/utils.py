import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from rest_framework.exceptions import ValidationError

def dlsite_get_ogp_data(url:str):
    """
    DLSiteのOGPデータを取得する
    Args:
        url: DLSiteのURL
    Returns:
        ogp_data:
        {
            'title': タイトル,
            'description': 説明,
            'image': 画像URL,
            'url': URL
        }
    """
    try:
        ogp_data = {
            'title': '',
            'description': '',
            'image': '',
            'url': url
        }
        parsed_url = urlparse(url)
        if parsed_url.netloc != 'www.dlsite.com':
            raise ValidationError('Invalid URL')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            if tag.get('property') in ['og:title', 'og:description', 'og:image']:
                property_name = tag.get('property').replace('og:', '')
                ogp_data[property_name] = tag.get('content', '')
        return ogp_data
    except Exception as e:
        print(e)
        return None