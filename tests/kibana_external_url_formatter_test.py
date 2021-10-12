from typing import Any
import pytest
import requests

from elastalert.kibana_external_url_formatter import AbsoluteKibanaExternalUrlFormatter
from elastalert.kibana_external_url_formatter import ShortKibanaExternalUrlFormatter

from unittest import mock

class FormatTestCase:
    def __init__(
         self,
         base_url: str,
         relative_url: str,
         expected_url: str
    ) -> None:
        self.base_url = base_url
        self.relative_url = relative_url
        self.expected_url = expected_url

@pytest.mark.parametrize("test_case", [
    FormatTestCase(
        base_url = 'http://elasticsearch.test.org:9200/_plugin/kibana/',
        relative_url = 'app/dev_tools#/console',
        expected_url = 'http://elasticsearch.test.org:9200/_plugin/kibana/app/dev_tools#/console'
    ),
    FormatTestCase(
        base_url = 'http://opensearch.test.org/_dashboards/',
        relative_url = 'app/dev_tools#/console',
        expected_url = 'http://opensearch.test.org/_dashboards/app/dev_tools#/console'
    ),
    FormatTestCase(
        base_url = 'http://kibana.test.org/',
        relative_url = '/app/dev_tools#/console',
        expected_url = 'http://kibana.test.org/app/dev_tools#/console'
    )
])
def test_absolute_kinbana_external_url_formatter(
    test_case: FormatTestCase
):
    formatter = AbsoluteKibanaExternalUrlFormatter(
        base_url = test_case.base_url
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
         expected_api_request: Any,
         expected_url: str
    ) -> None:
        self.base_url = base_url
        self.authorization = auth
        self.relative_url = relative_url
        self.expected_api_request = expected_api_request
        self.expected_url = expected_url

@mock.patch('requests.post', side_effect=mock_kibana_shorten_url_api)
@pytest.mark.parametrize("test_case", [
    ShortenUrlTestCase(
        base_url = 'http://elasticsearch.test.org/_plugin/kibana/',
        auth = None,
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
    )
])
def test_short_kinbana_external_url_formatter(
    mock_post: mock.MagicMock,
    test_case: ShortenUrlTestCase
):
    formatter = ShortKibanaExternalUrlFormatter(
        base_url = test_case.base_url,
        auth = test_case.authorization
    )

    actualUrl = formatter.format(test_case.relative_url)
    assert actualUrl == test_case.expected_url

    mock_post.assert_called_once_with(**test_case.expected_api_request)
