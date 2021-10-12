from typing import Any
import requests
from elastalert.auth import Auth

from elastalert.util import EAException
from requests import RequestException
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlsplit, urlunsplit

def append_security_tenant(url, security_tenant):
    '''Appends the security_tenant query string parameter to the url'''
    parsed = urlsplit(url)

    if parsed.query:
        qs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    else:
        qs = []
    qs.append(('security_tenant', security_tenant))

    new_query = urlencode(qs)
    new_args = parsed._replace(query=new_query)
    return urlunsplit(new_args)

class KibanaExternalUrlFormatter:
    '''Formats an external Kibana url'''

    def format(self, relative_url: str) -> str:
        pass

class AbsoluteKibanaExternalUrlFormatter(KibanaExternalUrlFormatter):
    '''Formats an external absolute Kibana url'''

    def __init__(self, base_url: str, security_tenant: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.security_tenant = security_tenant

    def format(self, relative_url: str) -> str:
        url = urljoin(self.base_url, relative_url)
        if self.security_tenant:
            url = append_security_tenant(url, self.security_tenant)
        return url

class ShortKibanaExternalUrlFormatter(KibanaExternalUrlFormatter):
    '''Formats an external url using the Kibana Shorten URL API'''

    def __init__(self, base_url: str, auth: Any, security_tenant: str) -> None:
        super().__init__()
        self.auth = auth
        self.security_tenant = security_tenant
        self.goto_url = urljoin(base_url, 'goto/')

        shorten_url = urljoin(base_url, 'api/shorten_url')
        if security_tenant:
            shorten_url = append_security_tenant(shorten_url, security_tenant)
        self.shorten_url = shorten_url

    def format(self, relative_url: str) -> str:
        # join with '/' to ensure relative to root of app
        long_url = urljoin('/', relative_url)

        try:
            response = requests.post(
                url=self.shorten_url,
                auth=self.auth,
                headers={
                    'kbn-xsrf': 'elastalert',
                    'osd-xsrf': 'elastalert'
                },
                json={
                    'url': long_url
                }
            )
            response.raise_for_status()
        except RequestException as e:
            raise EAException("Failed to invoke Kibana Shorten URL API: %s" % e)

        url_id = response.json().get('urlId')

        goto_url = urljoin(self.goto_url, url_id)
        if self.security_tenant:
            goto_url = append_security_tenant(goto_url, self.security_tenant)
        return goto_url


def create_kibana_auth(rule) -> Any:
    '''Creates a kibana http authentication for use by requests'''
    kibana_url = rule.get('kibana_url')
    kibana_host = urlparse(kibana_url).hostname
    auth = Auth()
    http_auth = auth(
        host=kibana_host,
        username=rule.get('kibana_username'),
        password=rule.get('kibana_password'),
        aws_region=rule.get('aws_region'),
        profile_name=rule.get('profile'),
    )
    return http_auth


def create_kibana_external_url_formatter(
    rule,
    shorten: bool,
    security_tenant: str
) -> KibanaExternalUrlFormatter:
    '''Creates a kibana external url formatter'''

    base_url = rule.get('kibana_url')

    if shorten:
        auth = create_kibana_auth(rule)
        return ShortKibanaExternalUrlFormatter(base_url, auth, security_tenant)

    return AbsoluteKibanaExternalUrlFormatter(base_url, security_tenant)
