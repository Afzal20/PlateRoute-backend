from django.urls import path

from . import views

urlpatterns = [
    path("reviews/", views.ReviewCreateView.as_view(), name="review-create"),
    path("reviews/branches/<uuid:branch_uuid>/", views.ReviewListView.as_view(), name="review-list"),
    path("reviews/<int:pk>/reply/", views.ReviewReplyView.as_view(), name="review-reply"),
]