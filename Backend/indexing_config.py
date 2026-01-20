#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IndexingConfig:
    """Verwaltet Konfiguration für Indexierungs-Verzeichnisse"""
    
    def __init__(self, config_file: str = "/config/indexing.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.directories = []
        self.supported_extensions = {
            # Office-Formate
            'libreoffice': ['.odt', '.ods', '.odp', '.odg', '.odf'],
            'microsoft_office': [
                '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.docm', '.xlsm', '.pptm'
            ],
            # Bilder (mit OCR)
            'images': ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.gif'],
            # PDFs (mit OCR)
            'pdf': ['.pdf'],
            # Andere Textformate
            'text': ['.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm'],
            # E-Mail
            'email': ['.eml', '.msg'],
            # Archive
            'archives': ['.zip', '.tar', '.gz', '.7z']
        }
        
        self.load_config()
    
    def load_config(self):
        """Lädt Konfiguration aus JSON-Datei"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.directories = data.get('directories', [])
                logger.info(f"Indexierungs-Konfiguration geladen: {len(self.directories)} Verzeichnisse")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Konfiguration: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def save_config(self):
        """Speichert Konfiguration"""
        try:
            config = {
                'directories': self.directories,
                'version': '1.0'
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Konfiguration gespeichert: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
            return False
    
    def _create_default_config(self):
        """Erstellt Standard-Konfiguration"""
        self.directories = [
            {
                'id': 'data',
                'path': '/data',
                'enabled': True,
                'recursive': True,
                'watch': False,
                'description': 'Haupt-Datenverzeichnis',
                'file_types': ['all'],
                'exclude_patterns': ['*.tmp', '*.bak', '.git/*', '__pycache__/*']
            },
            {
                'id': 'watch',
                'path': '/watch',
                'enabled': True,
                'recursive': True,
                'watch': True,
                'description': 'Überwachtes Verzeichnis für neue Dateien',
                'file_types': ['all'],
                'exclude_patterns': []
            }
        ]
        
        self.save_config()
    
    def add_directory(self, directory_config: Dict[str, Any]) -> bool:
        """Fügt ein Verzeichnis zur Konfiguration hinzu"""
        # Validierung
        if 'id' not in directory_config or 'path' not in directory_config:
            logger.error("'id' und 'path' sind erforderlich")
            return False
        
        # Prüfen ob ID bereits existiert
        if any(d['id'] == directory_config['id'] for d in self.directories):
            logger.error(f"Verzeichnis mit ID '{directory_config['id']}' existiert bereits")
            return False
        
        # Defaults setzen
        directory_config.setdefault('enabled', True)
        directory_config.setdefault('recursive', True)
        directory_config.setdefault('watch', False)
        directory_config.setdefault('file_types', ['all'])
        directory_config.setdefault('exclude_patterns', [])
        directory_config.setdefault('description', '')
        
        self.directories.append(directory_config)
        self.save_config()
        
        logger.info(f"Verzeichnis hinzugefügt: {directory_config['path']}")
        return True
    
    def remove_directory(self, directory_id: str) -> bool:
        """Entfernt ein Verzeichnis aus der Konfiguration"""
        original_length = len(self.directories)
        self.directories = [d for d in self.directories if d['id'] != directory_id]
        
        if len(self.directories) < original_length:
            self.save_config()
            logger.info(f"Verzeichnis entfernt: {directory_id}")
            return True
        
        logger.warning(f"Verzeichnis nicht gefunden: {directory_id}")
        return False
    
    def update_directory(self, directory_id: str, updates: Dict[str, Any]) -> bool:
        """Aktualisiert ein Verzeichnis"""
        for directory in self.directories:
            if directory['id'] == directory_id:
                directory.update(updates)
                self.save_config()
                logger.info(f"Verzeichnis aktualisiert: {directory_id}")
                return True
        
        logger.warning(f"Verzeichnis nicht gefunden: {directory_id}")
        return False
    
    def get_directories(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """Gibt Verzeichnisse zurück"""
        if enabled_only:
            return [d for d in self.directories if d.get('enabled', True)]
        return self.directories
    
    def get_watched_directories(self) -> List[Dict[str, Any]]:
        """Gibt Verzeichnisse zurück, die überwacht werden sollen"""
        return [d for d in self.directories if d.get('watch', False) and d.get('enabled', True)]
    
    def is_file_allowed(self, file_path: str, directory_config: Dict[str, Any]) -> bool:
        """Prüft ob eine Datei indexiert werden soll"""
        path = Path(file_path)
        
        # Ausschlussmuster prüfen
        for pattern in directory_config.get('exclude_patterns', []):
            if path.match(pattern):
                return False
        
        # Dateityp prüfen
        file_types = directory_config.get('file_types', ['all'])
        
        if 'all' in file_types:
            return True
        
        extension = path.suffix.lower()
        
        for file_type in file_types:
            if file_type in self.supported_extensions:
                if extension in self.supported_extensions[file_type]:
                    return True
        
        return False
    
    def get_all_supported_extensions(self) -> List[str]:
        """Gibt alle unterstützten Dateierweiterungen zurück"""
        extensions = []
        for ext_list in self.supported_extensions.values():
            extensions.extend(ext_list)
        return list(set(extensions))
    
    def export_config(self) -> Dict[str, Any]:
        """Exportiert Konfiguration"""
        return {
            'directories': self.directories,
            'supported_extensions': self.supported_extensions,
            'count': len(self.directories)
        }


def create_example_config():
    """Erstellt eine Beispiel-Konfiguration"""
    config = IndexingConfig()
    
    # Beispiel: Mehrere Verzeichnisse
    config.add_directory({
        'id': 'documents',
        'path': '/mnt/documents',
        'enabled': True,
        'recursive': True,
        'watch': False,
        'description': 'Firmen-Dokumente',
        'file_types': ['microsoft_office', 'libreoffice', 'pdf'],
        'exclude_patterns': ['*/temp/*', '*.tmp']
    })
    
    config.add_directory({
        'id': 'scans',
        'path': '/mnt/scans',
        'enabled': True,
        'recursive': True,
        'watch': True,
        'description': 'Gescannte Dokumente (mit OCR)',
        'file_types': ['images', 'pdf'],
        'exclude_patterns': []
    })
    
    config.add_directory({
        'id': 'archive',
        'path': '/mnt/archive',
        'enabled': False,
        'recursive': True,
        'watch': False,
        'description': 'Archiv (deaktiviert)',
        'file_types': ['all'],
        'exclude_patterns': []
    })
    
    logger.info("Beispiel-Konfiguration erstellt")


if __name__ == '__main__':
    create_example_config()
    
    config = IndexingConfig()
    
    # Konfiguration anzeigen
    print("\nKonfigurierte Verzeichnisse:")
    for directory in config.get_directories():
        print(f"  [{directory['id']}] {directory['path']}")
        print(f"    Rekursiv: {directory['recursive']}")
        print(f"    Überwacht: {directory['watch']}")
        print(f"    Dateitypen: {', '.join(directory['file_types'])}")
        print()
    
    print(f"\nUnterstützte Erweiterungen: {len(config.get_all_supported_extensions())}")
