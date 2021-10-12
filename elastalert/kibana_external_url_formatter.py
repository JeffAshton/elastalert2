import requests

from elastalert.util import EAException
from requests import RequestException
from urllib.parse import urljoin

class KibanaExternalUrlFormatter:
    '''Formats an external Kibana url'''

    def format(self, relative_url: str) -> str:
        pass

class AbsoluteKibanaExternalUrlFormatter(KibanaExternalUrlFormatter):
    '''Formats an external absolute Kibana url'''

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url

    def format(self, relative_url: str) -> str:
        url = urljoin(self.base_url, relative_url)
        return url

class ShortKibanaExternalUrlFormatter(KibanaExternalUrlFormatter):
    '''Formats an external url using the Kibana Shorten URL API'''

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.goto_url = urljoin(base_url, 'goto/')
        self.shorten_api_url = urljoin(base_url, 'api/shorten_url')

    def format(self, relative_url: str) -> str:
        response = requests.post(
            url = self.shorten_api_url,
            headers = {
                'kbn-xsrf': 'elastalert',
                'osd-xsrf': 'elastalert'
            },
            json = {
                # join with '/' to ensure relative to root of app
                'url': urljoin('/', relative_url)
            }
        )
        response.raise_for_status()

        url_id = response.json().get('urlId')
        goto_url = urljoin(self.goto_url, url_id)
        return goto_url
