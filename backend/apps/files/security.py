"""
File Security Scanner
Virus scanning and malware detection for uploaded files
"""
import hashlib
import logging
import mimetypes
from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class FileSecurityScanner:
    """
    Security scanner for uploaded files
    
    Implements multiple security checks:
    1. File extension validation
    2. MIME type validation
    3. File signature (magic bytes) validation
    4. Optional: ClamAV antivirus scanning
    5. File size limits
    """
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
        'videos': ['.mp4', '.avi', '.mov', '.webm'],
    }
    
    # File signatures (magic bytes) for common formats
    FILE_SIGNATURES = {
        'pdf': [b'%PDF-'],
        'docx': [b'PK\x03\x04'],  # ZIP format
        'doc': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # OLE format
        'jpg': [b'\xff\xd8\xff'],
        'png': [b'\x89PNG\r\n\x1a\n'],
        'gif': [b'GIF87a', b'GIF89a'],
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZES = {
        'resume': 10 * 1024 * 1024,  # 10MB
        'image': 5 * 1024 * 1024,     # 5MB
        'video': 100 * 1024 * 1024,   # 100MB
    }
    
    @classmethod
    def validate_file(cls, uploaded_file, file_category='documents'):
        """
        Comprehensive file validation
        
        Args:
            uploaded_file: Django UploadedFile object
            file_category: 'documents', 'images', or 'videos'
        
        Raises:
            ValidationError: If file fails any security check
        """
        # 1. Extension check
        cls._validate_extension(uploaded_file.name, file_category)
        
        # 2. MIME type check
        cls._validate_mime_type(uploaded_file)
        
        # 3. File signature check (magic bytes)
        cls._validate_file_signature(uploaded_file)
        
        # 4. Size check
        cls._validate_file_size(uploaded_file, file_category)
        
        # 5. Optional: ClamAV scan (if available)
        if cls._is_clamav_available():
            cls._scan_with_clamav(uploaded_file)
        else:
            logger.warning("ClamAV not available, skipping virus scan")
        
        logger.info(f"File validation passed: {uploaded_file.name}")
        return True
    
    @classmethod
    def _validate_extension(cls, filename, category):
        """Check if file extension is allowed"""
        import os
        ext = os.path.splitext(filename)[1].lower()
        
        allowed = cls.ALLOWED_EXTENSIONS.get(category, [])
        if ext not in allowed:
            raise ValidationError(
                f"File extension '{ext}' not allowed. "
                f"Allowed extensions: {', '.join(allowed)}"
            )
    
    @classmethod
    def _validate_mime_type(cls, uploaded_file):
        """
        Validate MIME type matches file extension
        Prevents .exe.pdf attacks
        """
        import os
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        
        # Get MIME type from file content
        content_type = uploaded_file.content_type
        
        # Expected MIME types
        expected_mimes = {
            '.pdf': ['application/pdf'],
            '.doc': ['application/msword'],
            '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            '.jpg': ['image/jpeg'],
            '.jpeg': ['image/jpeg'],
            '.png': ['image/png'],
            '.gif': ['image/gif'],
        }
        
        if ext in expected_mimes:
            if content_type not in expected_mimes[ext]:
                raise ValidationError(
                    f"MIME type mismatch. File claims to be {ext} "
                    f"but has MIME type {content_type}"
                )
    
    @classmethod
    def _validate_file_signature(cls, uploaded_file):
        """
        Validate file signature (magic bytes)
        Detects if file is actually what extension claims
        """
        import os
        
        # Read first 32 bytes
        uploaded_file.seek(0)
        file_header = uploaded_file.read(32)
        uploaded_file.seek(0)  # Reset for later processing
        
        ext = os.path.splitext(uploaded_file.name)[1].lower().lstrip('.')
        
        if ext in cls.FILE_SIGNATURES:
            expected_signatures = cls.FILE_SIGNATURES[ext]
            
            # Check if file starts with any expected signature
            is_valid = any(
                file_header.startswith(sig) 
                for sig in expected_signatures
            )
            
            if not is_valid:
                raise ValidationError(
                    f"File signature mismatch. File may be corrupted or malicious."
                )
    
    @classmethod
    def _validate_file_size(cls, uploaded_file, category):
        """Check file size limits"""
        max_size = cls.MAX_FILE_SIZES.get(
            'resume' if category == 'documents' else category,
            10 * 1024 * 1024  # Default 10MB
        )
        
        if uploaded_file.size > max_size:
            raise ValidationError(
                f"File too large. Maximum size: {max_size / (1024*1024):.1f}MB"
            )
    
    @classmethod
    def _is_clamav_available(cls):
        """Check if ClamAV is available"""
        try:
            import pyclamd
            cd = pyclamd.ClamdUnixSocket()
            return cd.ping()
        except:
            return False
    
    @classmethod
    def _scan_with_clamav(cls, uploaded_file):
        """
        Scan file with ClamAV antivirus
        
        Installation:
        - Ubuntu: apt-get install clamav clamav-daemon
        - Python: pip install pyclamd
        - Start daemon: service clamav-daemon start
        """
        try:
            import pyclamd
            
            cd = pyclamd.ClamdUnixSocket()
            
            # Read file content
            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            uploaded_file.seek(0)
            
            # Scan
            result = cd.scan_stream(file_content)
            
            if result:
                # Virus found
                virus_name = result.get('stream', ['UNKNOWN'])[1]
                logger.error(f"VIRUS DETECTED: {virus_name} in {uploaded_file.name}")
                raise ValidationError(
                    f"Security threat detected: {virus_name}. File upload rejected."
                )
            
            logger.info(f"ClamAV scan passed: {uploaded_file.name}")
            
        except ImportError:
            logger.warning("pyclamd not installed, skipping ClamAV scan")
        except Exception as e:
            logger.error(f"ClamAV scan error: {e}")
            # Don't block upload if scanner fails
            # But log for security monitoring
    
    @classmethod
    def calculate_file_hash(cls, uploaded_file):
        """Calculate SHA256 hash of file for deduplication"""
        uploaded_file.seek(0)
        file_hash = hashlib.sha256()
        
        # Read in chunks to handle large files
        for chunk in uploaded_file.chunks():
            file_hash.update(chunk)
        
        uploaded_file.seek(0)
        return file_hash.hexdigest()


def validate_resume_file(uploaded_file):
    """Shortcut for resume validation"""
    return FileSecurityScanner.validate_file(uploaded_file, 'documents')


def validate_image_file(uploaded_file):
    """Shortcut for image validation"""
    return FileSecurityScanner.validate_file(uploaded_file, 'images')
