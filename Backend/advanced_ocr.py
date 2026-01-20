#!/usr/bin/env python3
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import json

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logging.warning("EasyOCR nicht verfügbar. Installieren Sie es für bessere Ergebnisse.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedOCR:
    """Erweiterte OCR-Engine mit Sütterlin-Support und GPU-Beschleunigung"""
    
    def __init__(
        self,
        use_gpu: bool = True,
        enable_suetterlin: bool = True,
        cache_dir: str = "/tmp/ocr_cache"
    ):
        self.use_gpu = use_gpu and self._check_gpu_available()
        self.enable_suetterlin = enable_suetterlin
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Tesseract Konfiguration
        self.tesseract_configs = {
            'standard': '--psm 3 --oem 3',
            'single_column': '--psm 6 --oem 3',
            'sparse_text': '--psm 11 --oem 3',
            'handwriting': '--psm 13 --oem 3'
        }
        
        # EasyOCR für Sütterlin und schwierige Texte
        self.easyocr_reader = None
        if EASYOCR_AVAILABLE and self.use_gpu:
            try:
                self.easyocr_reader = easyocr.Reader(
                    ['de', 'en'],
                    gpu=self.use_gpu,
                    download_enabled=True,
                    model_storage_directory='/models/easyocr'
                )
                logger.info(f"EasyOCR initialisiert (GPU: {self.use_gpu})")
            except Exception as e:
                logger.error(f"EasyOCR Initialisierung fehlgeschlagen: {e}")
                self.easyocr_reader = None
        
        # Statistiken
        self.stats = {
            'total_processed': 0,
            'gpu_processed': 0,
            'suetterlin_detected': 0,
            'preprocessing_applied': 0
        }
    
    def _check_gpu_available(self) -> bool:
        """Prüft ob GPU verfügbar ist"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def preprocess_image(
        self, 
        image: Image.Image,
        mode: str = 'standard'
    ) -> Image.Image:
        """
        Erweiterte Bildvorverarbeitung für bessere OCR
        
        Modes:
        - standard: Normale Dokumente
        - historical: Alte/vergilbte Dokumente
        - handwriting: Handschrift/Sütterlin
        - low_quality: Schlechte Scans
        """
        self.stats['preprocessing_applied'] += 1
        
        # Zu NumPy Array konvertieren
        img_array = np.array(image)
        
        if mode == 'historical':
            # Für alte Dokumente
            img_array = self._enhance_historical_document(img_array)
        
        elif mode == 'handwriting':
            # Für Handschrift und Sütterlin
            img_array = self._enhance_handwriting(img_array)
        
        elif mode == 'low_quality':
            # Für schlechte Scans
            img_array = self._enhance_low_quality(img_array)
        
        else:
            # Standard-Verarbeitung
            img_array = self._enhance_standard(img_array)
        
        # Zurück zu PIL Image
        return Image.fromarray(img_array)
    
    def _enhance_standard(self, img: np.ndarray) -> np.ndarray:
        """Standard-Verbesserung"""
        # Graustufen
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Entrauschen
        img = cv2.fastNlMeansDenoising(img, h=10)
        
        # Adaptive Binarisierung
        img = cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        return img
    
    def _enhance_historical_document(self, img: np.ndarray) -> np.ndarray:
        """Verbesserung für alte/vergilbte Dokumente"""
        # Graustufen
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Kontrast erhöhen
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        img = clahe.apply(img)
        
        # Starkes Entrauschen
        img = cv2.fastNlMeansDenoising(img, h=15)
        
        # Morphologische Operationen für bessere Textqualität
        kernel = np.ones((2,2), np.uint8)
        img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
        
        # Adaptive Binarisierung mit größerem Block
        img = cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 15, 5
        )
        
        return img
    
    def _enhance_handwriting(self, img: np.ndarray) -> np.ndarray:
        """Verbesserung für Handschrift/Sütterlin"""
        # Graustufen
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Sehr starkes Entrauschen
        img = cv2.fastNlMeansDenoising(img, h=20)
        
        # Kontrast maximieren
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
        img = clahe.apply(img)
        
        # Kantenverstärkung
        img = cv2.bilateralFilter(img, 9, 75, 75)
        
        # Otsu's Binarisierung (gut für Handschrift)
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphologische Operationen
        kernel = np.ones((1,1), np.uint8)
        img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
        
        return img
    
    def _enhance_low_quality(self, img: np.ndarray) -> np.ndarray:
        """Verbesserung für schlechte Scans"""
        # Graustufen
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Sehr starkes Entrauschen
        img = cv2.fastNlMeansDenoising(img, h=25)
        
        # Schärfen
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        img = cv2.filter2D(img, -1, kernel)
        
        # Kontrast erhöhen
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        img = clahe.apply(img)
        
        # Adaptive Binarisierung
        img = cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        return img
    
    def detect_text_type(self, image: Image.Image) -> str:
        """
        Erkennt die Art des Texts (Druckschrift, Handschrift, Sütterlin)
        """
        # Einfache Heuristik basierend auf Bildmerkmalen
        img_array = np.array(image.convert('L'))
        
        # Kantendetektion
        edges = cv2.Canny(img_array, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Varianz (Handschrift hat höhere Varianz)
        variance = np.var(img_array)
        
        # Heuristik
        if edge_density > 0.15 and variance > 2000:
            # Viele Kanten und hohe Varianz → wahrscheinlich Handschrift
            return 'handwriting'
        elif variance < 1000:
            # Niedrige Varianz → wahrscheinlich alter/verblasster Text
            return 'historical'
        else:
            # Standard Druckschrift
            return 'standard'
    
    def extract_text_tesseract(
        self,
        image: Image.Image,
        lang: str = 'deu+eng',
        config: str = 'standard'
    ) -> Dict[str, Any]:
        """OCR mit Tesseract"""
        try:
            # Preprocessing
            text_type = self.detect_text_type(image)
            processed_image = self.preprocess_image(image, mode=text_type)
            
            # Tesseract Config
            tesseract_config = self.tesseract_configs.get(config, self.tesseract_configs['standard'])
            
            # OCR durchführen
            text = pytesseract.image_to_string(
                processed_image,
                lang=lang,
                config=tesseract_config
            )
            
            # Konfidenz
            data = pytesseract.image_to_data(
                processed_image,
                lang=lang,
                output_type=pytesseract.Output.DICT
            )
            
            confidences = [int(c) for c in data['conf'] if c != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'text': text,
                'confidence': avg_confidence,
                'method': 'tesseract',
                'text_type': text_type,
                'preprocessing': True
            }
        
        except Exception as e:
            logger.error(f"Tesseract OCR Fehler: {e}")
            return {
                'text': '',
                'confidence': 0,
                'method': 'tesseract',
                'error': str(e)
            }
    
    def extract_text_easyocr(
        self,
        image: Image.Image,
        languages: List[str] = ['de', 'en']
    ) -> Dict[str, Any]:
        """OCR mit EasyOCR (besser für Handschrift/Sütterlin)"""
        if not self.easyocr_reader:
            return {
                'text': '',
                'confidence': 0,
                'method': 'easyocr',
                'error': 'EasyOCR nicht verfügbar'
            }
        
        try:
            # Zu NumPy Array
            img_array = np.array(image)
            
            # OCR durchführen
            results = self.easyocr_reader.readtext(
                img_array,
                detail=1,
                paragraph=True
            )
            
            # Text und Konfidenz extrahieren
            text_parts = []
            confidences = []
            
            for (bbox, text, conf) in results:
                text_parts.append(text)
                confidences.append(conf)
            
            combined_text = '\n'.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            if self.use_gpu:
                self.stats['gpu_processed'] += 1
            
            return {
                'text': combined_text,
                'confidence': avg_confidence * 100,  # Normalisieren auf 0-100
                'method': 'easyocr',
                'gpu_used': self.use_gpu,
                'preprocessing': False
            }
        
        except Exception as e:
            logger.error(f"EasyOCR Fehler: {e}")
            return {
                'text': '',
                'confidence': 0,
                'method': 'easyocr',
                'error': str(e)
            }
    
    def extract_text_suetterlin(
        self,
        image: Image.Image
    ) -> Dict[str, Any]:
        """
        Spezielle OCR für Sütterlin-Schrift
        
        Verwendet eine Kombination aus:
        1. Speziellem Preprocessing für alte Handschriften
        2. EasyOCR mit GPU-Beschleunigung
        3. Fallback auf Tesseract mit angepassten Parametern
        """
        self.stats['suetterlin_detected'] += 1
        
        logger.info("Sütterlin-Erkennung gestartet")
        
        # Spezielles Preprocessing für Sütterlin
        processed_image = self.preprocess_image(image, mode='handwriting')
        
        # Versuch 1: EasyOCR (wenn verfügbar und GPU)
        if self.easyocr_reader and self.use_gpu:
            result = self.extract_text_easyocr(processed_image)
            
            if result['confidence'] > 50:  # Akzeptable Konfidenz
                result['is_suetterlin'] = True
                logger.info(f"Sütterlin erkannt via EasyOCR (Konfidenz: {result['confidence']:.1f}%)")
                return result
        
        # Versuch 2: Tesseract mit Fraktur/Gothic
        # Sütterlin ähnelt der Fraktur-Schrift
        tesseract_result = self.extract_text_tesseract(
            processed_image,
            lang='deu_frak+deu+eng',  # Fraktur-Modell
            config='handwriting'
        )
        
        tesseract_result['is_suetterlin'] = True
        logger.info(f"Sütterlin verarbeitet via Tesseract (Konfidenz: {tesseract_result['confidence']:.1f}%)")
        
        return tesseract_result
    
    def extract_text_auto(
        self,
        image: Image.Image,
        lang: str = 'deu+eng',
        enable_suetterlin_detection: bool = None
    ) -> Dict[str, Any]:
        """
        Automatische OCR mit intelligenter Methodenwahl
        """
        self.stats['total_processed'] += 1
        
        if enable_suetterlin_detection is None:
            enable_suetterlin_detection = self.enable_suetterlin
        
        # Textyp erkennen
        text_type = self.detect_text_type(image)
        
        # Wenn Handschrift und Sütterlin aktiviert
        if text_type == 'handwriting' and enable_suetterlin_detection:
            return self.extract_text_suetterlin(image)
        
        # Wenn GPU verfügbar und EasyOCR installiert, bevorzuge EasyOCR
        if self.easyocr_reader and self.use_gpu and text_type == 'handwriting':
            result = self.extract_text_easyocr(image)
            if result['confidence'] > 40:
                return result
        
        # Standard: Tesseract
        return self.extract_text_tesseract(image, lang=lang)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Gibt OCR-Statistiken zurück"""
        return {
            **self.stats,
            'gpu_available': self.use_gpu,
            'easyocr_available': self.easyocr_reader is not None,
            'suetterlin_enabled': self.enable_suetterlin
        }


# Batch-OCR-Verarbeitung
class BatchOCRProcessor:
    """Optimierte Batch-Verarbeitung für große Mengen"""
    
    def __init__(self, ocr_engine: AdvancedOCR, batch_size: int = 10):
        self.ocr_engine = ocr_engine
        self.batch_size = batch_size
    
    def process_batch(
        self,
        image_paths: List[str],
        output_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Verarbeitet eine Liste von Bildern in Batches"""
        results = []
        
        for i in range(0, len(image_paths), self.batch_size):
            batch = image_paths[i:i + self.batch_size]
            
            logger.info(f"Verarbeite Batch {i//self.batch_size + 1} ({len(batch)} Bilder)")
            
            for image_path in batch:
                try:
                    image = Image.open(image_path)
                    result = self.ocr_engine.extract_text_auto(image)
                    
                    result['file_path'] = image_path
                    result['file_name'] = Path(image_path).name
                    
                    results.append(result)
                    
                    # Optional: Ergebnisse speichern
                    if output_dir:
                        output_path = Path(output_dir) / f"{Path(image_path).stem}.json"
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(output_path, 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)
                
                except Exception as e:
                    logger.error(f"Fehler bei {image_path}: {e}")
                    results.append({
                        'file_path': image_path,
                        'error': str(e),
                        'text': '',
                        'confidence': 0
                    })
        
        return results


if __name__ == '__main__':
    # Test der erweiterten OCR
    ocr = AdvancedOCR(
        use_gpu=True,
        enable_suetterlin=True
    )
    
    # Beispiel-Bild verarbeiten
    test_image_path = '/data/test_document.png'
    
    if os.path.exists(test_image_path):
        image = Image.open(test_image_path)
        
        # Automatische Erkennung
        result = ocr.extract_text_auto(image)
        
        print(f"Methode: {result['method']}")
        print(f"Konfidenz: {result['confidence']:.1f}%")
        print(f"Text:\n{result['text'][:200]}...")
    
    # Statistiken anzeigen
    stats = ocr.get_statistics()
    print(f"\nStatistiken:")
    print(f"  Gesamt verarbeitet: {stats['total_processed']}")
    print(f"  GPU verwendet: {stats['gpu_processed']}")
    print(f"  Sütterlin erkannt: {stats['suetterlin_detected']}")
