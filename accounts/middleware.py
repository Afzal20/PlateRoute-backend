from django.core.cache import cache
from django.http import JsonResponse


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = self.get_client_ip(request)
        key = f"rate_limit:{ip}"
        count = cache.get(key, 0)

        if count >= 100:
            return JsonResponse({"error": "Rate limit exceeded"}, status=429)

        cache.set(key, count + 1, 60)
        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded.split(",")[0] if x_forwarded else request.META.get("REMOTE_ADDR")
