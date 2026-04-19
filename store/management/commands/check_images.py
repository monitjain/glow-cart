from django.core.management.base import BaseCommand
from store.models import Product


class Command(BaseCommand):
    help = 'List all products with their image URLs'

    def handle(self, *args, **kwargs):
        products = Product.objects.all()
        if not products:
            self.stdout.write('No products found.')
            return
        for p in products:
            try:
                url = p.image.url if p.image else 'NO IMAGE'
            except Exception as e:
                url = f'ERROR: {e}'
            self.stdout.write(f'#{p.id} {p.name} → {url}')
