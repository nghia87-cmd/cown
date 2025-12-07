"""
Management command to rebuild Elasticsearch indexes
Usage: python manage.py rebuild_index
"""

from django.core.management.base import BaseCommand
from django_elasticsearch_dsl.registries import registry


class Command(BaseCommand):
    help = 'Rebuild Elasticsearch indexes for jobs and companies'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            type=str,
            help='Comma-separated list of models to index (e.g., Job,Company)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild - delete and recreate indexes',
        )
        parser.add_argument(
            '--parallel',
            action='store_true',
            help='Index documents in parallel',
        )
    
    def handle(self, *args, **options):
        models = options.get('models', '').split(',') if options.get('models') else []
        force = options.get('force', False)
        parallel = options.get('parallel', False)
        
        if force:
            self.stdout.write('Deleting indexes...')
            for index in registry.get_indices(models):
                index.delete(ignore=404)
                self.stdout.write(f'  Deleted {index._name}')
            
            self.stdout.write('Creating indexes...')
            for index in registry.get_indices(models):
                index.create()
                self.stdout.write(f'  Created {index._name}')
        
        self.stdout.write('Indexing documents...')
        for doc in registry.get_documents(models):
            self.stdout.write(f'  Indexing {doc.Django.model.__name__}...')
            
            qs = doc().get_queryset()
            count = qs.count()
            
            if parallel:
                doc().update(qs, parallel=True)
            else:
                doc().update(qs)
            
            self.stdout.write(self.style.SUCCESS(f'    Indexed {count} documents'))
        
        self.stdout.write(self.style.SUCCESS('Indexing complete!'))
