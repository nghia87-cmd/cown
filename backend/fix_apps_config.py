"""
Script to fix apps.py config for all apps
"""

import os
from pathlib import Path

# List of apps to update
apps = [
    'notifications', 'payments', 'analytics', 'messaging', 'reviews',
    'saved_jobs', 'recommendations', 'search', 'storage', 'email_service',
    'export', 'audit_logs', 'reports'
]

apps_dir = Path('apps')

for app_name in apps:
    app_path = apps_dir / app_name / 'apps.py'
    
    if app_path.exists():
        # Read current content
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert app_name to CamelCase for class name
        class_name = ''.join(word.capitalize() for word in app_name.split('_')) + 'Config'
        
        # Replace name = 'app_name' with name = 'apps.app_name'
        old_name = f"name = '{app_name}'"
        new_name = f"name = 'apps.{app_name}'"
        
        if old_name in content:
            content = content.replace(old_name, new_name)
            
            # Add verbose_name if not present
            if 'verbose_name' not in content:
                # Insert verbose_name before the last line
                lines = content.strip().split('\n')
                verbose_name_line = f"    verbose_name = '{app_name.replace('_', ' ').title()}'"
                lines.insert(-1, verbose_name_line)
                content = '\n'.join(lines) + '\n'
            
            # Write updated content
            with open(app_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✓ Updated {app_name}/apps.py")
        else:
            print(f"✗ Skipped {app_name}/apps.py (already updated or different format)")
    else:
        print(f"✗ Not found: {app_path}")

print("\nDone!")
