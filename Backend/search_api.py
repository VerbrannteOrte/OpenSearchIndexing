#!/usr/bin/env python3
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from opensearchpy import OpenSearch
from facet_config_manager import FacetConfigManager
from indexing_config import IndexingConfig

app = Flask(__name__)
CORS(app)

# Manager
facet_manager = FacetConfigManager()
indexing_config = IndexingConfig()

# OpenSearch Client
client = OpenSearch(
    hosts=[os.getenv('OPENSEARCH_URL', 'https://localhost:9200')],
    http_auth=(
        os.getenv('OPENSEARCH_USER', 'admin'),
        os.getenv('OPENSEARCH_PASSWORD', 'Admin123!')
    ),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False
)


@app.route('/search', methods=['GET'])
def search():
    """Volltextsuche über alle Indizes mit dynamischen Facetten"""
    query = request.args.get('q', '')
    size = int(request.args.get('size', 10))
    index = request.args.get('index', 'documents,web_pages')
    
    if not query:
        return jsonify({'error': 'Query parameter "q" required'}), 400
    
    # Dynamische Aggregationen aus Facetten-Config generieren
    aggregations = {}
    enabled_facets = facet_manager.get_facets(enabled_only=True)
    
    for facet in enabled_facets:
        agg = facet_manager.generate_opensearch_aggregation(facet)
        aggregations[facet['id']] = agg
    
    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "content^2", "description", "ocr_text"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        "highlight": {
            "fields": {
                "content": {"fragment_size": 150, "number_of_fragments": 3},
                "title": {},
                "description": {}
            },
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"]
        },
        "aggs": aggregations,
        "size": size
    }
    
    try:
        response = client.search(index=index, body=search_body)
        
        results = []
        for hit in response['hits']['hits']:
            result = {
                'id': hit['_id'],
                'score': hit['_score'],
                'source': hit['_source'],
                'highlights': hit.get('highlight', {})
            }
            results.append(result)
        
        # Aggregationen mit Display-Maps anreichern
        facets_data = {}
        for facet in enabled_facets:
            facet_id = facet['id']
            if facet_id in response.get('aggregations', {}):
                agg_result = response['aggregations'][facet_id]
                
                # Bei nested Aggregations die inneren Buckets extrahieren
                if facet['source'] == 'nested':
                    buckets = agg_result[f"{facet_id}_terms"]['buckets']
                else:
                    buckets = agg_result['buckets']
                
                # Display-Mapping anwenden falls vorhanden
                if 'display_map' in facet:
                    for bucket in buckets:
                        if bucket['key'] in facet['display_map']:
                            bucket['display_name'] = facet['display_map'][bucket['key']]
                        else:
                            bucket['display_name'] = bucket['key']
                else:
                    for bucket in buckets:
                        bucket['display_name'] = bucket['key']
                
                facets_data[facet_id] = {
                    'label': facet['label'],
                    'icon': facet.get('icon', '📊'),
                    'buckets': buckets
                }
        
        return jsonify({
            'total': response['hits']['total']['value'],
            'results': results,
            'facets': facets_data,
            'took': response['took']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/search/facets', methods=['GET'])
def search_facets():
    """Suche mit Facetten (Filter)"""
    query = request.args.get('q', '')
    
    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title", "content"]
            }
        },
        "aggs": {
            "mime_types": {
                "terms": {"field": "mime_type", "size": 10}
            },
            "domains": {
                "terms": {"field": "domain", "size": 10}
            },
            "languages": {
                "terms": {"field": "language", "size": 10}
            }
        },
        "size": 10
    }
    
    try:
        response = client.search(index='documents,web_pages', body=search_body)
        
        return jsonify({
            'results': response['hits']['hits'],
            'facets': response['aggregations']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/suggest', methods=['GET'])
def suggest():
    """Auto-Vervollständigung für Suche"""
    prefix = request.args.get('prefix', '')
    
    if len(prefix) < 2:
        return jsonify({'suggestions': []})
    
    search_body = {
        "suggest": {
            "title-suggest": {
                "prefix": prefix,
                "completion": {
                    "field": "title.keyword",
                    "size": 5
                }
            }
        }
    }
    
    try:
        response = client.search(index='documents,web_pages', body=search_body)
        suggestions = response['suggest']['title-suggest'][0]['options']
        
        return jsonify({
            'suggestions': [s['text'] for s in suggestions]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/stats', methods=['GET'])
def stats():
    """Statistiken über indexierte Dokumente"""
    try:
        docs_count = client.count(index='documents')
        pages_count = client.count(index='web_pages')
        
        return jsonify({
            'documents': docs_count['count'],
            'web_pages': pages_count['count'],
            'total': docs_count['count'] + pages_count['count']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === Facetten-Verwaltungs-Endpunkte ===

@app.route('/admin/facets', methods=['GET'])
def get_facets():
    """Gibt alle Facetten zurück"""
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
    facets = facet_manager.get_facets(enabled_only=enabled_only)
    return jsonify({'facets': facets})


@app.route('/admin/facets/<facet_id>', methods=['GET'])
def get_facet(facet_id):
    """Gibt eine spezifische Facette zurück"""
    facet = facet_manager.get_facet(facet_id)
    if facet:
        return jsonify(facet)
    return jsonify({'error': 'Facette nicht gefunden'}), 404


@app.route('/admin/facets', methods=['POST'])
def add_facet():
    """Fügt eine neue Facette hinzu"""
    facet_config = request.json
    
    if facet_manager.add_facet(facet_config):
        return jsonify({'success': True, 'message': 'Facette hinzugefügt'})
    return jsonify({'success': False, 'error': 'Fehler beim Hinzufügen'}), 400


@app.route('/admin/facets/<facet_id>', methods=['PUT'])
def update_facet(facet_id):
    """Aktualisiert eine Facette"""
    updates = request.json
    
    if facet_manager.update_facet(facet_id, updates):
        return jsonify({'success': True, 'message': 'Facette aktualisiert'})
    return jsonify({'success': False, 'error': 'Facette nicht gefunden'}), 404


@app.route('/admin/facets/<facet_id>', methods=['DELETE'])
def delete_facet(facet_id):
    """Entfernt eine Facette"""
    if facet_manager.remove_facet(facet_id):
        return jsonify({'success': True, 'message': 'Facette entfernt'})
    return jsonify({'success': False, 'error': 'Facette nicht gefunden'}), 404


@app.route('/admin/facets/<facet_id>/toggle', methods=['POST'])
def toggle_facet(facet_id):
    """Aktiviert/Deaktiviert eine Facette"""
    enabled = request.json.get('enabled', True)
    
    if facet_manager.toggle_facet(facet_id, enabled):
        return jsonify({'success': True, 'message': f"Facette {'aktiviert' if enabled else 'deaktiviert'}"})
    return jsonify({'success': False, 'error': 'Facette nicht gefunden'}), 404


@app.route('/admin/facets/reorder', methods=['POST'])
def reorder_facets():
    """Ändert die Reihenfolge der Facetten"""
    facet_ids = request.json.get('facet_ids', [])
    
    if facet_manager.reorder_facets(facet_ids):
        return jsonify({'success': True, 'message': 'Reihenfolge aktualisiert'})
    return jsonify({'success': False, 'error': 'Fehler beim Umsortieren'}), 400


@app.route('/admin/facets/export', methods=['GET'])
def export_facets():
    """Exportiert Facetten-Konfiguration"""
    config = facet_manager.export_config()
    return jsonify(config)


@app.route('/admin/ontologies', methods=['GET'])
def list_ontologies():
    """Listet verfügbare Ontologien auf"""
    from ontology_manager import OntologyManager
    
    ontology_mgr = OntologyManager()
    
    ontologies = []
    for name, graph in ontology_mgr.graphs.items():
        ontologies.append({
            'name': name,
            'concepts_count': len(ontology_mgr.concept_labels),
            'schemes': list(ontology_mgr.concept_schemes.keys())
        })
    
    return jsonify({'ontologies': ontologies})


@app.route('/admin/facets/from-ontology', methods=['POST'])
def create_facet_from_ontology():
    """Erstellt eine Facette aus einer Ontologie"""
    data = request.json
    ontology_name = data.get('ontology_name')
    label = data.get('label')
    icon = data.get('icon', '🏷️')
    field_name = data.get('field_name')
    
    if not ontology_name or not label:
        return jsonify({'error': 'ontology_name und label erforderlich'}), 400
    
    if facet_manager.create_ontology_facet(ontology_name, label, field_name, icon):
        return jsonify({'success': True, 'message': 'Facette erstellt'})
    return jsonify({'success': False, 'error': 'Fehler beim Erstellen'}), 400


# === Indexierungs-Verzeichnisse ===

@app.route('/admin/directories', methods=['GET'])
def get_directories():
    """Gibt alle konfigurierten Verzeichnisse zurück"""
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
    directories = indexing_config.get_directories(enabled_only=enabled_only)
    return jsonify({'directories': directories})


@app.route('/admin/directories/<directory_id>', methods=['GET'])
def get_directory(directory_id):
    """Gibt ein spezifisches Verzeichnis zurück"""
    directories = indexing_config.get_directories(enabled_only=False)
    directory = next((d for d in directories if d['id'] == directory_id), None)
    
    if directory:
        return jsonify(directory)
    return jsonify({'error': 'Verzeichnis nicht gefunden'}), 404


@app.route('/admin/directories', methods=['POST'])
def add_directory():
    """Fügt ein neues Verzeichnis hinzu"""
    directory_config = request.json
    
    if indexing_config.add_directory(directory_config):
        return jsonify({'success': True, 'message': 'Verzeichnis hinzugefügt'})
    return jsonify({'success': False, 'error': 'Fehler beim Hinzufügen'}), 400


@app.route('/admin/directories/<directory_id>', methods=['PUT'])
def update_directory(directory_id):
    """Aktualisiert ein Verzeichnis"""
    updates = request.json
    
    if indexing_config.update_directory(directory_id, updates):
        return jsonify({'success': True, 'message': 'Verzeichnis aktualisiert'})
    return jsonify({'success': False, 'error': 'Verzeichnis nicht gefunden'}), 404


@app.route('/admin/directories/<directory_id>', methods=['DELETE'])
def delete_directory(directory_id):
    """Entfernt ein Verzeichnis"""
    if indexing_config.remove_directory(directory_id):
        return jsonify({'success': True, 'message': 'Verzeichnis entfernt'})
    return jsonify({'success': False, 'error': 'Verzeichnis nicht gefunden'}), 404


@app.route('/admin/supported-file-types', methods=['GET'])
def get_supported_file_types():
    """Gibt unterstützte Dateitypen zurück"""
    return jsonify({
        'file_types': indexing_config.supported_extensions,
        'all_extensions': indexing_config.get_all_supported_extensions()
    })


@app.route('/admin/trigger-indexing', methods=['POST'])
def trigger_indexing():
    """Triggert manuelle Re-Indexierung"""
    # Hier würde normalerweise ein Signal an den Indexer gesendet
    # Für dieses Beispiel geben wir nur eine Bestätigung zurück
    return jsonify({
        'success': True,
        'message': 'Indexierung wurde getriggert. Prüfen Sie die Indexer-Logs.'
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
