from typing import Any
import pytest
import requests

from elastalert.kibana_external_url_formatter import AbsoluteKibanaExternalUrlFormatter, append_security_tenant, create_kibana_external_url_formatter
from elastalert.kibana_external_url_formatter import ShortKibanaExternalUrlFormatter
from elastalert.util import EAException

from unittest import mock

class FormatTestCase:
    def __init__(
         self,
         base_url: str,
         security_tenant: str,
         relative_url: str,
         expected_url: str
    ) -> None:
        self.base_url = base_url
        self.security_tenant = security_tenant
        self.relative_url = relative_url
        self.expected_url = expected_url

@pytest.mark.parametrize("test_case", [
    FormatTestCase(
        base_url = 'http://elasticsearch.test.org:9200/_plugin/kibana/',
        security_tenant = None,
        relative_url = 'app/dev_tools#/console',
        expected_url = 'http://elasticsearch.test.org:9200/_plugin/kibana/app/dev_tools#/console'
    ),
    FormatTestCase(
        base_url = 'http://opensearch.test.org/_dashboards/',
        security_tenant = None,
        relative_url = 'app/dev_tools#/console',
        expected_url = 'http://opensearch.test.org/_dashboards/app/dev_tools#/console'
    ),
    FormatTestCase(
        base_url = 'http://kibana.test.org/',
        security_tenant = None,
        relative_url = '/app/dev_tools#/console',
        expected_url = 'http://kibana.test.org/app/dev_tools#/console'
    )
])
def test_absolute_kinbana_external_url_formatter(
    test_case: FormatTestCase
):
    formatter = AbsoluteKibanaExternalUrlFormatter(
        base_url = test_case.base_url,
        security_tenant = test_case.security_tenant
    )
    actualUrl = formatter.format(test_case.relative_url)
    assert actualUrl == test_case.expected_url


def mock_kibana_shorten_url_api(*args, **kwargs):
    class MockResponse:
        def __init__(self, status_code):
            self.status_code = status_code
        def json(self):
            return {
                'urlId': '62af3ebe6652370f85de91ccb3a3825f'
            }
        def raise_for_status(self):
            if self.status_code == 400:
                raise requests.exceptions.HTTPError()

    json = kwargs['json']
    url = json['url']

    if url.startswith('/app/'):
        return MockResponse(200)
    else:
        return MockResponse(400)

class ShortenUrlTestCase:
    def __init__(
         self,
         base_url: str,
         auth: Any,
         relative_url: str,
         security_tenant: str,
         expected_api_request: Any,
         expected_url: str
    ) -> None:
        self.base_url = base_url
        self.authorization = auth
        self.relative_url = relative_url
        self.security_tenant = security_tenant
        self.expected_api_request = expected_api_request
        self.expected_url = expected_url

@mock.patch('requests.post', side_effect=mock_kibana_shorten_url_api)
@pytest.mark.parametrize("test_case", [
    ShortenUrlTestCase(
        base_url = 'http://elasticsearch.test.org/_plugin/kibana/',
        auth = None,
        security_tenant = None,
        relative_url = 'app/dev_tools#/console',
        expected_api_request = {
            'url': 'http://elasticsearch.test.org/_plugin/kibana/api/shorten_url',
            'auth': None,
            'headers': {
                'kbn-xsrf': 'elastalert',
                'osd-xsrf': 'elastalert'
            },
            'json': {
                'url': '/app/dev_tools#/console'
            }
        },
        expected_url = 'http://elasticsearch.test.org/_plugin/kibana/goto/62af3ebe6652370f85de91ccb3a3825f'
    ),
    ShortenUrlTestCase(
        base_url = 'http://kibana.test.org/',
        auth = 'username:password',
        security_tenant = None,
        relative_url = '/app/dev_tools#/console',
        expected_api_request = {
            'url': 'http://kibana.test.org/api/shorten_url',
            'auth': 'username:password',
            'headers': {
                'kbn-xsrf': 'elastalert',
                'osd-xsrf': 'elastalert'
            },
            'json': {
                'url': '/app/dev_tools#/console'
            }
        },
        expected_url = 'http://kibana.test.org/goto/62af3ebe6652370f85de91ccb3a3825f'
    ),
    ShortenUrlTestCase(
        base_url = 'http://kibana.test.org/',
        auth = None,
        security_tenant = 'global',
        relative_url = '/app/dev_tools#/console',
        expected_api_request = {
            'url': 'http://kibana.test.org/api/shorten_url?security_tenant=global',
            'auth': None,
            'headers': {
                'kbn-xsrf': 'elastalert',
                'osd-xsrf': 'elastalert'
            },
            'json': {
                'url': '/app/dev_tools#/console'
            }
        },
        expected_url = 'http://kibana.test.org/goto/62af3ebe6652370f85de91ccb3a3825f?security_tenant=global'
    )
])
def test_short_kinbana_external_url_formatter(
    mock_post: mock.MagicMock,
    test_case: ShortenUrlTestCase
):
    formatter = ShortKibanaExternalUrlFormatter(
        base_url = test_case.base_url,
        auth = test_case.authorization,
        security_tenant = test_case.security_tenant,
    )

    actualUrl = formatter.format(test_case.relative_url)
    assert actualUrl == test_case.expected_url

    mock_post.assert_called_once_with(**test_case.expected_api_request)


@mock.patch('requests.post', side_effect=mock_kibana_shorten_url_api)
def test_short_kinbana_external_url_formatter_request_exception(mock_post: mock.MagicMock):
    formatter = ShortKibanaExternalUrlFormatter(
        base_url = 'http://kibana.test.org',
        auth = None,
        security_tenant = None,
    )
    with pytest.raises(EAException, match="Failed to invoke Kibana Shorten URL API"):
        formatter.format('http://wacky.org')
    mock_post.assert_called_once()


def test_create_kibana_external_url_formatter_without_shortening():
    formatter = create_kibana_external_url_formatter(
        rule = {
            'kibana_url': 'http://kibana.test.org/'
        },
        shorten = False,
        security_tenant = None
    )
    assert type(formatter) is AbsoluteKibanaExternalUrlFormatter
    assert formatter.base_url == 'http://kibana.test.org/'
    assert formatter.security_tenant == None


def test_create_kibana_external_url_formatter_without_shortening_and_security_tenant():
    formatter = create_kibana_external_url_formatter(
        rule = {
            'kibana_url': 'http://kibana.test.org/'
        },
        shorten = False,
        security_tenant = 'foo'
    )
    assert type(formatter) is AbsoluteKibanaExternalUrlFormatter
    assert formatter.base_url == 'http://kibana.test.org/'
    assert formatter.security_tenant == 'foo'


def test_create_kibana_external_url_formatter_with_shortening():
    formatter = create_kibana_external_url_formatter(
        rule = {
            'kibana_url': 'http://kibana.test.org/',
            'kibana_username': 'username',
            'kibana_password': 'password'
        },
        shorten = True,
        security_tenant = 'foo'
    )
    assert type(formatter) is ShortKibanaExternalUrlFormatter
    assert formatter.auth == 'username:password'
    assert formatter.security_tenant == 'foo'
    assert formatter.goto_url == 'http://kibana.test.org/goto/'
    assert formatter.shorten_url == 'http://kibana.test.org/api/shorten_url?security_tenant=foo'


@pytest.mark.parametrize("test_case", [
    {
        'url': 'http://test.org',
        'expected':  'http://test.org?security_tenant=foo'
    },
    {
        'url': 'http://test.org?year=2021',
        'expected':  'http://test.org?year=2021&security_tenant=foo'
    },
    {
        'url': 'http://test.org#fragement',
        'expected':  'http://test.org?security_tenant=foo#fragement'
    },
    {
        'url': 'http://test.org?year=2021#fragement',
        'expected':  'http://test.org?year=2021&security_tenant=foo#fragement'
    },
])
def test_append_security_tenant(test_case):
    url = test_case.get('url')
    expected = test_case.get('expected')
    result = append_security_tenant(url=url, security_tenant='foo')
    assert result == expected
