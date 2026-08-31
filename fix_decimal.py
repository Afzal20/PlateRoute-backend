import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection

queries = [
    "UPDATE vendors_branch SET avg_rating = 4.5 WHERE avg_rating > 9.99;",
    "UPDATE analytics_dailybranchmetrics SET completion_ratio = 0.9 WHERE completion_ratio > 9.9999;"
]

with connection.cursor() as cursor:
    for q in queries:
        cursor.execute(q)
print("Decimals fixed!")
