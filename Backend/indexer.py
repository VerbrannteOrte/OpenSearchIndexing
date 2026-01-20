#!/usr/bin/env python3
import os
import time
import logging
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import fnmatch

import requests
from tika import parser
from opensearchpy import OpenSearch, helpers
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pytesseract
from PIL import Image
import pdf2image

from ontology_manager import OntologyManager
from indexing_config import IndexingConfig
from advanced_ocr import AdvancedOCR, BatchOCRProcessor
from metadata_extractor import MetadataExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpenSearchIndexer:
    def __init__(
        self,
        opensearch_url: str,
        username: str,
        password: str,
        tika_url: str,
        index_name: str = "documents",
        ontology_dir: str = "/ontologies",
        config_dir: str = "/config"
    ):
        self.opensearch_url = opensearch_url
        self.tika_url = tika_url
        self.index_name = index_name
        
        # OpenSearch Client erstellen
        self.client = OpenSearch(
            hosts=[opensearch_url],
            http_auth=(username, password),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # Ontologie-Manager initialisieren
        self.ontology = OntologyManager(ontology_dir)
        
        # Indexierungs-Konfiguration laden
        self.indexing_config = IndexingConfig(f"{config_dir}/indexing.json")
        
        # Erweiterte OCR-Engine
        use_gpu = os.getenv('OCR_USE_GPU', 'true').lower() == 'true'
        enable_suetterlin = os.getenv('OCR_ENABLE_SUETTERLIN', 'true').lower() == 'true'
        
        self.advanced_ocr = AdvancedOCR(
            use_gpu=use_gpu,
            enable_suetterlin=enable_suetterlin
        )
        
        # Metadaten-Extraktor
        self.metadata_extractor = MetadataExtractor()
        
        # Batch-Processor
        self.batch_processor = BatchOCRProcessor(self.advanced_ocr, batch_size=10)
        
        # Unterstützte Bild-Formate für OCR
        self.ocr_image_formats = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp']
        
        # Office-Formate
        self.office_formats = {
            'libreoffice': ['.odt', '.ods', '.odp', '.odg', '.odf'],
            'microsoft': ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.docm', '.xlsm', '.pptm']
        }
        
        self._create_index()
    
    def _create_index(self):
        """Erstellt den Index mit optimiertem Mapping für Volltextsuche und Facetten"""
        
        if self.client.indices.exists(index=self.index_name):
            logger.info(f"Index '{self.index_name}' existiert bereits")
            return
        
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "german_analyzer": {
                            "type": "standard",
                            "stopwords": "_german_"
                        },
                        "english_analyzer": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "title": {
                        "type": "text",
                        "analyzer": "german_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "german_analyzer"
                    },
                    "url": {
                        "type": "keyword"
                    },
                    "file_path": {
                        "type": "keyword"
                    },
                    "file_name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "file_extension": {
                        "type": "keyword"
                    },
                    "mime_type": {
                        "type": "keyword"
                    },
                    "file_type_category": {
                        "type": "keyword"
                    },
                    "file_size": {
                        "type": "long"
                    },
                    "created_date": {
                        "type": "date"
                    },
                    "modified_date": {
                        "type": "date"
                    },
                    "indexed_date": {
                        "type": "date"
                    },
                    "hash": {
                        "type": "keyword"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": True
                    },
                    "ocr_text": {
                        "type": "text",
                        "analyzer": "german_analyzer"
                    },
                    "has_ocr": {
                        "type": "boolean"
                    },
                    "language": {
                        "type": "keyword"
                    },
                    "page_count": {
                        "type": "integer"
                    },
                    "source_directory": {
                        "type": "keyword"
                    },
                    # Ontologie-Facetten
                    "concepts": {
                        "properties": {
                            "uri": {"type": "keyword"},
                            "label": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}}
                            },
                            "scheme": {"type": "keyword"},
                            "confidence": {"type": "float"}
                        }
                    },
                    "document_type": {
                        "type": "keyword"
                    },
                    "categories": {
                        "type": "keyword"
                    },
                    "tags": {
                        "type": "keyword"
                    }
                }
            }
        }
        
        self.client.indices.create(index=self.index_name, body=mapping)
        logger.info(f"Index '{self.index_name}' erstellt")
    
    def extract_text_with_tika(self, file_path: str) -> Dict[str, Any]:
        """Extrahiert Text aus Datei mit Apache Tika"""
        try:
            parsed = parser.from_file(
                file_path,
                serverEndpoint=self.tika_url
            )
            
            return {
                'content': parsed.get('content', ''),
                'metadata': parsed.get('metadata', {})
            }
        except Exception as e:
            logger.error(f"Tika Fehler bei {file_path}: {e}")
            return {'content': '', 'metadata': {}}
    
    def extract_text_with_ocr(self, image_path: str, lang: str = 'deu+eng') -> str:
        """Extrahiert Text aus Bild mit erweiterter OCR (inkl. Sütterlin)"""
        try:
            image = Image.open(image_path)
            
            # Verwende erweiterte OCR-Engine
            result = self.advanced_ocr.extract_text_auto(image, lang=lang)
            
            logger.info(f"OCR erfolgreich: {image_path} ({result['method']}, Konfidenz: {result['confidence']:.1f}%)")
            
            return result['text']
        except Exception as e:
            logger.error(f"OCR Fehler bei {image_path}: {e}")
            return ""
    
    def extract_text_from_pdf_with_ocr(self, pdf_path: str, lang: str = 'deu+eng') -> str:
        """Extrahiert Text aus PDF mit erweiterter OCR (für gescannte PDFs)"""
        try:
            # PDF zu Bildern konvertieren
            images = pdf2image.convert_from_path(pdf_path, dpi=300)
            
            ocr_text = []
            for i, pil_image in enumerate(images):
                logger.info(f"OCR für Seite {i+1}/{len(images)} von {pdf_path}")
                
                # Verwende erweiterte OCR
                result = self.advanced_ocr.extract_text_auto(pil_image, lang=lang)
                
                if result['text'].strip():
                    ocr_text.append(f"--- Seite {i+1} ---\n{result['text']}")
            
            result_text = "\n\n".join(ocr_text)
            logger.info(f"PDF OCR erfolgreich: {len(images)} Seiten, {len(result_text)} Zeichen")
            return result_text
            
        except Exception as e:
            logger.error(f"PDF OCR Fehler bei {pdf_path}: {e}")
            return ""
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Berechnet SHA256 Hash der Datei"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Hash-Berechnung fehlgeschlagen für {file_path}: {e}")
            return ""
    
    def extract_concepts(self, text: str) -> List[Dict[str, Any]]:
        """Extrahiert Konzepte aus Text mittels Ontologie"""
        concepts = self.ontology.find_concepts(text)
        
        # Deduplizierung
        unique_concepts = {}
        for concept in concepts:
            uri = concept['uri']
            if uri not in unique_concepts or concept['confidence'] > unique_concepts[uri]['confidence']:
                unique_concepts[uri] = concept
        
        return list(unique_concepts.values())
    
    def get_file_type_category(self, extension: str) -> str:
        """Kategorisiert Dateityp"""
        extension = extension.lower()
        
        if extension == '.pdf':
            return 'PDF'
        elif extension in self.office_formats['libreoffice']:
            return 'LibreOffice'
        elif extension in self.office_formats['microsoft']:
            return 'Microsoft Office'
        elif extension in self.ocr_image_formats:
            return 'Bild'
        elif extension in ['.txt', '.md']:
            return 'Text'
        elif extension in ['.html', '.htm']:
            return 'HTML'
        else:
            return 'Sonstiges'
    
    def index_file(self, file_path: str, source_directory: str = 'unknown') -> bool:
        """Indexiert eine einzelne Datei mit OCR-Unterstützung"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.error(f"Datei nicht gefunden: {file_path}")
                return False
            
            if not path.is_file():
                return False
            
            # Hash berechnen für Duplikat-Erkennung
            file_hash = self.calculate_file_hash(file_path)
            if not file_hash:
                return False
            
            # Prüfen ob bereits indexiert
            query = {
                "query": {
                    "term": {"hash": file_hash}
                }
            }
            response = self.client.search(index=self.index_name, body=query)
            
            if response['hits']['total']['value'] > 0:
                logger.info(f"Datei bereits indexiert: {file_path}")
                return True
            
            # MIME-Type und Extension
            extension = path.suffix.lower()
            mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            file_type_category = self.get_file_type_category(extension)
            
            logger.info(f"Indexiere: {file_path} ({file_type_category})")
            
            # Erweiterte Metadaten extrahieren
            extended_metadata = self.metadata_extractor.extract_metadata(file_path)
            
            # Text extrahieren mit Tika
            tika_result = self.extract_text_with_tika(file_path)
            content = tika_result['content'] or ''
            metadata = tika_result['metadata']
            
            # Metadaten zusammenführen
            metadata.update(extended_metadata)
            
            # OCR durchführen
            ocr_text = ""
            has_ocr = False
            
            # OCR für Bilder
            if extension in self.ocr_image_formats:
                logger.info(f"Führe OCR für Bild durch: {file_path}")
                ocr_text = self.extract_text_with_ocr(file_path)
                has_ocr = len(ocr_text.strip()) > 0
            
            # OCR für PDFs (wenn Tika wenig Text gefunden hat - wahrscheinlich gescannt)
            elif extension == '.pdf':
                # Wenn Tika wenig Text gefunden hat, ist es wahrscheinlich ein gescanntes PDF
                if len(content.strip()) < 100:
                    logger.info(f"PDF scheint gescannt zu sein, führe OCR durch: {file_path}")
                    ocr_text = self.extract_text_from_pdf_with_ocr(file_path)
                    has_ocr = len(ocr_text.strip()) > 0
            
            # Konzepte aus Text extrahieren
            full_text = f"{path.name} {content} {ocr_text}"
            concepts = self.extract_concepts(full_text)
            
            # Kategorien ableiten
            categories = []
            document_type = None
            
            for concept in concepts:
                label = concept['label']
                categories.append(label)
                
                if document_type is None and 'type' in label.lower():
                    document_type = label
            
            # Seitenzahl aus Metadata
            page_count = None
            if 'xmpTPg:NPages' in metadata:
                try:
                    page_count = int(metadata['xmpTPg:NPages'])
                except:
                    pass
            
            # Dokument erstellen
            doc = {
                'title': path.name,
                'file_name': path.name,
                'file_extension': extension,
                'content': content,
                'file_path': str(path.absolute()),
                'mime_type': mime_type,
                'file_type_category': file_type_category,
                'file_size': path.stat().st_size,
                'created_date': datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
                'modified_date': datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                'indexed_date': datetime.now().isoformat(),
                'hash': file_hash,
                'metadata': metadata,
                'ocr_text': ocr_text,
                'has_ocr': has_ocr,
                'language': metadata.get('language', 'unknown'),
                'page_count': page_count,
                'source_directory': source_directory,
                'concepts': concepts,
                'categories': categories,
                'document_type': document_type,
                'tags': []
            }
            
            # In OpenSearch indexieren
            self.client.index(
                index=self.index_name,
                body=doc,
                id=file_hash
            )
            
            logger.info(f"✓ Datei indexiert: {file_path} (OCR: {has_ocr}, Konzepte: {len(concepts)})")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Indexieren von {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def should_index_file(self, file_path: str, directory_config: Dict[str, Any]) -> bool:
        """Prüft ob eine Datei indexiert werden soll"""
        return self.indexing_config.is_file_allowed(file_path, directory_config)
    
    def index_directory(self, directory_config: Dict[str, Any]):
        """Indexiert alle Dateien in einem konfigurierten Verzeichnis"""
        dir_path = Path(directory_config['path'])
        
        if not dir_path.exists():
            logger.warning(f"Verzeichnis existiert nicht: {dir_path}")
            return
        
        if not dir_path.is_dir():
            logger.error(f"Kein Verzeichnis: {dir_path}")
            return
        
        logger.info(f"Starte Indexierung: {dir_path} (rekursiv: {directory_config['recursive']})")
        
        pattern = "**/*" if directory_config['recursive'] else "*"
        
        indexed = 0
        skipped = 0
        
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                if self.should_index_file(str(file_path), directory_config):
                    if self.index_file(str(file_path), directory_config['id']):
                        indexed += 1
                else:
                    skipped += 1
        
        logger.info(f"✓ Verzeichnis abgeschlossen: {dir_path} ({indexed} indexiert, {skipped} übersprungen)")
    
    def index_all_configured_directories(self):
        """Indexiert alle konfigurierten Verzeichnisse"""
        directories = self.indexing_config.get_directories(enabled_only=True)
        
        logger.info(f"Starte Indexierung von {len(directories)} Verzeichnissen")
        
        for directory in directories:
            if not directory.get('watch', False):  # Nur nicht-überwachte Verzeichnisse initial indexieren
                self.index_directory(directory)
    
    def index_urls_from_file(self, url_file: str):
        """Indexiert URLs aus einer Textdatei"""
        try:
            with open(url_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            logger.info(f"Gefunden: {len(urls)} URLs in {url_file}")
            
            from web_crawler import WebCrawler
            
            crawler = WebCrawler(
                opensearch_url=self.opensearch_url,
                username=os.getenv('OPENSEARCH_USER', 'admin'),
                password=os.getenv('OPENSEARCH_PASSWORD', 'Admin123!'),
                index_name='web_pages'
            )
            
            for url in urls:
                try:
                    logger.info(f"Verarbeite URL: {url}")
                    
                    if url.endswith('/*'):
                        base_url = url[:-2]
                        max_pages = int(os.getenv('MAX_PAGES_PER_SITE', '50'))
                        crawler.crawl_website(base_url, max_pages=max_pages)
                    else:
                        crawler.crawl_page(url)
                    
                except Exception as e:
                    logger.error(f"Fehler bei URL {url}: {e}")
            
            logger.info(f"URL-Import abgeschlossen: {len(urls)} URLs verarbeitet")
            
        except Exception as e:
            logger.error(f"Fehler beim Lesen von {url_file}: {e}")
    
    def search(self, query: str, size: int = 10, facets: List[str] = None) -> Dict[str, Any]:
        """Führt eine Volltextsuche mit Facetten aus"""
        
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "content^2", "ocr_text^2", "file_name^2", "metadata.*", "concepts.label"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "content": {},
                    "title": {},
                    "ocr_text": {},
                    "file_name": {}
                },
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"]
            },
            "aggs": {
                "document_types": {
                    "terms": {"field": "document_type", "size": 20}
                },
                "file_types": {
                    "terms": {"field": "file_type_category", "size": 20}
                },
                "mime_types": {
                    "terms": {"field": "mime_type", "size": 20}
                },
                "extensions": {
                    "terms": {"field": "file_extension", "size": 30}
                },
                "categories": {
                    "terms": {"field": "categories", "size": 30}
                },
                "has_ocr": {
                    "terms": {"field": "has_ocr"}
                },
                "source_directories": {
                    "terms": {"field": "source_directory", "size": 20}
                },
                "languages": {
                    "terms": {"field": "language", "size": 10}
                }
            },
            "size": size
        }
        
        return self.client.search(index=self.index_name, body=search_body)


class MultiDirectoryFileWatcher(FileSystemEventHandler):
    """Überwacht mehrere Verzeichnisse auf neue Dateien"""
    
    def __init__(self, indexer: OpenSearchIndexer, directory_config: Dict[str, Any]):
        self.indexer = indexer
        self.directory_config = directory_config
    
    def on_created(self, event):
        if not event.is_directory:
            if self.indexer.should_index_file(event.src_path, self.directory_config):
                logger.info(f"Neue Datei erkannt: {event.src_path}")
                time.sleep(1)
                self.indexer.index_file(event.src_path, self.directory_config['id'])
    
    def on_modified(self, event):
        if not event.is_directory:
            if self.indexer.should_index_file(event.src_path, self.directory_config):
                logger.info(f"Datei geändert: {event.src_path}")
                time.sleep(1)
                self.indexer.index_file(event.src_path, self.directory_config['id'])


def main():
    opensearch_url = os.getenv('OPENSEARCH_URL', 'https://localhost:9200')
    opensearch_user = os.getenv('OPENSEARCH_USER', 'admin')
    opensearch_password = os.getenv('OPENSEARCH_PASSWORD', 'Admin123!')
    tika_url = os.getenv('TIKA_URL', 'http://localhost:9998')
    
    # Indexer erstellen
    indexer = OpenSearchIndexer(
        opensearch_url=opensearch_url,
        username=opensearch_user,
        password=opensearch_password,
        tika_url=tika_url
    )
    
    # URLs aus Textdatei importieren
    url_file = '/data/urls.txt'
    if os.path.exists(url_file):
        logger.info(f"Importiere URLs aus {url_file}")
        indexer.index_urls_from_file(url_file)
    
    # Alle konfigurierten Verzeichnisse indexieren
    indexer.index_all_configured_directories()
    
    # Überwachte Verzeichnisse einrichten
    watched_directories = indexer.indexing_config.get_watched_directories()
    
    if watched_directories:
        logger.info(f"Starte Überwachung von {len(watched_directories)} Verzeichnissen")
        
        observer = Observer()
        
        for directory in watched_directories:
            dir_path = directory['path']
            if os.path.exists(dir_path):
                event_handler = MultiDirectoryFileWatcher(indexer, directory)
                observer.schedule(
                    event_handler, 
                    dir_path, 
                    recursive=directory.get('recursive', True)
                )
                logger.info(f"✓ Überwache: {dir_path}")
        
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    else:
        logger.info("Keine Verzeichnisse zur Überwachung konfiguriert")


if __name__ == '__main__':
    main()
