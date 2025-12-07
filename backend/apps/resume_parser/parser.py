"""
Resume Parser Service - Extract data from PDF/DOCX files
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import PyPDF2
import docx
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from .models import ParsedResume, ResumeParsingLog


class ResumeParser:
    """Parse resume files and extract structured data"""
    
    # Common skills database (can be extended)
    COMMON_SKILLS = [
        # Programming Languages
        'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust',
        'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'SQL', 'HTML', 'CSS',
        
        # Frameworks & Libraries
        'Django', 'Flask', 'FastAPI', 'React', 'Vue', 'Angular', 'Node.js', 'Express',
        'Spring', 'Laravel', 'Rails', 'ASP.NET', 'jQuery', 'Bootstrap', 'Tailwind',
        
        # Databases
        'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server', 'SQLite',
        'DynamoDB', 'Cassandra', 'Elasticsearch',
        
        # DevOps & Cloud
        'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'Jenkins', 'GitLab CI', 'GitHub Actions',
        'Terraform', 'Ansible', 'Linux', 'Unix', 'Nginx', 'Apache',
        
        # Tools & Technologies
        'Git', 'GitHub', 'GitLab', 'Jira', 'Confluence', 'VS Code', 'IntelliJ', 'PyCharm',
        'Postman', 'Figma', 'Sketch', 'Adobe XD',
        
        # Methodologies
        'Agile', 'Scrum', 'Kanban', 'TDD', 'CI/CD', 'Microservices', 'RESTful API',
        'GraphQL', 'OOP', 'Design Patterns',
        
        # Soft Skills
        'Leadership', 'Communication', 'Teamwork', 'Problem Solving', 'Critical Thinking',
        'Time Management', 'Project Management',
    ]
    
    # Email pattern
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Phone pattern (supports various formats)
    PHONE_PATTERN = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    # URL patterns
    LINKEDIN_PATTERN = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+'
    GITHUB_PATTERN = r'(?:https?://)?(?:www\.)?github\.com/[\w-]+'
    
    def __init__(self, parsed_resume: ParsedResume):
        self.parsed_resume = parsed_resume
        self.text = ""
        self.lines = []
    
    def parse(self) -> Dict[str, Any]:
        """Main parsing method"""
        try:
            self._log('START', 'Starting resume parsing', 'INFO')
            
            # Update status
            self.parsed_resume.status = 'PROCESSING'
            self.parsed_resume.processing_started_at = timezone.now()
            self.parsed_resume.save()
            
            # Extract text from file
            self.text = self._extract_text()
            self.lines = [line.strip() for line in self.text.split('\n') if line.strip()]
            
            self._log('EXTRACT', f'Extracted {len(self.text)} characters', 'INFO')
            
            # Parse different sections
            data = {
                'personal_info': self._extract_personal_info(),
                'summary': self._extract_summary(),
                'skills': self._extract_skills(),
                'work_experience': self._extract_work_experience(),
                'education': self._extract_education(),
                'certifications': self._extract_certifications(),
                'languages': self._extract_languages(),
                'social_links': self._extract_social_links(),
            }
            
            # Calculate total experience
            total_exp = self._calculate_total_experience(data.get('work_experience', []))
            
            # Update parsed resume
            self.parsed_resume.raw_data = data
            self.parsed_resume.full_name = data['personal_info'].get('name', '')
            self.parsed_resume.email = data['personal_info'].get('email', '')
            self.parsed_resume.phone = data['personal_info'].get('phone', '')
            self.parsed_resume.location = data['personal_info'].get('location', '')
            self.parsed_resume.summary = data.get('summary', '')
            self.parsed_resume.skills = data.get('skills', [])
            self.parsed_resume.work_experience = data.get('work_experience', [])
            self.parsed_resume.education = data.get('education', [])
            self.parsed_resume.certifications = data.get('certifications', [])
            self.parsed_resume.languages = data.get('languages', [])
            self.parsed_resume.total_experience_years = total_exp
            self.parsed_resume.linkedin_url = data['social_links'].get('linkedin', '')
            self.parsed_resume.github_url = data['social_links'].get('github', '')
            self.parsed_resume.portfolio_url = data['social_links'].get('portfolio', '')
            self.parsed_resume.parsing_confidence = 75.0  # Basic confidence score
            self.parsed_resume.status = 'COMPLETED'
            self.parsed_resume.processing_completed_at = timezone.now()
            self.parsed_resume.save()
            
            self._log('COMPLETE', 'Resume parsing completed successfully', 'INFO')
            
            return data
            
        except Exception as e:
            self._log('ERROR', f'Parsing failed: {str(e)}', 'ERROR')
            self.parsed_resume.status = 'FAILED'
            self.parsed_resume.error_message = str(e)
            self.parsed_resume.save()
            raise
    
    def _extract_text(self) -> str:
        """Extract text from PDF or DOCX file"""
        file_path = self.parsed_resume.file.path
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return self._extract_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return self._extract_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
        except Exception as e:
            self._log('PDF_EXTRACT', f'PDF extraction error: {str(e)}', 'ERROR')
            raise
        return text
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        text = ""
        try:
            doc = docx.Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            self._log('DOCX_EXTRACT', f'DOCX extraction error: {str(e)}', 'ERROR')
            raise
        return text
    
    def _extract_personal_info(self) -> Dict[str, str]:
        """Extract personal information"""
        info = {
            'name': '',
            'email': '',
            'phone': '',
            'location': '',
        }
        
        # Extract email
        email_match = re.search(self.EMAIL_PATTERN, self.text)
        if email_match:
            info['email'] = email_match.group(0)
        
        # Extract phone
        phone_match = re.search(self.PHONE_PATTERN, self.text)
        if phone_match:
            info['phone'] = phone_match.group(0)
        
        # Extract name (usually first non-empty line)
        if self.lines:
            info['name'] = self.lines[0]
        
        # Extract location (heuristic: look for city/country keywords)
        location_keywords = ['Hanoi', 'Ho Chi Minh', 'Da Nang', 'Vietnam', 'VN']
        for line in self.lines[:10]:  # Check first 10 lines
            if any(keyword in line for keyword in location_keywords):
                info['location'] = line
                break
        
        return info
    
    def _extract_summary(self) -> str:
        """Extract professional summary"""
        summary_keywords = ['summary', 'profile', 'objective', 'about', 'overview']
        
        for i, line in enumerate(self.lines):
            if any(keyword in line.lower() for keyword in summary_keywords):
                # Get next few lines as summary
                summary_lines = []
                for j in range(i + 1, min(i + 6, len(self.lines))):
                    if len(self.lines[j]) > 20:  # Reasonable length
                        summary_lines.append(self.lines[j])
                return ' '.join(summary_lines)
        
        return ''
    
    def _extract_skills(self) -> List[str]:
        """Extract skills from resume"""
        skills = []
        text_lower = self.text.lower()
        
        # Find skills section
        skills_section = ""
        for i, line in enumerate(self.lines):
            if 'skill' in line.lower():
                # Get next 10 lines
                skills_section = ' '.join(self.lines[i:i+10])
                break
        
        # Match against common skills
        for skill in self.COMMON_SKILLS:
            if skill.lower() in text_lower or skill.lower() in skills_section.lower():
                if skill not in skills:
                    skills.append(skill)
        
        return skills
    
    def _extract_work_experience(self) -> List[Dict[str, Any]]:
        """Extract work experience"""
        experience = []
        exp_keywords = ['experience', 'employment', 'work history']
        
        # Find experience section
        exp_start = -1
        for i, line in enumerate(self.lines):
            if any(keyword in line.lower() for keyword in exp_keywords):
                exp_start = i
                break
        
        if exp_start == -1:
            return experience
        
        # Simple extraction (can be improved with ML)
        current_exp = {}
        for i in range(exp_start + 1, len(self.lines)):
            line = self.lines[i]
            
            # Stop at next section
            if any(keyword in line.lower() for keyword in ['education', 'certification', 'skill']):
                break
            
            # Heuristic: job title lines are usually short and capitalized
            if len(line) < 60 and line[0].isupper():
                if current_exp:
                    experience.append(current_exp)
                current_exp = {'title': line, 'company': '', 'description': ''}
            elif len(line) > 20 and current_exp:
                current_exp['description'] = current_exp.get('description', '') + ' ' + line
        
        if current_exp:
            experience.append(current_exp)
        
        return experience[:5]  # Limit to 5 entries
    
    def _extract_education(self) -> List[Dict[str, Any]]:
        """Extract education"""
        education = []
        edu_keywords = ['education', 'academic', 'qualification']
        
        # Find education section
        edu_start = -1
        for i, line in enumerate(self.lines):
            if any(keyword in line.lower() for keyword in edu_keywords):
                edu_start = i
                break
        
        if edu_start == -1:
            return education
        
        # Extract education entries
        for i in range(edu_start + 1, min(edu_start + 10, len(self.lines))):
            line = self.lines[i]
            if len(line) > 10:
                education.append({'degree': line, 'institution': ''})
        
        return education[:3]  # Limit to 3 entries
    
    def _extract_certifications(self) -> List[Dict[str, str]]:
        """Extract certifications"""
        certifications = []
        cert_keywords = ['certification', 'certificate', 'license']
        
        for i, line in enumerate(self.lines):
            if any(keyword in line.lower() for keyword in cert_keywords):
                # Get next few lines
                for j in range(i + 1, min(i + 5, len(self.lines))):
                    if len(self.lines[j]) > 10:
                        certifications.append({'name': self.lines[j], 'issuer': ''})
        
        return certifications[:5]
    
    def _extract_languages(self) -> List[Dict[str, str]]:
        """Extract languages"""
        languages = []
        lang_keywords = ['language']
        
        common_languages = ['English', 'Vietnamese', 'French', 'Chinese', 'Japanese', 'Korean']
        
        for lang in common_languages:
            if lang.lower() in self.text.lower():
                languages.append({'language': lang, 'proficiency': 'Unknown'})
        
        return languages
    
    def _extract_social_links(self) -> Dict[str, str]:
        """Extract social media links"""
        links = {
            'linkedin': '',
            'github': '',
            'portfolio': '',
        }
        
        # LinkedIn
        linkedin_match = re.search(self.LINKEDIN_PATTERN, self.text, re.IGNORECASE)
        if linkedin_match:
            links['linkedin'] = linkedin_match.group(0)
        
        # GitHub
        github_match = re.search(self.GITHUB_PATTERN, self.text, re.IGNORECASE)
        if github_match:
            links['github'] = github_match.group(0)
        
        return links
    
    def _calculate_total_experience(self, work_experience: List[Dict]) -> Optional[float]:
        """Calculate total years of experience"""
        # Simplified calculation - can be improved by parsing dates
        if work_experience:
            return float(len(work_experience) * 2)  # Rough estimate: 2 years per job
        return None
    
    def _log(self, step: str, message: str, level: str = 'INFO'):
        """Log parsing steps"""
        ResumeParsingLog.objects.create(
            parsed_resume=self.parsed_resume,
            step=step,
            message=message,
            level=level
        )
