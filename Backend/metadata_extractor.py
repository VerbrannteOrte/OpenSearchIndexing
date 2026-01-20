#!/usr/bin/env python3
import os
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import mimetypes

from PIL import Image
from PIL.ExifTags import TAGS
import PyPDF2
import olefile
import hashlib

try:
    import exifread
    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False
    logging.warning("exifread nicht verfügbar")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Erweiterte Metadaten-Extraktion für verschiedene Dateiformate"""
    
    def __init__(self):
        self.extractors = {
            '.pdf': self.extract_pdf_metadata,
            '.jpg': self.extract_image_metadata,
            '.jpeg': self.extract_image_metadata,
            '.png': self.extract_image_metadata,
            '.tif': self.extract_image_metadata,
            '.tiff': self.extract_image_metadata,
            '.doc': self.extract_office_metadata,
            '.docx': self.extract_office_metadata,
            '.xls': self.extract_office_metadata,
            '.xlsx': self.extract_office_metadata,
            '.ppt': self.extract_office_metadata,
            '.pptx': self.extract_office_metadata,
        }
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Hauptmethode zur Metadaten-Extraktion"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        metadata = {
            'file_name': path.name,
            'file_extension': extension,
            'file_size': path.stat().st_size,
            'created_date': datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
            'modified_date': datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            'mime_type': mimetypes.guess_type(file_path)[0],
        }
        
        # Format-spezifische Extraktion
        if extension in self.extractors:
            try:
                format_metadata = self.extractors[extension](file_path)
                metadata.update(format_metadata)
            except Exception as e:
                logger.error(f"Metadaten-Extraktion fehlgeschlagen für {file_path}: {e}")
                metadata['extraction_error'] = str(e)
        
        # Erweiterte Analyse
        metadata.update(self.analyze_filename(path.name))
        
        return metadata
    
    def extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extrahiert PDF-spezifische Metadaten"""
        metadata = {}
        
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Seitenzahl
                metadata['page_count'] = len(pdf_reader.pages)
                
                # PDF-Informationen
                if pdf_reader.metadata:
                    info = pdf_reader.metadata
                    
                    metadata['pdf_title'] = info.get('/Title', '')
                    metadata['pdf_author'] = info.get('/Author', '')
                    metadata['pdf_subject'] = info.get('/Subject', '')
                    metadata['pdf_creator'] = info.get('/Creator', '')
                    metadata['pdf_producer'] = info.get('/Producer', '')
                    metadata['pdf_keywords'] = info.get('/Keywords', '')
                    
                    # Datum
                    if '/CreationDate' in info:
                        metadata['pdf_creation_date'] = self.parse_pdf_date(info['/CreationDate'])
                    if '/ModDate' in info:
                        metadata['pdf_modification_date'] = self.parse_pdf_date(info['/ModDate'])
                
                # Verschlüsselung
                metadata['pdf_encrypted'] = pdf_reader.is_encrypted
                
                # Erste Seite analysieren für OCR-Entscheidung
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()
                metadata['first_page_text_length'] = len(text)
                metadata['is_likely_scanned'] = len(text.strip()) < 100
        
        except Exception as e:
            logger.error(f"PDF Metadaten-Fehler: {e}")
            metadata['pdf_error'] = str(e)
        
        return metadata
    
    def extract_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extrahiert EXIF und andere Bild-Metadaten"""
        metadata = {}
        
        try:
            with Image.open(file_path) as img:
                # Basis-Informationen
                metadata['image_width'] = img.width
                metadata['image_height'] = img.height
                metadata['image_format'] = img.format
                metadata['image_mode'] = img.mode
                metadata['image_megapixels'] = round((img.width * img.height) / 1000000, 2)
                
                # DPI
                if 'dpi' in img.info:
                    metadata['image_dpi'] = img.info['dpi']
                
                # EXIF Daten
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        
                        # Wichtige EXIF Tags
                        if tag == 'DateTime':
                            metadata['exif_datetime'] = str(value)
                        elif tag == 'Make':
                            metadata['camera_make'] = str(value)
                        elif tag == 'Model':
                            metadata['camera_model'] = str(value)
                        elif tag == 'Software':
                            metadata['software'] = str(value)
                        elif tag == 'Artist':
                            metadata['artist'] = str(value)
                        elif tag == 'Copyright':
                            metadata['copyright'] = str(value)
                        elif tag == 'ImageDescription':
                            metadata['image_description'] = str(value)
                
                # Erweiterte EXIF mit exifread
                if EXIFREAD_AVAILABLE:
                    with open(file_path, 'rb') as f:
                        tags = exifread.process_file(f, details=False)
                        
                        if 'EXIF DateTimeOriginal' in tags:
                            metadata['photo_taken_date'] = str(tags['EXIF DateTimeOriginal'])
                        
                        if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                            metadata['has_gps'] = True
        
        except Exception as e:
            logger.error(f"Bild Metadaten-Fehler: {e}")
            metadata['image_error'] = str(e)
        
        return metadata
    
    def extract_office_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extrahiert Office-Dokument Metadaten"""
        metadata = {}
        
        try:
            # Für alte Office-Formate (.doc, .xls, .ppt)
            if olefile.isOleFile(file_path):
                ole = olefile.OleFileIO(file_path)
                
                meta = ole.get_metadata()
                
                metadata['office_title'] = meta.title or ''
                metadata['office_author'] = meta.author or ''
                metadata['office_subject'] = meta.subject or ''
                metadata['office_keywords'] = meta.keywords or ''
                metadata['office_comments'] = meta.comments or ''
                metadata['office_created'] = str(meta.create_time) if meta.create_time else ''
                metadata['office_modified'] = str(meta.modify_time) if meta.modify_time else ''
                metadata['office_last_author'] = meta.last_saved_by or ''
                metadata['office_revision'] = meta.revision_number or ''
                metadata['office_application'] = meta.creating_application or ''
                
                ole.close()
            
            # Für neue Office-Formate (.docx, .xlsx, .pptx)
            elif file_path.endswith(('.docx', '.xlsx', '.pptx')):
                # Diese sind ZIP-Archive mit XML-Metadaten
                import zipfile
                import xml.etree.ElementTree as ET
                
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    # Core Properties
                    try:
                        core_xml = zip_ref.read('docProps/core.xml')
                        root = ET.fromstring(core_xml)
                        
                        # Namespaces
                        ns = {
                            'dc': 'http://purl.org/dc/elements/1.1/',
                            'dcterms': 'http://purl.org/dc/terms/',
                            'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
                        }
                        
                        title = root.find('.//dc:title', ns)
                        if title is not None and title.text:
                            metadata['office_title'] = title.text
                        
                        creator = root.find('.//dc:creator', ns)
                        if creator is not None and creator.text:
                            metadata['office_author'] = creator.text
                        
                        subject = root.find('.//dc:subject', ns)
                        if subject is not None and subject.text:
                            metadata['office_subject'] = subject.text
                        
                        keywords = root.find('.//cp:keywords', ns)
                        if keywords is not None and keywords.text:
                            metadata['office_keywords'] = keywords.text
                    
                    except KeyError:
                        pass
                    
                    # App Properties für Seitenzahl etc.
                    try:
                        app_xml = zip_ref.read('docProps/app.xml')
                        root = ET.fromstring(app_xml)
                        
                        pages = root.find('.//{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Pages')
                        if pages is not None and pages.text:
                            metadata['page_count'] = int(pages.text)
                        
                        words = root.find('.//{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Words')
                        if words is not None and words.text:
                            metadata['word_count'] = int(words.text)
                    
                    except KeyError:
                        pass
        
        except Exception as e:
            logger.error(f"Office Metadaten-Fehler: {e}")
            metadata['office_error'] = str(e)
        
        return metadata
    
    def analyze_filename(self, filename: str) -> Dict[str, Any]:
        """Analysiert Dateinamen für zusätzliche Informationen"""
        metadata = {}
        
        # Datum im Dateinamen (YYYY-MM-DD oder DD.MM.YYYY)
        date_patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',
            r'(\d{2})\.(\d{2})\.(\d{4})',
            r'(\d{8})',  # YYYYMMDD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                metadata['filename_contains_date'] = True
                metadata['filename_date'] = match.group(0)
                break
        
        # Versionsnummer (v1, v2, version1, etc.)
        version_match = re.search(r'v(\d+)', filename, re.IGNORECASE)
        if version_match:
            metadata['filename_version'] = version_match.group(1)
        
        # Status-Keywords
        status_keywords = ['final', 'draft', 'entwurf', 'vorlage', 'template', 'korrektur']
        for keyword in status_keywords:
            if keyword in filename.lower():
                metadata['filename_status'] = keyword
                break
        
        # Sprach-Kürzel (DE, EN, FR, etc.)
        lang_match = re.search(r'[_-](DE|EN|FR|ES|IT)[_.-]', filename, re.IGNORECASE)
        if lang_match:
            metadata['filename_language'] = lang_match.group(1).upper()
        
        return metadata
    
    def parse_pdf_date(self, pdf_date: str) -> str:
        """Parst PDF-Datumsformat"""
        # PDF Datum: D:YYYYMMDDHHmmSSOHH'mm'
        try:
            if pdf_date.startswith('D:'):
                pdf_date = pdf_date[2:]
            
            # Extrahiere YYYY-MM-DD HH:mm:SS
            year = pdf_date[0:4]
            month = pdf_date[4:6]
            day = pdf_date[6:8]
            hour = pdf_date[8:10] if len(pdf_date) > 8 else '00'
            minute = pdf_date[10:12] if len(pdf_date) > 10 else '00'
            second = pdf_date[12:14] if len(pdf_date) > 12 else '00'
            
            return f"{year}-{month}-{day} {hour}:{minute}:{second}"
        except:
            return pdf_date
    
    def extract_text_statistics(self, text: str) -> Dict[str, Any]:
        """Analysiert Text-Statistiken"""
        return {
            'text_length': len(text),
            'word_count': len(text.split()),
            'line_count': len(text.split('\n')),
            'character_count': len(text),
            'paragraph_count': len([p for p in text.split('\n\n') if p.strip()]),
            'average_word_length': sum(len(word) for word in text.split()) / len(text.split()) if text.split() else 0,
        }
    
    def detect_language_advanced(self, text: str) -> Dict[str, Any]:
        """Erweiterte Spracherkennung"""
        # Einfache Heuristik basierend auf häufigen Wörtern
        german_indicators = ['der', 'die', 'das', 'und', 'ist', 'von', 'zu', 'den', 'mit', 'für']
        english_indicators = ['the', 'and', 'is', 'of', 'to', 'in', 'for', 'with', 'on', 'that']
        
        text_lower = text.lower()
        words = text_lower.split()
        
        german_count = sum(1 for word in german_indicators if word in words)
        english_count = sum(1 for word in english_indicators if word in words)
        
        if german_count > english_count:
            return {'language': 'de', 'confidence': 'high' if german_count > 5 else 'medium'}
        elif english_count > german_count:
            return {'language': 'en', 'confidence': 'high' if english_count > 5 else 'medium'}
        else:
            return {'language': 'unknown', 'confidence': 'low'}


if __name__ == '__main__':
    # Test
    extractor = MetadataExtractor()
    
    test_file = '/data/test.pdf'
    if os.path.exists(test_file):
        metadata = extractor.extract_metadata(test_file)
        
        print("Extrahierte Metadaten:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
