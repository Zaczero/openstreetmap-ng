import logging
import unicodedata
from ipaddress import IPv4Address, IPv6Address, ip_address
from shutil import which
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import msgspec
from fastapi import Request

from app.config import USER_AGENT


# TODO: configure logging
def _log_http_request(r: httpx.Request) -> None:
    logging.debug('Client HTTP request: %s %s', r.method, r.url)


def _log_http_response(r: httpx.Response) -> None:
    if r.is_success:
        logging.debug('Client HTTP response: %s %s %s', r.status_code, r.reason_phrase, r.url)
    else:
        logging.info('Client HTTP response: %s %s %s', r.status_code, r.reason_phrase, r.url)


HTTP = httpx.AsyncClient(
    headers={'User-Agent': USER_AGENT},
    timeout=httpx.Timeout(15),
    follow_redirects=True,
    http1=True,
    http2=True,
    # event_hooks={
    #     'request': [_log_http_request],
    #     'response': [_log_http_response],
    # },
)

# TODO: sorted keys?
_msgpack_encoder = msgspec.msgpack.Encoder(decimal_format='number', uuid_format='bytes')
MSGPACK_ENCODE = _msgpack_encoder.encode
_msgpack_decoder = msgspec.msgpack.Decoder()
MSGPACK_DECODE = _msgpack_decoder.decode
_json_encoder = msgspec.json.Encoder(decimal_format='number')
JSON_ENCODE = _json_encoder.encode
_json_decoder = msgspec.json.Decoder()
JSON_DECODE = _json_decoder.decode


# TODO: reporting of deleted accounts (prometheus)
# NOTE: breaking change


def unicode_normalize(text: str) -> str:
    """
    Normalize a string to NFC form.
    """

    return unicodedata.normalize('NFC', text)


def raise_if_program_unavailable(program: str) -> None:
    """
    Raise an exception if a program is not available.

    >>> raise_if_program_unavailable('bzip2')
    """

    if which(program) is None:
        raise FileNotFoundError(f'Program {program} is not available')


def extend_query_params(uri: str, params: dict) -> str:
    """
    Extend the query parameters of a URI.

    >>> extend_query_params('http://example.com', {'foo': 'bar'})
    'http://example.com?foo=bar'
    """

    if not params:
        return uri

    uri_ = urlsplit(uri)
    query = parse_qsl(uri_.query, keep_blank_values=True)
    query.extend(params.items())
    return urlunsplit(uri_._replace(query=urlencode(query)))


def parse_request_ip(request: Request) -> IPv4Address | IPv6Address:
    """
    Parse the client IP address from a `Request`.
    """

    return ip_address(request.client.host)
