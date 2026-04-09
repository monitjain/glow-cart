import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from django.contrib.auth.models import User

username = os.environ.get('ADMIN_USERNAME', 'MonitJain')
email    = os.environ.get('ADMIN_EMAIL', 'glowcart0811@gmail.com')
password = os.environ.get('ADMIN_PASSWORD', 'monitkagot@0811')

user, created = User.objects.get_or_create(
    username=username,
    defaults={'email': email, 'is_staff': True, 'is_superuser': True}
)

# Always update password and ensure staff/superuser flags are set
user.set_password(password)
user.email = email
user.is_staff = True
user.is_superuser = True
user.save()

if created:
    print(f'Superuser "{username}" created successfully.')
else:
    print(f'Superuser "{username}" password updated successfully.')
