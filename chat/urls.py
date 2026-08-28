from django.urls import path

from . import views

urlpatterns = [
    path("chat/threads/", views.ThreadListCreateView.as_view(), name="chat-threads"),
    path("chat/threads/<uuid:thread_uuid>/messages/", views.MessageListView.as_view(), name="chat-messages"),
    path("chat/threads/<uuid:thread_uuid>/send/", views.MessageSendView.as_view(), name="chat-send"),
    path("chat/threads/<uuid:thread_uuid>/read/", views.ReadView.as_view(), name="chat-read"),
    path("chat/threads/<uuid:thread_uuid>/report/", views.ReportView.as_view(), name="chat-report"),
]