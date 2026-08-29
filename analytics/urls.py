from django.urls import path

from . import views

urlpatterns = [path("reports/branches/<uuid:branch_uuid>/", views.BranchReportView.as_view(), name="branch-report")]