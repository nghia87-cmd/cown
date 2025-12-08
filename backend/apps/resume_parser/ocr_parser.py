"""
OCR Support for Resume Parser
Handles scanned PDFs and image-based documents
"""

import os
from typing import Dict, List, Optional
from io import BytesIO


class OCRResumeParser:
    """
    OCR-based resume parser for scanned PDFs and images
    
    Supports:
    - Tesseract OCR (free, open-source)
    - Azure Form Recognizer (paid, high accuracy)
    - Google Document AI (paid, high accuracy)
    
    Use when: ImprovedResumeParser returns empty/garbled text
    """
    
    def __init__(self, file_obj, ocr_engine: str = 'tesseract'):
        """
        Initialize OCR parser
        
        Args:
            file_obj: Django FileField object
            ocr_engine: 'tesseract', 'azure', or 'google'
        """
        self.file_obj = file_obj
        self.ocr_engine = ocr_engine
        self.text = ""
    
    def extract_text(self) -> str:
        """
        Extract text using OCR
        
        Returns:
            Extracted text content
        """
        if self.ocr_engine == 'tesseract':
            return self._extract_with_tesseract()
        elif self.ocr_engine == 'azure':
            return self._extract_with_azure()
        elif self.ocr_engine == 'google':
            return self._extract_with_google()
        else:
            raise ValueError(f"Unsupported OCR engine: {self.ocr_engine}")
    
    def _extract_with_tesseract(self) -> str:
        """
        Extract text using Tesseract OCR (FREE)
        
        Installation:
        - Windows: https://github.com/UB-Mannheim/tesseract/wiki
        - Ubuntu: sudo apt-get install tesseract-ocr
        - Python: pip install pytesseract pillow pdf2image
        
        Requirements:
        - pytesseract
        - pdf2image
        - Pillow
        """
        try:
            import pytesseract
            from pdf2image import convert_from_bytes
            from PIL import Image
            
            file_name = self.file_obj.name
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # Read file content
            self.file_obj.open('rb')
            file_content = self.file_obj.read()
            self.file_obj.close()
            
            text_parts = []
            
            if file_ext == '.pdf':
                # Convert PDF pages to images
                images = convert_from_bytes(file_content, dpi=300)
                
                # OCR each page
                for i, image in enumerate(images):
                    page_text = pytesseract.image_to_string(image, lang='eng+vie')
                    text_parts.append(f"--- Page {i+1} ---\n{page_text}")
            
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                # Direct image OCR
                image = Image.open(BytesIO(file_content))
                text = pytesseract.image_to_string(image, lang='eng+vie')
                text_parts.append(text)
            
            else:
                raise ValueError(f"Unsupported file type for OCR: {file_ext}")
            
            return "\n\n".join(text_parts)
        
        except ImportError as e:
            raise ImportError(
                "Tesseract OCR dependencies not installed. "
                "Install with: pip install pytesseract pdf2image pillow"
            )
    
    def _extract_with_azure(self) -> str:
        """
        Extract text using Azure Form Recognizer (PAID)
        
        Advantages:
        - High accuracy (90%+)
        - Understands document layout
        - Extracts tables and forms
        
        Setup:
        1. Create Azure Cognitive Services resource
        2. Get API key and endpoint
        3. pip install azure-ai-formrecognizer
        4. Add to settings.py:
           AZURE_FORM_RECOGNIZER_KEY = 'your-key'
           AZURE_FORM_RECOGNIZER_ENDPOINT = 'your-endpoint'
        """
        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential
            from django.conf import settings
            
            # Get credentials from settings
            key = getattr(settings, 'AZURE_FORM_RECOGNIZER_KEY', None)
            endpoint = getattr(settings, 'AZURE_FORM_RECOGNIZER_ENDPOINT', None)
            
            if not key or not endpoint:
                raise ValueError("Azure Form Recognizer credentials not configured")
            
            # Create client
            client = DocumentAnalysisClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )
            
            # Read file
            self.file_obj.open('rb')
            file_content = self.file_obj.read()
            self.file_obj.close()
            
            # Analyze document
            poller = client.begin_analyze_document(
                "prebuilt-document",
                document=file_content
            )
            result = poller.result()
            
            # Extract text with layout
            text_parts = []
            for page in result.pages:
                page_text = []
                for line in page.lines:
                    page_text.append(line.content)
                text_parts.append("\n".join(page_text))
            
            return "\n\n".join(text_parts)
        
        except ImportError:
            raise ImportError(
                "Azure Form Recognizer not installed. "
                "Install with: pip install azure-ai-formrecognizer"
            )
    
    def _extract_with_google(self) -> str:
        """
        Extract text using Google Document AI (PAID)
        
        Advantages:
        - Very high accuracy
        - Multi-language support
        - Entity extraction
        
        Setup:
        1. Enable Document AI API in Google Cloud
        2. Create service account and download JSON key
        3. pip install google-cloud-documentai
        4. Add to settings.py:
           GOOGLE_APPLICATION_CREDENTIALS = '/path/to/key.json'
           GOOGLE_DOCUMENT_AI_PROJECT_ID = 'your-project-id'
           GOOGLE_DOCUMENT_AI_PROCESSOR_ID = 'your-processor-id'
        """
        try:
            from google.cloud import documentai_v1 as documentai
            from django.conf import settings
            
            # Get credentials
            project_id = getattr(settings, 'GOOGLE_DOCUMENT_AI_PROJECT_ID', None)
            processor_id = getattr(settings, 'GOOGLE_DOCUMENT_AI_PROCESSOR_ID', None)
            
            if not project_id or not processor_id:
                raise ValueError("Google Document AI credentials not configured")
            
            # Create client
            client = documentai.DocumentProcessorServiceClient()
            
            # Read file
            self.file_obj.open('rb')
            file_content = self.file_obj.read()
            self.file_obj.close()
            
            # Prepare request
            name = f"projects/{project_id}/locations/us/processors/{processor_id}"
            document = documentai.Document(
                content=file_content,
                mime_type=self._get_mime_type()
            )
            
            request = documentai.ProcessRequest(
                name=name,
                raw_document=documentai.RawDocument(
                    content=file_content,
                    mime_type=self._get_mime_type()
                )
            )
            
            # Process document
            result = client.process_document(request=request)
            
            return result.document.text
        
        except ImportError:
            raise ImportError(
                "Google Document AI not installed. "
                "Install with: pip install google-cloud-documentai"
            )
    
    def _get_mime_type(self) -> str:
        """Get MIME type from file extension"""
        file_ext = os.path.splitext(self.file_obj.name)[1].lower()
        
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.bmp': 'image/bmp',
        }
        
        return mime_types.get(file_ext, 'application/octet-stream')
    
    @staticmethod
    def is_scanned_pdf(file_obj) -> bool:
        """
        Detect if PDF is scanned (image-based)
        
        Logic:
        - Extract text with pdfplumber
        - If text length < 100 chars, likely scanned
        - If text is mostly garbled, likely scanned
        
        Returns:
            True if PDF appears to be scanned
        """
        try:
            import pdfplumber
            from io import BytesIO
            
            file_obj.open('rb')
            file_content = file_obj.read()
            file_obj.close()
            
            text = ""
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                # Check first page
                if len(pdf.pages) > 0:
                    text = pdf.pages[0].extract_text() or ""
            
            # Heuristics
            if len(text) < 100:
                return True
            
            # Check for garbled text (lots of special chars)
            special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
            if special_char_ratio > 0.5:
                return True
            
            return False
        
        except Exception:
            # If can't determine, assume not scanned
            return False


# Convenience function
def parse_resume_with_ocr(
    file_obj,
    ocr_engine: str = 'tesseract'
) -> str:
    """
    Parse resume with OCR
    
    Args:
        file_obj: Django FileField object
        ocr_engine: 'tesseract', 'azure', or 'google'
    
    Returns:
        Extracted text
    
    Usage:
        from apps.resume_parser.ocr_parser import parse_resume_with_ocr
        
        text = parse_resume_with_ocr(
            file_obj=parsed_resume.file,
            ocr_engine='tesseract'
        )
    """
    parser = OCRResumeParser(file_obj, ocr_engine=ocr_engine)
    return parser.extract_text()
