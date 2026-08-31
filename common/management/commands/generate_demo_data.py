import os
import random
from urllib.request import urlretrieve
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import IntegrityError, transaction
from faker import Faker
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import django.db.models.fields.related as related

# Initialize faker
fake = Faker()

class Command(BaseCommand):
    help = 'Generates 500 demo data for each model and downloads images.'

    def handle(self, *args, **options):
        self.stdout.write("Starting data generation process...")
        
        # 1. Download Images
        self.stdout.write("Downloading dummy images...")
        media_dir = 'media/demo_images'
        os.makedirs(media_dir, exist_ok=True)
        images = []
        for i in range(1, 11):
            file_path = f"{media_dir}/image_{i}.jpg"
            if not os.path.exists(file_path):
                try:
                    url = f"https://picsum.photos/400/300?random={i}"
                    urlretrieve(url, file_path)
                    images.append(file_path)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Failed to download image {i}: {e}"))
            else:
                images.append(file_path)
                
        self.stdout.write(self.style.SUCCESS(f"Prepared {len(images)} images in {media_dir}"))

        models_list = apps.get_models()
        
        priority_apps = ['accounts', 'vendors', 'menus', 'addresses', 'orders', 'payments', 'delivery', 'promotions', 'reviews', 'support', 'chat', 'calls', 'analytics', 'common', 'notifications']
        def sort_key(model):
            app_label = model._meta.app_label
            if app_label in priority_apps:
                return priority_apps.index(app_label)
            return 100
        
        sorted_models = sorted(models_list, key=sort_key)
        
        exclude_apps = ['admin', 'auth', 'contenttypes', 'sessions', 'sites', 'account', 'socialaccount']
        
        MAX_RETRIES = 2
        for iteration in range(MAX_RETRIES):
            self.stdout.write(f"--- Iteration {iteration + 1} ---")
            for model in sorted_models:
                if model._meta.app_label in exclude_apps:
                    continue
                if 'base' in model.__name__.lower() or model._meta.abstract:
                    continue
                
                # Check current count
                if model.objects.count() >= 500:
                    continue
                
                self.stdout.write(f"Generating data for {model._meta.label}...")
                success_count = 0
                for _ in range(500):
                    if success_count >= 500:
                        break
                    
                    try:
                        with transaction.atomic():
                            obj_data = self.generate_fake_data(model, images)
                            if obj_data is not None:
                                obj = model(**obj_data)
                                obj.save()
                                success_count += 1
                    except Exception as e:
                        # Ignore constraints and just try to generate next
                        pass
                
                if success_count > 0:
                    self.stdout.write(self.style.SUCCESS(f"Added {success_count} records for {model._meta.label} (Total: {model.objects.count()})"))

        self.stdout.write(self.style.SUCCESS('Successfully completed data generation!'))

    def generate_fake_data(self, model, images):
        """Generates random data for model fields based on type."""
        data = {}
        for field in model._meta.fields:
            if field.primary_key or not field.editable or field.auto_created:
                continue
            
            if field.name == 'image_url' and images:
                data[field.name] = "/" + random.choice(images)
                continue
                
            if isinstance(field, related.ForeignKey) or isinstance(field, related.OneToOneField):
                related_model = field.related_model
                if related_model.objects.exists():
                    data[field.name] = related_model.objects.order_by('?').first()
                elif field.null:
                    data[field.name] = None
                else:
                    return None
                continue
            
            internal_type = field.get_internal_type()
            
            if field.choices:
                data[field.name] = random.choice([c[0] for c in field.choices])
            elif internal_type == 'CharField' or internal_type == 'SlugField':
                if 'email' in field.name.lower():
                    data[field.name] = fake.unique.email()
                elif 'name' in field.name.lower():
                    data[field.name] = fake.name()[:field.max_length]
                elif 'slug' in field.name.lower():
                    data[field.name] = fake.unique.slug()[:field.max_length]
                elif 'phone' in field.name.lower():
                    data[field.name] = fake.phone_number()[:field.max_length]
                elif 'currency' in field.name.lower():
                    data[field.name] = 'BDT'
                elif 'city' in field.name.lower():
                    data[field.name] = fake.city()[:field.max_length]
                elif 'address' in field.name.lower():
                    data[field.name] = fake.address()[:field.max_length]
                else:
                    data[field.name] = fake.word()[:field.max_length]
            elif internal_type == 'TextField':
                data[field.name] = fake.paragraph()
            elif internal_type == 'IntegerField' or internal_type == 'PositiveIntegerField' or internal_type == 'PositiveSmallIntegerField':
                data[field.name] = random.randint(0, 1000)
            elif internal_type == 'BigIntegerField':
                data[field.name] = random.randint(1000, 100000)
            elif internal_type == 'DecimalField':
                if field.max_digits and field.max_digits <= 5:
                    data[field.name] = Decimal(random.randrange(10, 500))/100
                else:
                    data[field.name] = Decimal(random.randrange(100, 10000))/100
            elif internal_type == 'FloatField':
                data[field.name] = random.uniform(1.0, 100.0)
            elif internal_type == 'BooleanField':
                data[field.name] = fake.boolean()
            elif internal_type == 'DateTimeField':
                data[field.name] = timezone.now() - timedelta(days=random.randint(0, 365))
            elif internal_type == 'DateField':
                data[field.name] = fake.date_this_year()
            elif internal_type == 'TimeField':
                data[field.name] = fake.time_object()
            elif internal_type == 'EmailField':
                data[field.name] = fake.unique.email()
            elif internal_type == 'URLField':
                data[field.name] = fake.url()
            elif internal_type == 'JSONField':
                data[field.name] = {"demo": "data", "value": random.randint(1, 100)}
            else:
                data[field.name] = None
                
        return data
