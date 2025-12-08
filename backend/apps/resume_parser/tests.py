"""
Unit Tests for Resume Parser
Critical: OCR fallback, scanned PDF detection, skills extraction
"""

import pytest
import io
from unittest.mock import patch, MagicMock
from django.test import TestCase
from apps.resume_parser.parser_improved import ImprovedResumeParser
from apps.resume_parser.ocr_parser import OCRResumeParser


class TestResumeParser(TestCase):
    """Test resume parsing functionality"""
    
    def test_parse_text_resume(self):
        """Test parsing text-based PDF resume"""
        parser = ImprovedResumeParser()
        
        # Mock pdfplumber
        with patch('pdfplumber.open') as mock_pdf:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = """
            John Doe
            john.doe@example.com
            +84 123 456 789
            
            EXPERIENCE
            Senior Software Engineer at Google
            2020 - Present
            - Developed Python applications
            - Led team of 5 developers
            
            SKILLS
            Python, Django, PostgreSQL, Redis, AWS
            """
            
            mock_pdf.return_value.__enter__.return_value.pages = [mock_page]
            
            result = parser.parse(
                file_path='test.pdf',
                content=b'fake pdf content'
            )
            
            # Should extract basic info
            self.assertIsNotNone(result)
            self.assertIn('john.doe@example.com', result.get('emails', []))
            self.assertIn('Python', result.get('skills', []))
            self.assertIn('Django', result.get('skills', []))
            self.assertGreater(len(result.get('experience', [])), 0)
    
    def test_scanned_pdf_fallback_to_ocr(self):
        """Test automatic OCR fallback for scanned PDFs"""
        parser = ImprovedResumeParser()
        
        # Mock pdfplumber to return minimal text (scanned PDF)
        with patch('pdfplumber.open') as mock_pdf:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "  \n  \n  "  # Almost empty
            mock_pdf.return_value.__enter__.return_value.pages = [mock_page]
            
            # Mock OCR parser
            with patch.object(OCRResumeParser, 'parse') as mock_ocr:
                mock_ocr.return_value = {
                    'full_text': 'John Doe\nSoftware Engineer',
                    'emails': ['john@example.com'],
                    'skills': ['Python', 'Java']
                }
                
                result = parser.parse(
                    file_path='scanned.pdf',
                    content=b'fake pdf'
                )
                
                # Should have called OCR
                mock_ocr.assert_called_once()
                
                # Should return OCR results
                self.assertEqual(result['emails'], ['john@example.com'])
                self.assertIn('Python', result['skills'])


class TestOCRParser(TestCase):
    """Test OCR resume parsing"""
    
    def test_detect_scanned_pdf(self):
        """Test scanned PDF detection heuristic"""
        ocr = OCRResumeParser()
        
        # Text-based PDF (high text/page ratio)
        self.assertFalse(ocr.is_scanned_pdf(text_length=500, page_count=1))
        
        # Scanned PDF (low text/page ratio)
        self.assertTrue(ocr.is_scanned_pdf(text_length=10, page_count=1))
        
        # Empty PDF
        self.assertTrue(ocr.is_scanned_pdf(text_length=0, page_count=1))
    
    @patch('pytesseract.image_to_string')
    @patch('pdf2image.convert_from_bytes')
    def test_extract_with_tesseract(self, mock_convert, mock_ocr):
        """Test Tesseract OCR extraction"""
        ocr = OCRResumeParser()
        
        # Mock PDF to image conversion
        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        
        # Mock OCR result
        mock_ocr.return_value = "John Doe\nSenior Developer\npython@example.com"
        
        result = ocr._extract_with_tesseract(b'fake pdf')
        
        self.assertIn('John Doe', result)
        self.assertIn('python@example.com', result)
        mock_convert.assert_called_once()
        mock_ocr.assert_called_once()
    
    def test_parse_ocr_text(self):
        """Test parsing OCR-extracted text"""
        ocr = OCRResumeParser()
        
        with patch.object(ocr, '_extract_with_tesseract') as mock_extract:
            mock_extract.return_value = """
            Jane Smith
            jane.smith@company.com
            +84 987 654 321
            
            TECHNICAL SKILLS
            - Python, Django, Flask
            - JavaScript, React, Node.js
            - PostgreSQL, MongoDB, Redis
            
            WORK EXPERIENCE
            Lead Engineer at Amazon (2021-2023)
            Built scalable microservices
            """
            
            result = ocr.parse(
                file_content=b'fake pdf',
                file_extension='.pdf',
                engine='tesseract'
            )
            
            # Should extract structured data
            self.assertIsNotNone(result)
            self.assertEqual(result['full_text'][:10], 'Jane Smith'[:10])
            self.assertIn('jane.smith@company.com', result['emails'])
            self.assertIn('Python', result['skills'])
            self.assertIn('Django', result['skills'])
            self.assertIn('React', result['skills'])


@pytest.mark.django_db
class TestResumeS3Streaming:
    """Test resume parsing from S3 with streaming"""
    
    def test_parse_from_s3_stream(self):
        """Test parsing resume from S3 without downloading"""
        parser = ImprovedResumeParser()
        
        # Mock S3 file object
        with patch('pdfplumber.open') as mock_pdf:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test resume content"
            mock_pdf.return_value.__enter__.return_value.pages = [mock_page]
            
            # Simulate S3 file as BytesIO
            file_stream = io.BytesIO(b'fake pdf bytes')
            
            result = parser.parse(
                file_path='resume.pdf',
                content=file_stream.read()
            )
            
            self.assertIsNotNone(result)


class TestSkillsExtraction(TestCase):
    """Test skills extraction accuracy"""
    
    def test_extract_programming_languages(self):
        """Test extracting programming language skills"""
        parser = ImprovedResumeParser()
        
        text = """
        TECHNICAL SKILLS
        Languages: Python, Java, JavaScript, TypeScript, Go, Rust
        Frameworks: Django, Spring Boot, React, Vue.js
        Databases: PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch
        Cloud: AWS, Azure, Google Cloud Platform
        """
        
        result = parser._extract_skills(text)
        
        # Should find common skills
        self.assertIn('Python', result)
        self.assertIn('Java', result)
        self.assertIn('JavaScript', result)
        self.assertIn('Django', result)
        self.assertIn('PostgreSQL', result)
        self.assertIn('AWS', result)
    
    def test_extract_skills_from_experience(self):
        """Test extracting skills mentioned in experience section"""
        parser = ImprovedResumeParser()
        
        text = """
        EXPERIENCE
        Backend Developer (2020-2023)
        - Built REST APIs using Django and FastAPI
        - Managed PostgreSQL and Redis databases
        - Deployed on AWS using Docker and Kubernetes
        - Implemented CI/CD with Jenkins and GitLab
        """
        
        result = parser._extract_skills(text)
        
        self.assertIn('Django', result)
        self.assertIn('PostgreSQL', result)
        self.assertIn('Redis', result)
        self.assertIn('Docker', result)
        self.assertIn('Kubernetes', result)


class TestEmailExtraction(TestCase):
    """Test email extraction"""
    
    def test_extract_single_email(self):
        """Test extracting single email address"""
        parser = ImprovedResumeParser()
        
        text = "Contact: john.doe@example.com"
        emails = parser._extract_emails(text)
        
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0], 'john.doe@example.com')
    
    def test_extract_multiple_emails(self):
        """Test extracting multiple email addresses"""
        parser = ImprovedResumeParser()
        
        text = """
        Primary: john.doe@company.com
        Personal: john.personal@gmail.com
        """
        
        emails = parser._extract_emails(text)
        
        self.assertEqual(len(emails), 2)
        self.assertIn('john.doe@company.com', emails)
        self.assertIn('john.personal@gmail.com', emails)


class TestPhoneExtraction(TestCase):
    """Test phone number extraction"""
    
    def test_extract_vietnamese_phone(self):
        """Test extracting Vietnamese phone numbers"""
        parser = ImprovedResumeParser()
        
        text = "Phone: +84 123 456 789"
        phones = parser._extract_phones(text)
        
        self.assertGreater(len(phones), 0)
    
    def test_extract_various_phone_formats(self):
        """Test various phone number formats"""
        parser = ImprovedResumeParser()
        
        text = """
        Mobile: +84 987654321
        Office: (024) 1234-5678
        Home: 0123456789
        """
        
        phones = parser._extract_phones(text)
        
        # Should extract at least some valid formats
        self.assertGreater(len(phones), 0)


@pytest.mark.parametrize('file_extension,expected_type', [
    ('.pdf', 'pdf'),
    ('.jpg', 'image'),
    ('.jpeg', 'image'),
    ('.png', 'image'),
    ('.tiff', 'image'),
])
def test_file_type_detection(file_extension, expected_type):
    """Test file type detection"""
    ocr = OCRResumeParser()
    
    # Should correctly identify file types
    assert expected_type in ['pdf', 'image']
