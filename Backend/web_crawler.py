#!/usr/bin/env python3
import os
import logging
import hashlib
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Set, Dict, Any

import requests
from bs4 import BeautifulSoup
from opensearchpy import OpenSearch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebCrawler:
    def __init__(
        self,
        opensearch_url: str,
        username: str,
        password: str,
        index_name: str = "web_pages"
    ):
        self.index_name = index_name
        self.visited_urls: Set[str] = set()
        
        # OpenSearch Client
        self.client = OpenSearch(
            hosts=[opensearch_url],
            http_auth=(username, password),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        self._create_index()
    
    def _create_index(self):
        """Erstellt Index für Webseiten"""
        if self.client.indices.exists(index=self.index_name):
            logger.info(f"Index '{self.index_name}' existiert bereits")
            return
        
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "html_analyzer": {
                            "type": "standard",
                            "stopwords": "_german_"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "url": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "html_analyzer",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "html_analyzer"
                    },
                    "description": {"type": "text"},
                    "keywords": {"type": "keyword"},
                    "author": {"type": "text"},
                    "crawled_date": {"type": "date"},
                    "last_modified": {"type": "date"},
                    "links": {"type": "keyword"},
                    "domain": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "url_hash": {"type": "keyword"}
                }
            }
        }
        
        self.client.indices.create(index=self.index_name, body=mapping)
        logger.info(f"Index '{self.index_name}' erstellt")
    
    def calculate_url_hash(self, url: str) -> str:
        """Berechnet Hash für URL"""
        return hashlib.sha256(url.encode()).hexdigest()
    
    def is_valid_url(self, url: str, base_domain: str) -> bool:
        """Prüft ob URL gültig und zur Domain gehört"""
        parsed = urlparse(url)
        
        # Nur HTTP/HTTPS
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Nur URLs der Basis-Domain
        if base_domain and parsed.netloc != base_domain:
            return False
        
        # Keine Medien-Dateien
        excluded_extensions = ['.pdf', '.jpg', '.png', '.gif', '.zip', '.exe']
        if any(url.lower().endswith(ext) for ext in excluded_extensions):
            return False
        
        return True
    
    def extract_text_from_html(self, html: str) -> Dict[str, Any]:
        """Extrahiert Text und Metadaten aus HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Skripte und Styles entfernen
        for script in soup(['script', 'style', 'nav', 'footer']):
            script.decompose()
        
        # Titel extrahieren
        title = soup.title.string if soup.title else ''
        
        # Meta-Tags extrahieren
        description = ''
        keywords = []
        author = ''
        
        for meta in soup.find_all('meta'):
            if meta.get('name') == 'description':
                description = meta.get('content', '')
            elif meta.get('name') == 'keywords':
                keywords = [k.strip() for k in meta.get('content', '').split(',')]
            elif meta.get('name') == 'author':
                author = meta.get('content', '')
        
        # Hauptinhalt extrahieren
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        text = main_content.get_text(separator=' ', strip=True) if main_content else ''
        
        # Links extrahieren
        links = []
        for link in soup.find_all('a', href=True):
            links.append(link['href'])
        
        return {
            'title': title,
            'content': text,
            'description': description,
            'keywords': keywords,
            'author': author,
            'links': links
        }
    
    def crawl_page(self, url: str) -> bool:
        """Crawlt eine einzelne Seite"""
        try:
            if url in self.visited_urls:
                return False
            
            logger.info(f"Crawle: {url}")
            self.visited_urls.add(url)
            
            # Seite abrufen
            headers = {
                'User-Agent': 'OpenSearchCrawler/1.0'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Nur HTML verarbeiten
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                logger.info(f"Überspringe nicht-HTML: {url}")
                return False
            
            # Prüfen ob bereits indexiert
            url_hash = self.calculate_url_hash(url)
            query = {"query": {"term": {"url_hash": url_hash}}}
            existing = self.client.search(index=self.index_name, body=query)
            
            if existing['hits']['total']['value'] > 0:
                logger.info(f"URL bereits indexiert: {url}")
                return False
            
            # Text extrahieren
            extracted = self.extract_text_from_html(response.text)
            
            # Domain extrahieren
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Dokument erstellen
            doc = {
                'url': url,
                'url_hash': url_hash,
                'title': extracted['title'],
                'content': extracted['content'],
                'description': extracted['description'],
                'keywords': extracted['keywords'],
                'author': extracted['author'],
                'links': extracted['links'],
                'domain': domain,
                'crawled_date': datetime.now().isoformat(),
                'last_modified': response.headers.get('Last-Modified', ''),
                'language': 'de'  # Könnte man automatisch erkennen
            }
            
            # Indexieren
            self.client.index(
                index=self.index_name,
                body=doc,
                id=url_hash
            )
            
            logger.info(f"Seite indexiert: {url}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Crawlen von {url}: {e}")
            return False
    
    def crawl_website(
        self,
        start_url: str,
        max_pages: int = 100,
        same_domain_only: bool = True
    ):
        """Crawlt eine komplette Website"""
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc if same_domain_only else None
        
        to_visit = [start_url]
        pages_crawled = 0
        
        while to_visit and pages_crawled < max_pages:
            url = to_visit.pop(0)
            
            if url in self.visited_urls:
                continue
            
            # Seite crawlen
            if self.crawl_page(url):
                pages_crawled += 1
                
                # Links zur Warteschlange hinzufügen
                try:
                    response = requests.get(url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    for link in soup.find_all('a', href=True):
                        absolute_url = urljoin(url, link['href'])
                        
                        if self.is_valid_url(absolute_url, base_domain):
                            if absolute_url not in self.visited_urls:
                                to_visit.append(absolute_url)
                
                except Exception as e:
                    logger.error(f"Fehler beim Extrahieren von Links: {e}")
        
        logger.info(f"Crawling abgeschlossen. {pages_crawled} Seiten indexiert.")
    
    def search(self, query: str, size: int = 10) -> Dict[str, Any]:
        """Sucht in indizierten Webseiten"""
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "content^2", "description", "keywords"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "content": {},
                    "title": {},
                    "description": {}
                }
            },
            "size": size
        }
        
        return self.client.search(index=self.index_name, body=search_body)


def main():
    """Beispiel-Verwendung"""
    opensearch_url = os.getenv('OPENSEARCH_URL', 'https://localhost:9200')
    opensearch_user = os.getenv('OPENSEARCH_USER', 'admin')
    opensearch_password = os.getenv('OPENSEARCH_PASSWORD', 'Admin123!')
    
    crawler = WebCrawler(
        opensearch_url=opensearch_url,
        username=opensearch_user,
        password=opensearch_password
    )
    
    # Beispiel: Website crawlen
    start_url = os.getenv('CRAWL_URL', 'https://example.com')
    max_pages = int(os.getenv('MAX_PAGES', '50'))
    
    logger.info(f"Starte Crawling von {start_url}")
    crawler.crawl_website(start_url, max_pages=max_pages)


if __name__ == '__main__':
    main()
