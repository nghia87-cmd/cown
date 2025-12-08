"""
Dynamic Skills Management with Redis Caching
Replaces hardcoded skills list in resume parser
"""

from django.core.management.base import BaseCommand
from apps.master_data.models import Skill, SkillCategory
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Load skills into database and cache for resume parser'

    def handle(self, *args, **options):
        """Load comprehensive skills list into database"""
        
        skills_data = {
            'Programming Languages': [
                'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust',
                'PHP', 'Ruby', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'Perl',
                'Dart', 'Objective-C', 'Shell', 'Bash', 'PowerShell'
            ],
            'Web Frameworks': [
                'Django', 'Flask', 'FastAPI', 'Express.js', 'Node.js', 'React', 'Vue.js',
                'Angular', 'Next.js', 'Nuxt.js', 'Svelte', 'Spring Boot', 'ASP.NET',
                'Laravel', 'Rails', 'Gin', 'Echo', 'Fiber'
            ],
            'Databases': [
                'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'SQLite',
                'Oracle', 'SQL Server', 'MariaDB', 'Cassandra', 'DynamoDB', 'Firebase',
                'Supabase', 'Neo4j', 'InfluxDB', 'TimescaleDB', 'CockroachDB'
            ],
            'Cloud Platforms': [
                'AWS', 'Google Cloud', 'Azure', 'DigitalOcean', 'Heroku', 'Vercel',
                'Netlify', 'Railway', 'Render', 'Fly.io', 'Cloudflare', 'Linode',
                'Vultr', 'OVH', 'Alibaba Cloud'
            ],
            'DevOps & Tools': [
                'Docker', 'Kubernetes', 'Jenkins', 'GitLab CI', 'GitHub Actions',
                'Terraform', 'Ansible', 'Chef', 'Puppet', 'Prometheus', 'Grafana',
                'ELK Stack', 'Nginx', 'Apache', 'HAProxy', 'Traefik', 'Consul', 'Vault'
            ],
            'Mobile Development': [
                'React Native', 'Flutter', 'Ionic', 'Xamarin', 'Android', 'iOS',
                'SwiftUI', 'Jetpack Compose', 'Cordova', 'Capacitor'
            ],
            'Data Science & ML': [
                'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Keras',
                'OpenCV', 'NLTK', 'SpaCy', 'Hugging Face', 'LangChain', 'Jupyter',
                'Apache Spark', 'Hadoop', 'Airflow', 'MLflow', 'Kubeflow'
            ],
            'Testing': [
                'Jest', 'Mocha', 'Pytest', 'JUnit', 'Selenium', 'Cypress', 'Playwright',
                'Postman', 'k6', 'Locust', 'Artillery', 'TestCafe', 'Vitest'
            ],
            'Version Control': [
                'Git', 'GitHub', 'GitLab', 'Bitbucket', 'SVN', 'Mercurial'
            ],
            'Design & UI/UX': [
                'Figma', 'Adobe XD', 'Sketch', 'Photoshop', 'Illustrator',
                'Tailwind CSS', 'Bootstrap', 'Material-UI', 'Ant Design', 'Chakra UI'
            ],
            'Message Queues': [
                'RabbitMQ', 'Kafka', 'Redis Pub/Sub', 'AWS SQS', 'Google Pub/Sub',
                'NATS', 'ActiveMQ', 'ZeroMQ'
            ],
            'Monitoring & Logging': [
                'Datadog', 'New Relic', 'Sentry', 'Splunk', 'Elastic APM', 'Jaeger',
                'Zipkin', 'OpenTelemetry'
            ],
            'APIs & Protocols': [
                'REST', 'GraphQL', 'gRPC', 'WebSocket', 'SOAP', 'HTTP', 'MQTT',
                'WebRTC', 'SSE'
            ],
            'Security': [
                'OAuth', 'JWT', 'SAML', 'OpenID Connect', 'SSL/TLS', 'VPN',
                'Penetration Testing', 'OWASP', 'Burp Suite', 'Wireshark'
            ],
            'Soft Skills': [
                'Agile', 'Scrum', 'Kanban', 'Leadership', 'Communication',
                'Problem Solving', 'Critical Thinking', 'Teamwork', 'Time Management',
                'Project Management', 'Mentoring', 'Code Review'
            ]
        }
        
        created_count = 0
        updated_count = 0
        
        for category_name, skills in skills_data.items():
            # Get or create category first
            category, cat_created = SkillCategory.objects.get_or_create(
                name=category_name,
                defaults={
                    'slug': category_name.lower().replace(' ', '-').replace('&', 'and'),
                    'description': f'{category_name} related skills',
                }
            )
            
            if cat_created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category_name}')
                )
            
            for skill_name in skills:
                skill, created = Skill.objects.get_or_create(
                    name=skill_name,
                    defaults={
                        'slug': skill_name.lower().replace(' ', '-').replace('.', '').replace('#', 'sharp').replace('+', 'plus'),
                        'category': category,
                        'skill_type': 'TECHNICAL' if category_name != 'Soft Skills' else 'SOFT',
                        'is_verified': True,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Created skill: {skill_name}')
                    )
                else:
                    # Update category if needed
                    if skill.category != category:
                        skill.category = category
                        skill.save()
                        updated_count += 1
        
        # Cache all skills for resume parser
        self._cache_skills()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created: {created_count}, Updated: {updated_count}'
            )
        )
    
    def _cache_skills(self):
        """Cache all active skills to Redis"""
        from apps.master_data.models import Skill
        
        skills = Skill.objects.filter(is_active=True).values_list('name', flat=True)
        skills_list = list(skills)
        
        # Cache for 24 hours
        cache.set('resume_parser:skills', skills_list, timeout=86400)
        
        # Also cache by category for advanced matching
        categories = Skill.objects.filter(is_active=True).values_list(
            'category', flat=True
        ).distinct()
        
        for category in categories:
            category_skills = list(
                Skill.objects.filter(
                    is_active=True,
                    category=category
                ).values_list('name', flat=True)
            )
            cache_key = f'resume_parser:skills:{category}'
            cache.set(cache_key, category_skills, timeout=86400)
        
        logger.info(f'Cached {len(skills_list)} skills to Redis')
        self.stdout.write(
            self.style.SUCCESS(f'Cached {len(skills_list)} skills to Redis')
        )
