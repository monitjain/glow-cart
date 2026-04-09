from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os


class Command(BaseCommand):
    help = 'Create or update superuser from environment variables'

    def handle(self, *args, **kwargs):
        username = os.environ.get('ADMIN_USERNAME', 'MonitJain')
        email    = os.environ.get('ADMIN_EMAIL', 'glowcart0811@gmail.com')
        password = os.environ.get('ADMIN_PASSWORD', 'monitkagot@0811')

        user, created = User.objects.get_or_create(username=username)
        user.email        = email
        user.is_staff     = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" updated.'))
