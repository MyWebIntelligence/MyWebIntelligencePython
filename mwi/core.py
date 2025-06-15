"""
Core functions
"""
import asyncio
import json
import re
from argparse import Namespace
from os import path
from typing import Union
from urllib.parse import urlparse

import aiohttp
import nltk
import requests
from bs4 import BeautifulSoup
from nltk.stem.snowball import FrenchStemmer
from nltk.tokenize import word_tokenize
from peewee import IntegrityError, JOIN, SQL
import trafilatura # Added import

import settings
from . import model
from .export import Export

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


def confirm(message: str) -> bool:
    """
    Confirms action by requesting right input from user
    :param message:
    :return:
    """
    return input(message) == 'Y'


def check_args(args: Namespace, mandatory) -> bool:
    """
    Returns True if all required args are in parsed input args
    :param args:
    :param mandatory:
    :return:
    """
    args = vars(args)
    if isinstance(mandatory, str):
        mandatory = [mandatory]
    for arg in mandatory:
        if arg not in args or args[arg] is None:
            raise ValueError('Argument "%s" is required' % arg)
    return True


def split_arg(arg: str) -> list:
    """
    Splits arg string using comma separator and returns a filtered list
    :param arg:
    :return:
    """
    args = arg.split(",")
    return [a.strip() for a in args if a]


def get_arg_option(name: str, args: Namespace, set_type, default):
    """
    Returns value from optional argument
    :param name:
    :param args:
    :param set_type:
    :param default:
    :return:
    """
    args = vars(args)
    if (name in args) and (args[name] is not None):
        return set_type(args[name])
    return default


def stem_word(word: str) -> str:
    """
    Stems word with NLTK Snowball FrenchStemmer
    :param word:
    :return:
    """
    if 'stemmer' not in stem_word.__dict__:
        stem_word.stemmer = FrenchStemmer()
    return stem_word.stemmer.stem(word.lower())


def crawl_domains(limit: int = 0, http: str = None):
    """
    Crawl domains to retrieve info using a pipeline: Trafilatura, Archive.org, then direct requests.
    :param limit: Max number of domains to process.
    :param http: Filter by specific HTTP status (for recrawling).
    :return: Number of successfully processed domains.
    """
    domains_query = model.Domain.select()
    if limit > 0:
        domains_query = domains_query.limit(limit)
    if http is not None: # If http is specified, we are likely recrawling specific statuses
        domains_query = domains_query.where(model.Domain.http_status == http)
    else: # Default: crawl domains not yet fetched
        domains_query = domains_query.where(model.Domain.fetched_at.is_null())

    processed_count = 0
    for domain in domains_query:
        domain_url_https = f"https://{domain.name}"
        domain_url_http = f"http://{domain.name}"
        html_content = None
        effective_url = None
        source_method = None
        final_status_code = None

        # Reset fields that might be populated by previous attempts
        domain.title = None
        domain.description = None
        domain.keywords = None

        # Attempt 1: Trafilatura (tries HTTPS then HTTP internally if not specified)
        print(f"Attempting Trafilatura for {domain.name} ({domain_url_https})")
        try:
            # Trafilatura's fetch_url tries to find a working scheme
            downloaded = trafilatura.fetch_url(domain_url_https)
            if not downloaded: # Try HTTP if HTTPS failed
                 downloaded = trafilatura.fetch_url(domain_url_http)

            if downloaded:
                html_content = downloaded
                # fetch_url doesn't directly give status or final url, assume 200 if content received
                # For effective_url, we can try to get it from metadata later or use the input.
                # For now, let's assume the input URL that worked.
                # We need to determine if HTTPS or HTTP was successful for effective_url
                try:
                    # A bit of a hack: check if https version gives content
                    # This is imperfect as trafilatura might have its own redirect logic
                    requests.get(domain_url_https, timeout=2, allow_redirects=False).raise_for_status()
                    effective_url = domain_url_https
                except:
                    effective_url = domain_url_http

                final_status_code = "200" # Assume success if trafilatura returned content
                source_method = "TRAFILATURA"
                print(f"Trafilatura success for {domain.name} (URL: {effective_url})")
            else:
                print(f"Trafilatura failed to fetch content for {domain.name}")
        except Exception as e_trafi:
            print(f"Trafilatura exception for {domain.name}: {e_trafi}")
            final_status_code = "ERR_TRAFI"

        # Attempt 2: Archive.org (if Trafilatura failed)
        if not html_content:
            print(f"Attempting Archive.org for {domain.name}")
            try:
                # Prefer HTTPS for archive.org lookup, but it handles redirects
                archive_data_url = f"http://archive.org/wayback/available?url={domain_url_https}"
                archive_response = requests.get(archive_data_url, timeout=settings.default_timeout)
                archive_response.raise_for_status()
                archive_data = archive_response.json()
                
                archived_snapshot = archive_data.get('archived_snapshots', {}).get('closest', {})
                if archived_snapshot and archived_snapshot.get('available') and archived_snapshot.get('url'):
                    effective_url = archived_snapshot['url']
                    print(f"Found archived URL: {effective_url}")
                    archived_content_response = requests.get(
                        effective_url,
                        headers={"User-Agent": settings.user_agent},
                        timeout=settings.default_timeout
                    )
                    # We don't use raise_for_status() here as archive.org might return non-200 for the page itself
                    # but still provide content. The status code of the *archived page* is what matters.
                    final_status_code = str(archived_snapshot.get('status', '200')) # Use archived status
                    
                    if 'text/html' in archived_content_response.headers.get('Content-Type', '').lower():
                        html_content = archived_content_response.text
                        source_method = "ARCHIVE_ORG"
                        print(f"Archive.org success for {domain.name} (Status: {final_status_code})")
                    else:
                        print(f"Archive.org content for {domain.name} not HTML: {archived_content_response.headers.get('Content-Type')}")
                        if not final_status_code or final_status_code == '200': # If status was ok but not html
                            final_status_code = "ARC_NO_HTML"
                else:
                    print(f"No suitable archive found for {domain.name}")
                    final_status_code = "ERR_ARCHIVE_NF" # Not Found
            except requests.exceptions.Timeout:
                print(f"Archive.org timeout for {domain.name}")
                final_status_code = "ERR_ARCHIVE_TO"
            except requests.exceptions.RequestException as e_arc_req:
                print(f"Archive.org request exception for {domain.name}: {e_arc_req}")
                final_status_code = "ERR_ARCHIVE_REQ"
            except Exception as e_archive:
                print(f"Archive.org general exception for {domain.name}: {e_archive}")
                final_status_code = "ERR_ARCHIVE"

        # Attempt 3: Direct Requests (if Trafilatura and Archive.org failed)
        if not html_content:
            print(f"Attempting direct requests for {domain.name}")
            urls_to_try = [domain_url_https, domain_url_http]
            for current_url_to_try in urls_to_try:
                try:
                    response = requests.get(
                        current_url_to_try,
                        headers={"User-Agent": settings.user_agent},
                        timeout=settings.default_timeout,
                        allow_redirects=True # Allow redirects to find the final page
                    )
                    final_status_code = str(response.status_code)
                    effective_url = response.url # URL after redirects

                    if response.ok and 'text/html' in response.headers.get('Content-Type', '').lower():
                        html_content = response.text
                        source_method = "REQUESTS"
                        print(f"Direct request success for {domain.name} (URL: {effective_url}, Status: {final_status_code})")
                        break # Success, no need to try other URL
                    else:
                        print(f"Direct request for {current_url_to_try} failed or not HTML. Status: {final_status_code}, Content-Type: {response.headers.get('Content-Type')}")
                        if response.ok and not ('text/html' in response.headers.get('Content-Type', '').lower()):
                             final_status_code = "REQ_NO_HTML" # Mark as non-HTML success
                except requests.exceptions.Timeout:
                    print(f"Direct request timeout for {current_url_to_try}")
                    final_status_code = "ERR_REQ_TO"
                except requests.exceptions.RequestException as e_req:
                    print(f"Direct request exception for {current_url_to_try}: {e_req}")
                    final_status_code = "ERR_REQ" # General request error
                except Exception as e_direct: # Catch any other unexpected errors
                    print(f"Direct request general exception for {current_url_to_try}: {e_direct}")
                    final_status_code = "ERR_UNKNOWN"
            if not html_content and not final_status_code: # If all attempts failed without setting a status
                final_status_code = "ERR_ALL_FAILED"


        domain.fetched_at = model.datetime.datetime.now()
        domain.http_status = final_status_code if final_status_code else "ERR_NO_STATUS"

        if html_content and source_method:
            try:
                process_domain_content(domain, html_content, effective_url or domain_url_https, source_method)
                print(f"Domain {domain.name} processed successfully via {source_method}.")
                processed_count += 1
            except Exception as e_proc:
                print(f"Error processing content for domain {domain.name}: {e_proc}")
                domain.http_status = "ERR_PROCESS" # Mark as processing error
        else:
            print(f"Failed to fetch HTML for domain {domain.name} after all attempts. Final status: {domain.http_status}")
            # Ensure some basic info if all fails
            domain.title = domain.title or f"Website: {domain.name} (Fetch Failed)"

        try:
            domain.save()
        except Exception as e_save:
            print(f"CRITICAL: Failed to save domain {domain.name}: {e_save}")
            # Potentially log this more severely or handle retry

    return processed_count


def process_domain_content(domain: model.Domain, html_content: str, effective_url: str, source_method: str):
    """
    Process domain info from HTML content obtained via the pipeline.
    Uses enhanced metadata extraction (BeautifulSoup helpers and Trafilatura).
    :param domain: The domain object to update.
    :param html_content: The HTML content of the domain's page.
    :param effective_url: The URL from which the content was actually fetched (could be live or archive).
    :param source_method: String indicating how content was obtained (e.g., "TRAFILATURA", "ARCHIVE_ORG", "REQUESTS").
    """
    # 1. Use BeautifulSoup based helpers (og: twitter: schema: etc.)
    soup = BeautifulSoup(html_content, 'html.parser')
    bs_title = get_title(soup)
    bs_description = get_description(soup)
    bs_keywords = get_keywords(soup)

    # 2. Use Trafilatura's metadata extraction
    trafi_title = None
    trafi_description = None
    trafi_keywords_list = None
    
    try:
        # Ensure html_content is not None or empty before passing to trafilatura
        if html_content:
            meta_object = trafilatura.extract_metadata(html_content) # Removed url=effective_url
            if meta_object:
                trafi_title = meta_object.title
                trafi_description = meta_object.description
                if meta_object.tags: # Trafilatura uses 'tags'
                     trafi_keywords_list = meta_object.tags
        else:
            print(f"HTML content is empty for {domain.name} ({effective_url}), skipping trafilatura metadata.")
            
    except Exception as e_t_meta:
        print(f"Error during trafilatura.extract_metadata for {domain.name} ({effective_url}): {e_t_meta}")

    # 3. Combine results
    # Prioritize Trafilatura if available, then BS, then existing (if any, though usually None at this stage for domain)
    final_title = trafi_title or bs_title
    final_description = trafi_description or bs_description
    
    final_keywords_str = None
    if trafi_keywords_list:
        final_keywords_str = ", ".join(trafi_keywords_list)
    elif bs_keywords: # Only use bs_keywords if trafilatura didn't provide any
        final_keywords_str = bs_keywords
    
    print(f"Metadata from '{source_method}' for {domain.name} (URL: {effective_url}):\n"
          f"  BS: title={bool(bs_title)}, desc={bool(bs_description)}, keyw={bool(bs_keywords)}\n"
          f"  Trafi: title={bool(trafi_title)}, desc={bool(trafi_description)}, tags={bool(trafi_keywords_list)}")

    if final_title:
        domain.title = final_title.strip() if final_title else None
    if final_description:
        domain.description = final_description.strip() if final_description else None
    if final_keywords_str:
        domain.keywords = final_keywords_str.strip() if final_keywords_str else None
    
    # Fallback title if still nothing
    domain.title = domain.title or f"Website: {domain.name}"
    
    print(f"Final domain metadata for {domain.name}: title='{(domain.title or '')[:50]}...', "
          f"description='{(domain.description or '')[:50]}...', keywords='{(domain.keywords or '')[:50]}...'")


def get_meta_content(soup: BeautifulSoup, name: str):
    """
    Get named meta content property
    :param soup:
    :param name:
    :return:
    """
    tag = soup.find('meta', attrs={'name': name})
    if tag and 'content' in tag.attrs:
        content = tag['content'].strip()
        print(f"Found meta content for {name}: {content[:30]}...")
        return content
    return ''


def extract_metadata(url: str) -> dict:
    """
    Extract metadata from webpage with multiple fallback sources
    :param url: URL to extract metadata from
    :return: Dictionary with title, description, and keywords (None if not found)
    """
    try:
        # Ensure URL has a protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        print(f"Extracting metadata from {url}")
        response = requests.get(url, headers={"User-Agent": settings.user_agent}, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = get_title(soup)
        description = get_description(soup)
        keywords = get_keywords(soup)
        
        print(f"Extracted metadata: title={bool(title)}, description={bool(description)}, keywords={bool(keywords)}")
        
        return {
            'title': title,
            'description': description,
            'keywords': keywords
        }
    except Exception as e:
        print(f"Error extracting metadata from {url}: {str(e)}")
        return {'title': None, 'description': None, 'keywords': None}


def get_title(soup: BeautifulSoup) -> str:
    """
    Get page title with fallback chain
    :param soup: BeautifulSoup object
    :return: Title string or None if not found
    """
    # Open Graph title (highest priority)
    og_title = soup.find('meta', attrs={'property': 'og:title'})
    if og_title and og_title.get('content'):
        return og_title['content'].strip()
    
    # Twitter title
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    if twitter_title and twitter_title.get('content'):
        return twitter_title['content'].strip()
    
    # Schema.org title
    schema_title = soup.find('meta', attrs={'itemprop': 'title'})
    if schema_title and schema_title.get('content'):
        return schema_title['content'].strip()
    
    # Standard HTML title (lowest priority)
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    
    return None


def get_description(soup: BeautifulSoup) -> str:
    """
    Get page description with fallback chain
    :param soup: BeautifulSoup object
    :return: Description string or None if not found
    """
    # Standard meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        return meta_desc['content'].strip()
    
    # Open Graph description
    og_desc = soup.find('meta', attrs={'property': 'og:description'})
    if og_desc and og_desc.get('content'):
        return og_desc['content'].strip()
    
    # Twitter description
    twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
    if twitter_desc and twitter_desc.get('content'):
        return twitter_desc['content'].strip()
    
    # Schema.org description
    schema_desc = soup.find('meta', attrs={'itemprop': 'description'})
    if schema_desc and schema_desc.get('content'):
        return schema_desc['content'].strip()
    
    return None


def get_keywords(soup: BeautifulSoup) -> str:
    """
    Get page keywords with fallback chain
    :param soup: BeautifulSoup object
    :return: Keywords string or None if not found
    """
    # Standard meta keywords
    meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
    if meta_keywords and meta_keywords.get('content'):
        return meta_keywords['content'].strip()
    
    # Open Graph keywords (rare but check)
    og_keywords = soup.find('meta', attrs={'property': 'og:keywords'})
    if og_keywords and og_keywords.get('content'):
        return og_keywords['content'].strip()
    
    # Twitter keywords (rare but check)
    twitter_keywords = soup.find('meta', attrs={'name': 'twitter:keywords'})
    if twitter_keywords and twitter_keywords.get('content'):
        return twitter_keywords['content'].strip()
    
    return None


async def crawl_land(land: model.Land, limit: int = 0, http: str = None) -> tuple:
    """
    Start land crawl
    :param land:
    :param limit:
    :param http:
    :return:
    """
    print("Crawling land %d" % land.id)
    dictionary = get_land_dictionary(land)

    expressions = model.Expression.select().where(
        model.Expression.land == land,
        model.Expression.readable.is_null(True) | (model.Expression.readable == '')
    )
    if http is not None:
        expressions = expressions.where(model.Expression.http_status == http)

    if limit > 0:
        expressions = expressions.limit(limit)

    expression_count = expressions.count()
    batch_size = settings.parallel_connections
    batch_count = -(-expression_count//batch_size)
    last_batch_size = expression_count % batch_size
    current_offset = 0
    processed_count = 0

    for current_batch in range(batch_count):
        print("Batch %s/%s" % (current_batch+1, batch_count))
        batch_limit = last_batch_size if (current_batch+1 == batch_count and last_batch_size != 0) else batch_size
        expressions = expressions.limit(batch_limit).offset(current_offset).order_by(model.Expression.depth)
        connector = aiohttp.TCPConnector(limit=settings.parallel_connections, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for expression in expressions:
                tasks.append(crawl_expression(expression, dictionary, session))
            results = await asyncio.gather(*tasks)
            processed_count += sum(results)
        current_offset += batch_size
    return expression_count, expression_count - processed_count


async def crawl_expression(expression: model.Expression, dictionary, session: aiohttp.ClientSession):
    """
    :param expression:
    :param dictionary:
    :param session:
    :return:
    """
    print("Crawling expression %s" % expression.url)
    result = 0
    expression.http_status = '000'
    expression.fetched_at = model.datetime.datetime.now()
    try:
        async with session.get(expression.url,
                               headers={"User-Agent": settings.user_agent},
                               timeout=aiohttp.ClientTimeout(
                                   total=None,
                                   sock_connect=5,
                                   sock_read=5)) as response:
            expression.http_status = response.status
            if response.status == 200 and 'html' in response.headers.get('content-type', ''):
                content = await response.text()
                if content:
                    process_expression_content(expression, content, dictionary)
                    result = 1
            else:
                print(f"Non-200 status for {expression.url}: {response.status}. Trying archive.org.")
                # For non-200 responses, try archive.org immediately
                try:
                    archive_data_url = f"http://archive.org/wayback/available?url={expression.url}"
                    print(f"Fetching archive availability: {archive_data_url}")
                    archive_response = await asyncio.to_thread(
                        lambda: requests.get(archive_data_url, timeout=10)
                    )
                    archive_response.raise_for_status() # Check for errors fetching availability
                    archive_data = archive_response.json()
                    
                    archived_url = archive_data.get('archived_snapshots', {}).get('closest', {}).get('url')
                    if archived_url:
                        print(f"Found archived URL: {archived_url}")
                        archived_content_response = await asyncio.to_thread(
                            lambda: requests.get(archived_url, headers={"User-Agent": settings.user_agent}, timeout=10)
                        )
                        archived_content_response.raise_for_status() # Check for errors fetching content
                        archived_content = archived_content_response.text
                        if archived_content:
                            print(f"Processing archived content for {expression.url}")
                            process_expression_content(expression, archived_content, dictionary)
                            # Prepend comment to the actual readable content from archive
                            if expression.readable:
                                expression.readable = f"<!-- ARCHIVED CONTENT (Original Status: {response.status}) -->\n{expression.readable}"
                            else:
                                expression.readable = f"<!-- ARCHIVED CONTENT (Original Status: {response.status}) -->\n{archived_content[:500]}..." # Fallback if readable is empty
                            result = 1
                        else:
                            print(f"Archived content was empty for {expression.url}")
                    else:
                        print(f"No archived URL found for {expression.url}")
                except Exception as e_archive:
                    print(f"Error during archive.org fallback for {expression.url}: {str(e_archive)}")
            
            expression.save()
            print(f"Saving expression #{expression.id} (status: {expression.http_status}, processed: {bool(result)})")
            return result
            
    except aiohttp.ClientError as e_aio:
        print(f"AIOHTTP ClientError for {expression.url}: {str(e_aio)}")
        expression.http_status = 'ERR_AIO' # Custom status for aiohttp errors
    except requests.exceptions.RequestException as e_req:
        print(f"Requests Exception for {expression.url} (likely during archive.org): {str(e_req)}")
        expression.http_status = 'ERR_REQ' # Custom status for requests errors
    except Exception as e_general:
        print(f"General Exception for {expression.url}: {str(e_general)}")
        expression.http_status = 'ERR_GEN' # Custom status for other errors
    finally:
        # Ensure expression is always saved, even on unhandled errors within the try
        if not expression.id: # If expression was never saved due to early error
             print(f"Expression {expression.url} was not saved due to an early error.")
        else:
            try:
                expression.save()
                print(f"Saving expression #{expression.id} in finally block (status: {expression.http_status})")
            except Exception as e_save:
                print(f"CRITICAL: Failed to save expression #{expression.id} in finally block: {str(e_save)}")
        return result # result will be 0 if an exception occurred before it was set to 1


async def readable_land(land: model.Land, limit: int = 0):
    """
    Process readable content for expressions with empty readable field
    Processing pipeline: trafilatura > Mercuri > archive > raw html
    :param land:
    :param limit:
    :return:
    """
    words = get_land_dictionary(land)
    expressions = model.Expression.select()
    if limit > 0:
        expressions = expressions.limit(limit)
    expressions = expressions.where(
        model.Expression.land == land,
        model.Expression.readable.is_null(True) | (model.Expression.readable == '')
    )

    expression_count = expressions.count()
    batch_size = settings.parallel_connections
    batch_count = -(-expression_count//batch_size)
    last_batch_size = expression_count % batch_size
    current_offset = 0
    processed_count = 0

    for current_batch in range(batch_count):
        print("Batch %s/%s" % (current_batch+1, batch_count))
        batch_limit = last_batch_size if (current_batch+1 == batch_count and last_batch_size != 0) else batch_size
        expressions = expressions.limit(batch_limit).offset(current_offset).order_by(SQL('relevance').desc())

        tasks = []
        for expression in expressions:
            tasks.append(mercury_readable(expression, words))
        results = await asyncio.gather(*tasks)
        processed_count += sum(results)
        current_offset += batch_size
    return expression_count, expression_count - processed_count


async def mercury_readable(expression: model.Expression, words):
    """Strict processing pipeline: trafilatura > Mercuri > archive > raw html"""
    content = None
    raw_html = None
    links = []

    # Step 1: Try Trafilatura
    try:
        from trafilatura import fetch_url, extract
        downloaded = await asyncio.to_thread(fetch_url, expression.url)
        if downloaded:
            raw_html = downloaded
            content = extract(downloaded, include_links=True, include_comments=False, output_format='markdown')
            if content:
                links = extract_md_links(content)
                expression.readable = f"<!-- TRAFILATURA CONTENT -->\n{content}"
                print(f"Trafilatura succeeded for {expression.url}")
    except Exception as e:
        print(f"Trafilatura failed: {str(e)}")

    # Step 2: Fallback to Mercury parser
    if not content:
        try:
            print(f"Trying mercury-parser for {expression.url}")
            proc = await asyncio.create_subprocess_shell(
                f'mercury-parser {expression.url} --format=markdown',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            data = json.loads(stdout.decode())
            if 'content' in data and len(data['content']) > 100:
                content = data['content']
                links = extract_md_links(content)
                expression.readable = f"<!-- MERCURY CONTENT -->\n{content}"
                print(f"Mercury parser succeeded for {expression.url}")
        except Exception as e:
            print(f"Mercury parser failed: {str(e)}")

    # Step 3: Fallback to archive.org
    if not content:
        try:
            print(f"Trying archive.org for {expression.url}")
            archived_url = await asyncio.to_thread(
                lambda: requests.get(
                    f"http://archive.org/wayback/available?url={expression.url}",
                    timeout=5
                ).json().get('archived_snapshots', {}).get('closest', {}).get('url')
            )
            if archived_url:
                from trafilatura import fetch_url, extract
                downloaded = await asyncio.to_thread(fetch_url, archived_url)
                if downloaded:
                    content = extract(downloaded, output_format='markdown')
                    if content:
                        expression.readable = f"<!-- ARCHIVED CONTENT -->\n{content}"
                        print(f"Archive.org succeeded for {expression.url}")
        except Exception as e:
            print(f"Archive.org fallback failed: {str(e)}")

    # Step 4: Final fallback - store raw HTML
    if not content and raw_html:
        expression.readable = f"<!-- PARSER FAILED - RAW HTML -->\n{raw_html}"
        print(f"Storing raw HTML for {expression.url}")

    # Process results if we got any content
    if content or raw_html:
        # Check if page language matches land language
        if expression.lang and expression.land.lang and expression.lang != expression.land.lang:
            expression.relevance = 0
        else:
            expression.relevance = expression_relevance(words, expression)
        
        expression.readable_at = model.datetime.datetime.now()
        expression.save()
        
        # Create links if relevant
        model.ExpressionLink.delete().where(model.ExpressionLink.source == expression.id)
        if expression.relevance > 0 and expression.depth < 3 and links:
            print(f"Linking {len(links)} expressions to #{expression.id}")
            for link in links:
                link_expression(expression.land, expression, link)
        
        return 1 if content else -1
        
    return 0


def extract_md_links(md_content: str):
    """
    Extract URLs from Markdown content
    :param md_content:
    :return:
    """
    matches = re.findall(r'\(((https?|ftp)://[^\s/$.?#].[^\s]*)\)', md_content)
    return [match[0] for match in matches]


def add_expression(land: model.Land, url: str, depth=0) -> Union[model.Expression, bool]:
    """
    Add expression to land
    :param land:
    :param url:
    :param depth:
    :return:
    """
    url = remove_anchor(url)
    if is_crawlable(url):
        domain_name = get_domain_name(url)
        domain = model.Domain.get_or_create(name=domain_name)[0]
        expression = model.Expression.get_or_none(
            model.Expression.url == url,
            model.Expression.land == land)
        if expression is None:
            expression = model.Expression.create(land=land, domain=domain, url=url, depth=depth)
        return expression
    return False


def get_domain_name(url: str) -> str:
    """
    Returns domain from any url as sub.domain.ext or according to heuristics settings
    :param url:
    :return:
    """
    parsed = urlparse(url)
    domain_name = parsed.netloc
    for key, value in settings.heuristics.items():
        if domain_name.endswith(key):
            matches = re.findall(value, url)
            domain_name = matches[0] if matches else domain_name
    return domain_name


def remove_anchor(url: str) -> str:
    """
    Removes anchor from URL
    :param url:
    :return:
    """
    anchor_pos = url.find('#')
    return url[:anchor_pos] if anchor_pos > 0 else url


def link_expression(land: model.Land, source_expression: model.Expression, url: str) -> bool:
    """
    Link target expression to source expression
    :param land:
    :param source_expression:
    :param url:
    :return:
    """
    target_expression = add_expression(land, url, source_expression.depth + 1)
    if target_expression:
        try:
            model.ExpressionLink.create(
                source_id=source_expression.get_id(),
                target_id=target_expression.get_id())
            return True
        except IntegrityError:
            pass
    return False


def is_crawlable(url: str):
    """
    Checks whether an URL is valid for crawling
    :param url:
    :return:
    """
    try:
        parsed = urlparse(url)
        exclude_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.pdf',
                       '.txt', '.csv', '.xls', '.xlsx', '.doc', '.docx')

        return \
            (url is not None) \
            and url.startswith(('http://', 'https://')) \
            and (not url.endswith(exclude_ext))
    except:
        return False


def process_expression_content(expression: model.Expression, html: str, dictionary) -> model.Expression:
    """
    Process expression fields from HTML content
    :param expression:
    :param html:
    :param dictionary:
    :return:
    """
    print("Processing expression #%s" % expression.id)
    soup = BeautifulSoup(html, 'html.parser')

    if soup.html is not None:
        expression.lang = soup.html.get('lang', '')
    
    # Extract basic metadata from the soup object first
    expression.title = soup.title.string.strip() if soup.title and soup.title.string else ''
    expression.description = get_meta_content(soup, 'description')
    expression.keywords = get_meta_content(soup, 'keywords')
    
    print(f"Initial metadata from HTML for expression {expression.id}: title={bool(expression.title)}, "
          f"description={bool(expression.description)}, keywords={bool(expression.keywords)}")
    
    # Try to enhance with more robust metadata extraction
    try:
        metadata = extract_metadata(expression.url)
        
        # Only override if we got better metadata
        if metadata['title']:
            expression.title = metadata['title']
        if metadata['description']:
            expression.description = metadata['description']
        if metadata['keywords']:
            expression.keywords = metadata['keywords']
            
        print(f"Enhanced metadata for expression {expression.id}: title={bool(metadata['title'])}, "
              f"description={bool(metadata['description'])}, keywords={bool(metadata['keywords'])}")
    except Exception as e:
        print(f"Error enhancing metadata for expression {expression.id}: {str(e)}")
    
    # Ensure title has at least an empty string, but leave description and keywords as null if not found
    domain_name = expression.domain.name if expression.domain else urlparse(expression.url).netloc
    expression.title = expression.title or f"Content from {domain_name}"
    # Don't provide default values for description and keywords
    # expression.description = expression.description or None
    # expression.keywords = expression.keywords or None
    
    print(f"Final expression metadata to save: title={bool(expression.title)}, "
          f"description={bool(expression.description)}, keywords={bool(expression.keywords)}")

    clean_html(soup)

    if settings.archive is True:
        loc = path.join(settings.data_location, 'lands/%s/%s') \
              % (expression.land.get_id(), expression.get_id())
        with open(loc, 'w', encoding="utf-8") as html_file:
            html_file.write(html.strip())
        html_file.close()

    readable_content = get_readable(soup)
    if not readable_content.strip():
        expression.readable = f"<!-- RAW HTML -->\n{html}"
    else:
        expression.readable = readable_content

    # Check if page language matches land language
    if expression.lang and expression.land.lang and expression.lang != expression.land.lang:
        expression.relevance = 0
    else:
        expression.relevance = expression_relevance(dictionary, expression)

    if expression.relevance > 0:
        print("Expression #%d approved" % expression.get_id())
        extract_medias(soup, expression)
        expression.approved_at = model.datetime.datetime.now()
        if expression.depth < 3:
            urls = [a.get('href') for a in soup.find_all('a') if is_crawlable(a.get('href'))]
            print("Linking %d expression to #%s" % (len(urls), expression.id))
            for url in urls:
                link_expression(expression.land, expression, url)

    return expression


def extract_medias(content, expression: model.Expression):
    """
    Extract media src (img, video) from html content
    :param content:
    :param expression:
    :return:
    """
    print("Extracting media from #%s" % expression.id)
    medias = []
    for tag in ['img', 'video', 'audio']:
        for element in content.find_all(tag):
            src = element.get('src')
            is_valid_src = src is not None and src not in medias
            if tag == 'img':
                is_valid_src = is_valid_src and src.endswith(".jpg")
            if is_valid_src:
                if src.startswith("/"):
                    src = expression.url[:expression.url.find("/", 9) + 1].strip('/') + src
                media = model.Media.create(expression=expression, url=src, type=tag)
                media.save()


def get_readable(content):
    """
    Get readable part of HTML content
    :param content:
    :return:
    """
    text = content.get_text(separator=' ')
    lines = text.split("\n")
    text_lines = [line.strip() for line in lines if len(line.strip()) > 0]
    return "\n".join(text_lines)


def clean_html(soup):
    """
    Get rid of DOM objects with no valuable content
    :param soup:
    :return:
    """
    remove_selectors = ('script', 'style', 'iframe', 'form', 'footer', '.footer',
                        'nav', '.nav', '.menu', '.social', '.modal')
    for selector in remove_selectors:
        for tag in soup.select(selector):
            tag.decompose()


def get_land_dictionary(land: model.Land):
    """
    Get land dictionary
    :param land:
    :return:
    """
    return model.Word.select() \
        .join(model.LandDictionary, JOIN.LEFT_OUTER) \
        .where(model.LandDictionary.land == land)


def land_relevance(land: model.Land):
    """
    Start relevance computing according to land dictionary for each expression in land
    :param land:
    :return:
    """
    words = get_land_dictionary(land)
    select = model.Expression.select() \
        .where(model.Expression.land == land, model.Expression.readable.is_null(False))
    row_count = select.count()
    if row_count > 0:
        print("Updating relevances for %d expressions, it may take some time." % row_count)
        for expression in select:
            expression.relevance = expression_relevance(words, expression)
            expression.save()


def expression_relevance(dictionary, expression: model.Expression) -> int:
    """
    Compute expression relevance according to land dictionary
    :param dictionary:
    :param expression:
    :return:
    """
    lemmas = [w.lemma for w in dictionary]
    title_relevance = [0]
    content_relevance = [0]

    def get_relevance(text, weight) -> list:
        stems = [stem_word(w) for w in word_tokenize(text, language='french')]
        stemmed_text = " ".join(stems)
        return [sum(weight for _ in re.finditer(r'\b%s\b' % re.escape(lemma), stemmed_text)) for lemma in lemmas]

    try:
        title_relevance = get_relevance(expression.title, 10)
        content_relevance = get_relevance(expression.readable, 1)
    except:
        pass
    return sum(title_relevance) + sum(content_relevance)


def export_land(land: model.Land, export_type: str, minimum_relevance: int):
    """
    Export land data, file extension is set according to export type
    :param land:
    :param export_type:
    :param minimum_relevance:
    :return:
    """
    date_tag = model.datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = path.join(settings.data_location, 'export_land_%s_%s_%s') \
               % (land.name, export_type, date_tag)
    export = Export(export_type, land, minimum_relevance)
    count = export.write(export_type, filename)
    if count > 0:
        print("Successfully exported %s records to %s" % (count, filename))
    else:
        print("No records to export, check crawling state or lower minimum relevance threshold")


def export_tags(land: model.Land, export_type: str, minimum_relevance: int):
    date_tag = model.datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = path.join(settings.data_location, 'export_tags_%s_%s_%s.csv') \
               % (land.name, export_type, date_tag)
    export = Export(export_type, land, minimum_relevance)
    res = export.export_tags(filename)
    if res == 1:
        print("Successfully exported %s" % filename)
    else:
        print("Error exporting %s" % filename)


def update_heuristic():
    """
    Update domains according to heuristic settings
    :return:
    """
    domains = list(model.Domain.select().dicts())
    domains = {x['id']: x for x in domains}
    expressions = model.Expression.select()
    updated = 0
    for expression in expressions:
        domain = get_domain_name(expression.url)
        if domain != domains[expression.domain_id]['name']:
            to_domain, _ = model.Domain.get_or_create(name=domain)
            expression.domain = to_domain
            expression.save()
            updated += 1
    print("%d domain(s) updated" % updated)


def delete_media(land: model.Land, max_width: int = 0, max_height: int = 0, max_size: int = 0):
    expressions = model.Expression.select().where(model.Land == land)
    model.Media.delete().where(model.Media.expression << expressions)
