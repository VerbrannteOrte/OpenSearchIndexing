#!/usr/bin/env python3
import json
import logging
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import SKOS, RDF, RDFS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OntologyManager:
    """Verwaltet SKOS Ontologien und Taxonomien für Facettierung"""
    
    def __init__(self, ontology_dir: str = "/ontologies"):
        self.ontology_dir = Path(ontology_dir)
        self.ontology_dir.mkdir(exist_ok=True)
        
        self.graphs = {}  # Ontologie-Name -> RDF Graph
        self.concept_schemes = {}  # Scheme URI -> Concept URIs
        self.broader_relations = {}  # Concept -> Parent Concepts
        self.narrower_relations = {}  # Concept -> Child Concepts
        self.concept_labels = {}  # Concept URI -> Label
        self.concept_alts = {}  # Concept URI -> Alternative Labels
        
        # SKOS Namespace
        self.SKOS = SKOS
        
        self._load_ontologies()
    
    def _load_ontologies(self):
        """Lädt alle Ontologie-Dateien aus dem Verzeichnis"""
        for file_path in self.ontology_dir.glob("*.rdf"):
            self.load_ontology(str(file_path))
        
        for file_path in self.ontology_dir.glob("*.ttl"):
            self.load_ontology(str(file_path))
        
        for file_path in self.ontology_dir.glob("*.json"):
            self.load_json_taxonomy(str(file_path))
    
    def load_ontology(self, file_path: str, format: str = None) -> bool:
        """Lädt eine SKOS Ontologie (RDF/Turtle)"""
        try:
            g = Graph()
            
            # Format automatisch erkennen
            if format is None:
                if file_path.endswith('.ttl'):
                    format = 'turtle'
                elif file_path.endswith('.rdf') or file_path.endswith('.xml'):
                    format = 'xml'
                else:
                    format = 'turtle'
            
            g.parse(file_path, format=format)
            
            ontology_name = Path(file_path).stem
            self.graphs[ontology_name] = g
            
            logger.info(f"Ontologie geladen: {ontology_name} ({len(g)} Triples)")
            
            # Konzepte extrahieren
            self._extract_concepts(ontology_name, g)
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Laden von {file_path}: {e}")
            return False
    
    def _extract_concepts(self, ontology_name: str, graph: Graph):
        """Extrahiert Konzepte und Beziehungen aus RDF Graph"""
        
        # Alle SKOS Concepts finden
        for concept in graph.subjects(RDF.type, SKOS.Concept):
            concept_uri = str(concept)
            
            # Labels extrahieren
            for label in graph.objects(concept, SKOS.prefLabel):
                self.concept_labels[concept_uri] = str(label)
            
            # Alternative Labels
            alt_labels = []
            for alt in graph.objects(concept, SKOS.altLabel):
                alt_labels.append(str(alt))
            if alt_labels:
                self.concept_alts[concept_uri] = alt_labels
            
            # Broader (Parent) Relations
            broader = []
            for parent in graph.objects(concept, SKOS.broader):
                broader.append(str(parent))
            if broader:
                self.broader_relations[concept_uri] = broader
            
            # Narrower (Child) Relations
            narrower = []
            for child in graph.objects(concept, SKOS.narrower):
                narrower.append(str(child))
            if narrower:
                self.narrower_relations[concept_uri] = narrower
        
        # Concept Schemes extrahieren
        for scheme in graph.subjects(RDF.type, SKOS.ConceptScheme):
            scheme_uri = str(scheme)
            concepts = []
            
            for concept in graph.subjects(SKOS.inScheme, scheme):
                concepts.append(str(concept))
            
            self.concept_schemes[scheme_uri] = concepts
            
            # Scheme Label
            for label in graph.objects(scheme, SKOS.prefLabel):
                logger.info(f"Concept Scheme: {label} mit {len(concepts)} Konzepten")
    
    def load_json_taxonomy(self, file_path: str) -> bool:
        """Lädt eine einfache JSON-Taxonomie"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                taxonomy = json.load(f)
            
            ontology_name = Path(file_path).stem
            
            # JSON zu internem Format konvertieren
            self._process_json_taxonomy(ontology_name, taxonomy)
            
            logger.info(f"JSON-Taxonomie geladen: {ontology_name}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Laden von {file_path}: {e}")
            return False
    
    def _process_json_taxonomy(self, name: str, taxonomy: Dict):
        """Verarbeitet JSON-Taxonomie rekursiv"""
        
        def process_node(node: Dict, parent_uri: Optional[str] = None):
            concept_uri = f"urn:{name}:{node.get('id', node.get('label', '').replace(' ', '_'))}"
            label = node.get('label', node.get('name', ''))
            
            self.concept_labels[concept_uri] = label
            
            # Alternative Labels
            if 'aliases' in node:
                self.concept_alts[concept_uri] = node['aliases']
            
            # Parent-Beziehung
            if parent_uri:
                if concept_uri not in self.broader_relations:
                    self.broader_relations[concept_uri] = []
                self.broader_relations[concept_uri].append(parent_uri)
                
                if parent_uri not in self.narrower_relations:
                    self.narrower_relations[parent_uri] = []
                self.narrower_relations[parent_uri].append(concept_uri)
            
            # Kinder rekursiv verarbeiten
            if 'children' in node:
                for child in node['children']:
                    process_node(child, concept_uri)
        
        # Hauptknoten verarbeiten
        if isinstance(taxonomy, list):
            for item in taxonomy:
                process_node(item)
        elif isinstance(taxonomy, dict):
            process_node(taxonomy)
    
    def find_concepts(self, text: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Findet passende Konzepte im Text"""
        text_lower = text.lower()
        matches = []
        
        # Exakte Label-Matches
        for concept_uri, label in self.concept_labels.items():
            if label.lower() in text_lower:
                matches.append({
                    'uri': concept_uri,
                    'label': label,
                    'type': 'exact',
                    'confidence': 1.0
                })
        
        # Alternative Label-Matches
        for concept_uri, alts in self.concept_alts.items():
            for alt in alts:
                if alt.lower() in text_lower:
                    label = self.concept_labels.get(concept_uri, alt)
                    matches.append({
                        'uri': concept_uri,
                        'label': label,
                        'type': 'alternative',
                        'confidence': 0.9
                    })
        
        return matches
    
    def expand_query(self, concept_uri: str, include_broader: bool = True, 
                     include_narrower: bool = True) -> List[str]:
        """Erweitert eine Suchanfrage um verwandte Konzepte"""
        expanded = [concept_uri]
        
        # Breitere Konzepte einbeziehen
        if include_broader and concept_uri in self.broader_relations:
            expanded.extend(self.broader_relations[concept_uri])
        
        # Engere Konzepte einbeziehen
        if include_narrower and concept_uri in self.narrower_relations:
            expanded.extend(self.narrower_relations[concept_uri])
        
        return expanded
    
    def get_concept_hierarchy(self, concept_uri: str) -> Dict[str, Any]:
        """Gibt die komplette Hierarchie eines Konzepts zurück"""
        hierarchy = {
            'uri': concept_uri,
            'label': self.concept_labels.get(concept_uri, ''),
            'broader': [],
            'narrower': []
        }
        
        # Parents
        if concept_uri in self.broader_relations:
            for parent_uri in self.broader_relations[concept_uri]:
                hierarchy['broader'].append({
                    'uri': parent_uri,
                    'label': self.concept_labels.get(parent_uri, '')
                })
        
        # Children
        if concept_uri in self.narrower_relations:
            for child_uri in self.narrower_relations[concept_uri]:
                hierarchy['narrower'].append({
                    'uri': child_uri,
                    'label': self.concept_labels.get(child_uri, '')
                })
        
        return hierarchy
    
    def get_all_concepts(self) -> List[Dict[str, str]]:
        """Gibt alle Konzepte zurück"""
        concepts = []
        for uri, label in self.concept_labels.items():
            concepts.append({
                'uri': uri,
                'label': label
            })
        return concepts
    
    def create_facet_config(self) -> Dict[str, Any]:
        """Erstellt Konfiguration für OpenSearch Facetten"""
        facets = {}
        
        for scheme_uri, concepts in self.concept_schemes.items():
            scheme_label = self.concept_labels.get(scheme_uri, 'Unknown')
            
            facets[scheme_label] = {
                'field': f'concepts.{scheme_label.lower().replace(" ", "_")}',
                'values': [
                    {
                        'uri': concept,
                        'label': self.concept_labels.get(concept, concept)
                    }
                    for concept in concepts
                ]
            }
        
        return facets
    
    def save_taxonomy_json(self, output_path: str):
        """Speichert Taxonomie als JSON für Frontend"""
        taxonomy = {
            'concepts': [],
            'relations': {
                'broader': self.broader_relations,
                'narrower': self.narrower_relations
            }
        }
        
        for uri, label in self.concept_labels.items():
            concept = {
                'uri': uri,
                'label': label
            }
            
            if uri in self.concept_alts:
                concept['alternatives'] = self.concept_alts[uri]
            
            taxonomy['concepts'].append(concept)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(taxonomy, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Taxonomie gespeichert: {output_path}")


def create_example_taxonomy():
    """Erstellt eine Beispiel-Taxonomie für Dokumente"""
    taxonomy = {
        "id": "document_types",
        "label": "Dokumenttypen",
        "children": [
            {
                "id": "contracts",
                "label": "Verträge",
                "aliases": ["Vertrag", "Contract", "Agreement"],
                "children": [
                    {"id": "employment_contract", "label": "Arbeitsvertrag"},
                    {"id": "service_contract", "label": "Dienstleistungsvertrag"},
                    {"id": "rental_contract", "label": "Mietvertrag"}
                ]
            },
            {
                "id": "invoices",
                "label": "Rechnungen",
                "aliases": ["Rechnung", "Invoice", "Bill"],
                "children": [
                    {"id": "incoming_invoice", "label": "Eingangsrechnung"},
                    {"id": "outgoing_invoice", "label": "Ausgangsrechnung"}
                ]
            },
            {
                "id": "reports",
                "label": "Berichte",
                "aliases": ["Bericht", "Report"],
                "children": [
                    {"id": "annual_report", "label": "Jahresbericht"},
                    {"id": "quarterly_report", "label": "Quartalsbericht"},
                    {"id": "project_report", "label": "Projektbericht"}
                ]
            },
            {
                "id": "correspondence",
                "label": "Korrespondenz",
                "aliases": ["E-Mail", "Brief", "Letter"],
                "children": [
                    {"id": "email", "label": "E-Mail"},
                    {"id": "letter", "label": "Brief"},
                    {"id": "memo", "label": "Memo"}
                ]
            }
        ]
    }
    
    # Als JSON speichern
    output_dir = Path("/ontologies")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "document_types.json", 'w', encoding='utf-8') as f:
        json.dump(taxonomy, f, indent=2, ensure_ascii=False)
    
    logger.info("Beispiel-Taxonomie erstellt: /ontologies/document_types.json")


if __name__ == '__main__':
    # Beispiel-Taxonomie erstellen
    create_example_taxonomy()
    
    # Ontologie-Manager testen
    manager = OntologyManager()
    
    # Alle Konzepte anzeigen
    concepts = manager.get_all_concepts()
    logger.info(f"Geladene Konzepte: {len(concepts)}")
    
    for concept in concepts[:10]:
        logger.info(f"  - {concept['label']} ({concept['uri']})")
