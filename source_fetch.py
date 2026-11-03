"""Bounded public-website article extraction (no browser execution, no private hosts)."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 3_000_000
MAX_TEXT = 11_000
MAX_REDIRECTS = 3


class SourceError(ValueError):
    pass


def validate_url(url: str) -> str:
    url = url.strip()
    if len(url) > 2048:
        raise SourceError('URL is too long.')
    parts = urlsplit(url)
    if parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password:
        raise SourceError('Enter a public http or https article/post URL.')
    try:
        port = parts.port
    except ValueError as exc:
        raise SourceError('That URL has an invalid port.') from exc
    if port not in (None, 80, 443):
        raise SourceError('Only ordinary public web URLs are supported.')
    if parts.hostname.lower().rstrip('.') in ('localhost', 'localhost.localdomain'):
        raise SourceError('Local and private addresses are not supported.')
    return url


def check_public_host(url: str) -> None:
    hostname = urlsplit(url).hostname
    try:
        addresses = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise SourceError('Could not resolve that website.') from exc
    if not addresses:
        raise SourceError('Could not resolve that website.')
    for addr in addresses:
        ip = ipaddress.ip_address(addr[4][0])
        if not ip.is_global:
            raise SourceError('Only public internet websites can be fetched.')


def tidy(value: object) -> str:
    return ' '.join(str(value or '').split())


class PostParser(HTMLParser):
    BLOCKS = {'p', 'h1', 'h2', 'h3', 'blockquote', 'li'}
    IGNORE = {'style', 'nav', 'footer', 'form', 'noscript', 'svg', 'aside'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_stack = []
        self.block_depth = 0
        self.chunks = []
        self.textparts = []
        self.title = ''
        self.meta = ''
        self.title_parts = []
        self.in_title = False
        self.ldjson = []
        self.in_ldjson = False
        self.ld_chunks = []
        self.article_depth = 0
        self.article_paragraphs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.skip_stack:
            if tag in self.IGNORE or tag == 'script':
                self.skip_stack.append(tag)
            return
        if tag == 'script':
            if 'ld+json' in a.get('type', '').lower():
                self.in_ldjson = True
                self.ld_chunks = []
            else:
                self.skip_stack.append(tag)
            return
        if tag in self.IGNORE:
            self.skip_stack.append(tag)
            return
        if tag == 'meta':
            key = (a.get('property') or a.get('name') or '').lower()
            if key in ('og:description', 'twitter:description', 'description') and not self.meta:
                self.meta = a.get('content', '')
            if key in ('og:title', 'twitter:title') and not self.title:
                self.title = a.get('content', '')
        if tag == 'title':
            self.in_title = True
        if tag == 'article':
            self.article_depth += 1
        if tag in self.BLOCKS and self.block_depth == 0:
            self.block_depth = 1
            self.chunks = []
        elif tag in self.BLOCKS and self.block_depth:
            self.block_depth += 1

    def handle_endtag(self, tag):
        if self.in_ldjson and tag == 'script':
            if self.ld_chunks:
                self.ldjson.append(''.join(self.ld_chunks))
            self.in_ldjson = False
            self.ld_chunks = []
            return
        if self.skip_stack:
            if tag == self.skip_stack[-1]:
                self.skip_stack.pop()
            return
        if tag == 'title':
            self.in_title = False
            if not self.title:
                self.title = tidy(' '.join(self.title_parts))
        if tag == 'article' and self.article_depth:
            self.article_depth -= 1
        if tag in self.BLOCKS and self.block_depth:
            self.block_depth -= 1
            if not self.block_depth:
                chunk = tidy(''.join(self.chunks))
                if len(chunk) >= 20 and chunk not in self.textparts:
                    self.textparts.append(chunk)
                    if self.article_depth:
                        self.article_paragraphs.append(chunk)
                self.chunks = []

    def handle_data(self, data):
        if self.in_ldjson:
            self.ld_chunks.append(data)
            return
        if self.skip_stack:
            return
        if self.in_title:
            self.title_parts.append(data)
        if self.block_depth:
            self.chunks.append(data)


def structured_article(blobs: list[str]) -> tuple[str, str, str]:
    """Extract publisher-provided JSON-LD without treating arbitrary page data as article text."""
    candidates = []
    def scan(obj):
        if isinstance(obj, list):
            for v in obj:
                scan(v)
        elif isinstance(obj, dict):
            ty = obj.get('@type', '')
            types = ty if isinstance(ty, list) else [ty]
            if any(str(t).lower() in ('article', 'newsarticle', 'blogposting', 'socialmediaposting', 'discussionforumposting') for t in types):
                candidates.append(obj)
            for k in ('@graph', 'mainEntity', 'itemListElement'):
                if k in obj:
                    scan(obj[k])
    for raw in blobs[:30]:
        try:
            scan(json.loads(raw))
        except (json.JSONDecodeError, RecursionError):
            continue
    best = max(candidates, key=lambda c: len(str(c.get('articleBody', ''))), default={})
    title = tidy(best.get('headline') or best.get('name'))
    desc = tidy(best.get('description'))
    body = best.get('articleBody', '')
    if isinstance(body, list):
        body = '\n\n'.join(str(v) for v in body)
    body = tidy(body) if isinstance(body, str) else ''
    return title, desc, body


def extract_html(raw: bytes, url: str) -> dict:
    parser = PostParser()
    parser.feed(raw.decode('utf-8-sig', errors='replace'))
    ld_title, ld_summary, ld_body = structured_article(parser.ldjson)
    title = tidy(ld_title or parser.title)[:300]
    summary = tidy(ld_summary or parser.meta)[:1000]
    # Prefer an actual article body, then article-tag paragraphs, then generic paragraphs.
    text = ld_body or '\n\n'.join(parser.article_paragraphs) or '\n\n'.join(parser.textparts)
    # Pages whose only extracted text is navigation or cookie notices should not be marked full.
    if len(text) >= 180:
        quality = 'full'
    elif title and len(summary) >= 35:
        quality = 'summary'
        text = ''
    elif title and len(title) >= 25:
        quality = 'headline'
        text = ''
    else:
        raise SourceError('This website did not provide readable article content or a usable headline. Try the original publisher link or paste the article text.')
    content = '\n\n'.join(x for x in (title, summary, text) if x)[:MAX_TEXT]
    return {
        'url': url,
        'title': title or urlsplit(url).hostname,
        'content': content,
        'characters': len(content),
        'quality': quality,
        'warning': ('' if quality == 'full' else
                    'Only a summary was retrieved; replies may lack article details.' if quality == 'summary' else
                    'Only the headline was retrieved. Back Quip cannot verify the article details.'),
    }


async def fetch_source(url: str) -> dict:
    url = validate_url(url)
    timeout = httpx.Timeout(15.0, connect=6.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False,
                                 headers={
                                     'User-Agent': 'Mozilla/5.0 (compatible; BackQuip/1.5.1; +https://github.com/blarkin13/back-quip)',
                                     'Accept': 'text/html,application/xhtml+xml',
                                     'Accept-Language': 'en-US,en;q=0.9',
                                 }) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await asyncio.to_thread(check_public_host, url)
            try:
                async with client.stream('GET', url) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        loc = response.headers.get('location')
                        if not loc:
                            raise SourceError('The source redirected without a destination.')
                        url = validate_url(urljoin(url, loc))
                        continue
                    if response.status_code in (401, 403, 429):
                        raise SourceError('That site blocked automated reading. Try the original publisher link or paste the article text.')
                    response.raise_for_status()
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                        raise SourceError('This URL does not serve a readable web page.')
                    chunks, total = [], 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise SourceError('The page is too large to import.')
                        chunks.append(chunk)
                    return extract_html(b''.join(chunks), url)
            except httpx.TimeoutException as exc:
                raise SourceError('The website did not respond in time.') from exc
            except httpx.HTTPError as exc:
                raise SourceError('Could not read that URL. Try the original publisher link or paste the article text.') from exc
        raise SourceError('Too many redirects while loading the source.')
