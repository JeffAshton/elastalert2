from typing import Any
import requests
from elastalert.auth import Auth

from elastalert.util import EAException
from requests import RequestException
from urllib.parse import urljoin, urlparse

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

    def __init__(self, base_url: str, auth: Any) -> None:
        super().__init__()
        self.auth = auth
        self.goto_url = urljoin(base_url, 'goto/')
        self.shorten_api_url = urljoin(base_url, 'api/shorten_url')

    def format(self, relative_url: str) -> str:
        response = requests.post(
            url = self.shorten_api_url,
            auth = self.auth,
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


def create_kibana_auth(base_url, rule) -> Any:
    kibana_url = rule.get('kibana_url')
    auth = Auth()
    http_auth = auth(
        host = urlparse(kibana_url).hostname,
        username = rule.get('kibana_username'),
        password = rule.get('kibana_password'),
        aws_region = rule.get('aws_region'),
        profile_name = rule.get('profile'),
    )
    return http_auth


def create_kibana_external_url_formatter(rule, shorten: bool) -> KibanaExternalUrlFormatter:
    '''Creates a kibana external url formatter'''

    base_url = rule.get('kibana_url')

    if shorten:
        auth = create_kibana_auth(rule)
        return ShortKibanaExternalUrlFormatter(base_url, auth)

    return AbsoluteKibanaExternalUrlFormatter(base_url)

