# Seed the notification templates referenced by registered outbox handlers.
#
# notifications/handlers.py enqueues "order_placed_vendor" on every
# `order.placed` event (FR-NOT-01); services.enqueue raises
# `notify.unknown_template` when no active row exists, which previously made
# every order placement log a handler failure. Seeding here keeps the template
# present in fresh dev, test, and production databases.
from django.db import migrations

DEFAULT_TEMPLATES = [
    {
        "code": "order_placed_vendor",
        "channel": "email",
        "locale": "en",
        "subject": "New order #{order_pk}",
        "body": "You have a new order #{order_pk}. Total: {total}.",
        "active": True,
    },
]


def seed_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    for tpl in DEFAULT_TEMPLATES:
        # Only fill the gap; never clobber an operator-customized row.
        NotificationTemplate.objects.get_or_create(
            code=tpl["code"],
            defaults={k: v for k, v in tpl.items() if k != "code"},
        )


def unseed_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplate.objects.filter(
        code__in=[tpl["code"] for tpl in DEFAULT_TEMPLATES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
