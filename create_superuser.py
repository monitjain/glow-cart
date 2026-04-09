import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from django.contrib.auth.models import User

username = os.environ.get('ADMIN_USERNAME', 'MonitJain')
email    = os.environ.get('ADMIN_EMAIL', 'glowcart0811@gmail.com')
password = os.environ.get('ADMIN_PASSWORD', 'monitkagot@0811')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser "{username}" created successfully.')
else:
    print(f'Superuser "{username}" already exists.')
