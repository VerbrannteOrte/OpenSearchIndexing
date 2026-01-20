#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FacetConfigManager:
    """Verwaltet die Konfiguration von Facetten für die Web-UI"""
    
    def __init__(self, config_file: str = "/config/facets.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.facets = []
        self.load_config()
    
    def load_config(self):
        """Lädt Facetten-Konfiguration aus JSON-Datei"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.facets = data.get('facets', [])
                logger.info(f"Facetten-Konfiguration geladen: {len(self.facets)} Facetten")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Konfiguration: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def save_config(self):
        """Speichert Facetten-Konfiguration"""
        try:
            config = {
                'facets': self.facets,
                'version': '1.0'
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Facetten-Konfiguration gespeichert: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
            return False
    
    def _create_default_config(self):
        """Erstellt Standard-Facetten-Konfiguration"""
        self.facets = [
            {
                'id': 'document_type',
                'label': 'Dokumenttyp',
                'icon': '📄',
                'field': 'document_type',
                'type': 'terms',
                'enabled': True,
                'order': 1,
                'size': 20,
                'source': 'field'
            },
            {
                'id': 'mime_type',
                'label': 'Dateityp',
                'icon': '📁',
                'field': 'mime_type',
                'type': 'terms',
                'enabled': True,
                'order': 2,
                'size': 20,
                'source': 'field',
                'display_map': {
                    'application/pdf': 'PDF',
                    'application/msword': 'Word',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word (DOCX)',
                    'application/vnd.ms-excel': 'Excel',
                    'text/html': 'HTML',
                    'text/plain': 'Text',
                    'image/jpeg': 'JPEG Bild',
                    'image/png': 'PNG Bild'
                }
            },
            {
                'id': 'categories',
                'label': 'Kategorien',
                'icon': '🏷️',
                'field': 'categories',
                'type': 'terms',
                'enabled': True,
                'order': 3,
                'size': 30,
                'source': 'field'
            },
            {
                'id': 'concepts',
                'label': 'Konzepte',
                'icon': '🧠',
                'field': 'concepts.label.keyword',
                'type': 'terms',
                'enabled': True,
                'order': 4,
                'size': 50,
                'source': 'nested',
                'nested_path': 'concepts'
            },
            {
                'id': 'language',
                'label': 'Sprache',
                'icon': '🌐',
                'field': 'language',
                'type': 'terms',
                'enabled': True,
                'order': 5,
                'size': 10,
                'source': 'field',
                'display_map': {
                    'de': 'Deutsch',
                    'en': 'Englisch',
                    'fr': 'Französisch',
                    'es': 'Spanisch',
                    'it': 'Italienisch'
                }
            }
        ]
        
        self.save_config()
    
    def add_facet(self, facet_config: Dict[str, Any]) -> bool:
        """Fügt eine neue Facette hinzu"""
        # Validierung
        required_fields = ['id', 'label', 'field', 'type']
        for field in required_fields:
            if field not in facet_config:
                logger.error(f"Pflichtfeld fehlt: {field}")
                return False
        
        # Prüfen ob ID bereits existiert
        if any(f['id'] == facet_config['id'] for f in self.facets):
            logger.error(f"Facette mit ID '{facet_config['id']}' existiert bereits")
            return False
        
        # Defaults setzen
        facet_config.setdefault('enabled', True)
        facet_config.setdefault('order', len(self.facets) + 1)
        facet_config.setdefault('size', 20)
        facet_config.setdefault('source', 'field')
        facet_config.setdefault('icon', '📊')
        
        self.facets.append(facet_config)
        self.save_config()
        
        logger.info(f"Facette hinzugefügt: {facet_config['label']}")
        return True
    
    def remove_facet(self, facet_id: str) -> bool:
        """Entfernt eine Facette"""
        original_length = len(self.facets)
        self.facets = [f for f in self.facets if f['id'] != facet_id]
        
        if len(self.facets) < original_length:
            self.save_config()
            logger.info(f"Facette entfernt: {facet_id}")
            return True
        
        logger.warning(f"Facette nicht gefunden: {facet_id}")
        return False
    
    def update_facet(self, facet_id: str, updates: Dict[str, Any]) -> bool:
        """Aktualisiert eine Facette"""
        for facet in self.facets:
            if facet['id'] == facet_id:
                facet.update(updates)
                self.save_config()
                logger.info(f"Facette aktualisiert: {facet_id}")
                return True
        
        logger.warning(f"Facette nicht gefunden: {facet_id}")
        return False
    
    def toggle_facet(self, facet_id: str, enabled: bool) -> bool:
        """Aktiviert/Deaktiviert eine Facette"""
        return self.update_facet(facet_id, {'enabled': enabled})
    
    def reorder_facets(self, facet_ids: List[str]) -> bool:
        """Ändert die Reihenfolge der Facetten"""
        # Neue Reihenfolge erstellen
        reordered = []
        for order, facet_id in enumerate(facet_ids, start=1):
            facet = next((f for f in self.facets if f['id'] == facet_id), None)
            if facet:
                facet['order'] = order
                reordered.append(facet)
        
        if len(reordered) == len(self.facets):
            self.facets = sorted(reordered, key=lambda x: x['order'])
            self.save_config()
            logger.info("Facetten-Reihenfolge aktualisiert")
            return True
        
        logger.error("Fehler beim Umsortieren - nicht alle Facetten gefunden")
        return False
    
    def get_facets(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """Gibt Facetten-Konfiguration zurück"""
        facets = self.facets if not enabled_only else [f for f in self.facets if f.get('enabled', True)]
        return sorted(facets, key=lambda x: x.get('order', 999))
    
    def get_facet(self, facet_id: str) -> Optional[Dict[str, Any]]:
        """Gibt eine spezifische Facette zurück"""
        return next((f for f in self.facets if f['id'] == facet_id), None)
    
    def create_ontology_facet(
        self, 
        ontology_name: str, 
        label: str,
        field_name: Optional[str] = None,
        icon: str = '🏷️'
    ) -> bool:
        """Erstellt eine Facette aus einer Ontologie"""
        facet_id = f"ontology_{ontology_name.lower().replace(' ', '_')}"
        
        if field_name is None:
            field_name = f"ontology_{ontology_name.lower().replace(' ', '_')}"
        
        facet_config = {
            'id': facet_id,
            'label': label,
            'icon': icon,
            'field': field_name,
            'type': 'terms',
            'enabled': True,
            'order': len(self.facets) + 1,
            'size': 50,
            'source': 'ontology',
            'ontology_name': ontology_name
        }
        
        return self.add_facet(facet_config)
    
    def generate_opensearch_aggregation(self, facet: Dict[str, Any]) -> Dict[str, Any]:
        """Generiert OpenSearch Aggregation aus Facetten-Config"""
        agg = {}
        
        if facet['source'] == 'nested':
            # Nested Aggregation
            agg = {
                'nested': {
                    'path': facet['nested_path']
                },
                'aggs': {
                    f"{facet['id']}_terms": {
                        'terms': {
                            'field': facet['field'],
                            'size': facet.get('size', 20)
                        }
                    }
                }
            }
        else:
            # Standard Terms Aggregation
            agg = {
                'terms': {
                    'field': facet['field'],
                    'size': facet.get('size', 20)
                }
            }
        
        return agg
    
    def export_config(self) -> Dict[str, Any]:
        """Exportiert Konfiguration als Dictionary"""
        return {
            'facets': self.facets,
            'count': len(self.facets),
            'enabled_count': len([f for f in self.facets if f.get('enabled', True)])
        }


def create_profession_taxonomy():
    """Erstellt eine Beispiel-Taxonomie für Berufe"""
    taxonomy = {
        "id": "professions",
        "label": "Berufe",
        "children": [
            {
                "id": "it",
                "label": "IT und Technologie",
                "children": [
                    {"id": "developer", "label": "Entwickler", "aliases": ["Programmierer", "Software Engineer", "Developer"]},
                    {"id": "data_scientist", "label": "Data Scientist", "aliases": ["Datenwissenschaftler", "ML Engineer"]},
                    {"id": "devops", "label": "DevOps Engineer", "aliases": ["System Administrator", "SysAdmin"]},
                    {"id": "designer", "label": "UX/UI Designer", "aliases": ["Designer", "Webdesigner"]}
                ]
            },
            {
                "id": "business",
                "label": "Business und Management",
                "children": [
                    {"id": "manager", "label": "Manager", "aliases": ["Geschäftsführer", "CEO", "Director"]},
                    {"id": "consultant", "label": "Berater", "aliases": ["Consultant", "Business Analyst"]},
                    {"id": "sales", "label": "Vertrieb", "aliases": ["Sales", "Account Manager", "Verkäufer"]},
                    {"id": "marketing", "label": "Marketing Manager", "aliases": ["Marketing", "CMO"]}
                ]
            },
            {
                "id": "legal",
                "label": "Recht und Finanzen",
                "children": [
                    {"id": "lawyer", "label": "Rechtsanwalt", "aliases": ["Anwalt", "Jurist", "Lawyer"]},
                    {"id": "accountant", "label": "Buchhalter", "aliases": ["Accountant", "Steuerberater"]},
                    {"id": "auditor", "label": "Wirtschaftsprüfer", "aliases": ["Auditor", "Prüfer"]}
                ]
            },
            {
                "id": "healthcare",
                "label": "Gesundheitswesen",
                "children": [
                    {"id": "doctor", "label": "Arzt", "aliases": ["Doktor", "Mediziner", "Doctor", "Physician"]},
                    {"id": "nurse", "label": "Krankenpfleger", "aliases": ["Pfleger", "Nurse"]},
                    {"id": "pharmacist", "label": "Apotheker", "aliases": ["Pharmacist", "Pharmazeut"]}
                ]
            },
            {
                "id": "education",
                "label": "Bildung",
                "children": [
                    {"id": "teacher", "label": "Lehrer", "aliases": ["Teacher", "Dozent", "Professor"]},
                    {"id": "researcher", "label": "Forscher", "aliases": ["Researcher", "Wissenschaftler", "Scientist"]}
                ]
            },
            {
                "id": "creative",
                "label": "Kreative Berufe",
                "children": [
                    {"id": "journalist", "label": "Journalist", "aliases": ["Reporter", "Redakteur"]},
                    {"id": "photographer", "label": "Fotograf", "aliases": ["Photographer"]},
                    {"id": "videographer", "label": "Videograf", "aliases": ["Video Producer", "Kameramann"]}
                ]
            }
        ]
    }
    
    output_dir = Path("/ontologies")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "professions.json", 'w', encoding='utf-8') as f:
        json.dump(taxonomy, f, indent=2, ensure_ascii=False)
    
    logger.info("Berufe-Taxonomie erstellt: /ontologies/professions.json")
    return taxonomy


if __name__ == '__main__':
    # Beispiel-Verwendung
    manager = FacetConfigManager()
    
    # Berufe-Taxonomie erstellen
    create_profession_taxonomy()
    
    # Facette für Berufe hinzufügen
    manager.create_ontology_facet(
        ontology_name='professions',
        label='Berufe',
        field_name='professions',
        icon='👔'
    )
    
    # Alle Facetten anzeigen
    print("\nKonfigurierte Facetten:")
    for facet in manager.get_facets():
        print(f"  [{facet['order']}] {facet['icon']} {facet['label']} ({'aktiv' if facet['enabled'] else 'inaktiv'})")
