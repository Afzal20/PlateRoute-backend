import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from menus.models import Category, Item, Option, OptionGroup
from vendors.models import Branch

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_FILE = BASE_DIR / "data" / "foods_200.json"


class Command(BaseCommand):
    help = "Loads 200 food items from formatted JSON into backend database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing imported items before loading",
        )

    def handle(self, *args, **options):
        if not DATA_FILE.exists():
            self.stdout.write(self.style.ERROR(f"Data file not found: {DATA_FILE}"))
            return

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            food_items = json.load(f)

        self.stdout.write(f"Loaded {len(food_items)} food items from {DATA_FILE.name}.")

        branches = list(Branch.objects.filter(is_accepting=True)[:25])
        if not branches:
            branches = list(Branch.objects.all()[:25])
        if not branches:
            self.stdout.write(self.style.ERROR("No branches found in database!"))
            return

        self.stdout.write(f"Distributing 200 items across {len(branches)} vendor branches.")

        # Purge old fake demo items that have invalid/garbage image URLs
        invalid_items = Item.objects.exclude(image_url__startswith="http").exclude(image_url__startswith="/media")
        if invalid_items.exists():
            deleted_count = invalid_items.count()
            invalid_items.delete()
            self.stdout.write(f"Purged {deleted_count} old demo items with invalid image URLs.")

        if options["clear"]:
            self.stdout.write("Clearing all existing items before reload...")
            Item.objects.all().delete()

        created_items_count = 0
        created_categories_count = 0
        created_options_count = 0

        with transaction.atomic():
            for idx, food in enumerate(food_items):
                branch = branches[idx % len(branches)]
                cat_name = food.get("category", "General")

                category, cat_created = Category.objects.get_or_create(
                    branch=branch,
                    name=cat_name,
                    defaults={"position": idx % 10}
                )
                if cat_created:
                    created_categories_count += 1

                # Prioritize full HTTPS remote URL so image_url is an authentic web URL
                remote_url = food.get("remote_primary_image") or food.get("image_url", "")
                local_path = food.get("image_url", "")
                extra_urls = food.get("remote_extra_images") or food.get("extra_images", [])

                item, item_created = Item.objects.update_or_create(
                    branch=branch,
                    name=food["name"],
                    defaults={
                        "category": category,
                        "description": food.get("description", ""),
                        "image_url": remote_url,
                        "local_image_url": local_path,
                        "extra_images": extra_urls,
                        "base_price_minor": food.get("base_price_minor", 25000),
                        "currency": food.get("currency", "BDT"),
                        "available": True,
                        "sort_key": food.get("index", idx),
                    }
                )

                if item_created or item:
                    created_items_count += 1

                # Option groups
                option_groups_data = food.get("option_groups", [])
                if option_groups_data:
                    item.groups.all().delete()
                    for g_data in option_groups_data:
                        og = OptionGroup.objects.create(
                            item=item,
                            title=g_data["title"],
                            min_select=g_data.get("min_select", 0),
                            max_select=g_data.get("max_select", 1),
                        )
                        for opt_data in g_data.get("options", []):
                            Option.objects.create(
                                group=og,
                                label=opt_data["label"],
                                price_delta_minor=opt_data.get("price_delta_minor", 0),
                                is_default=opt_data.get("is_default", False),
                                available=opt_data.get("available", True),
                            )
                            created_options_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Database population completed successfully!\n"
                f"- Total Items Added/Updated: {created_items_count}\n"
                f"- Total Categories Managed: {created_categories_count}\n"
                f"- Total Customization Options Added: {created_options_count}\n"
                f"- Current Item count in DB: {Item.objects.count()}"
            )
        )
