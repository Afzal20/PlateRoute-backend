from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError
from orders.models import Order
from rest_framework import status

from . import services
from .models import Message, Participant, Report, Thread


def _message_id(request):
    try:
        return int(request.data.get("message_id", 0))
    except (TypeError, ValueError):
        raise DomainError("chat.bad_message_id", "message_id must be an integer.", status.HTTP_400_BAD_REQUEST)


def _thread_for(request, thread_uuid):
    thread = get_object_or_404(Thread, uuid=thread_uuid)
    if not Participant.objects.filter(thread=thread, user=request.user, left_at__isnull=True).exists():
        raise DomainError("chat.not_participant", "You are not a member of this thread.", status.HTTP_403_FORBIDDEN)
    return thread


class ThreadListCreateView(APIView):
    """GET my threads with unread counts; POST bootstrap an order thread."""

    def get(self, request):
        threads = Thread.objects.filter(participants__user=request.user, participants__left_at__isnull=True) \
            .distinct().order_by("-last_message_at")
        data = []
        for thread in threads:
            last = thread.messages.order_by("-id").first() if thread.message_count else None
            data.append({
                "uuid": str(thread.uuid), "kind": thread.kind,
                "subject": thread.subject, "order": str(thread.order_id) if thread.order_id else None,
                "closed_at": thread.closed_at,
                "last_message": last.body if last else None, "last_message_at": thread.last_message_at,
                "unread": services.unread_count(thread, request.user),
            })
        return Response(data)

    def post(self, request):
        order = get_object_or_404(Order, uuid=request.data.get("order", ""))
        if order.customer_id != request.user.id and not order.branch.is_managed_by(request.user) \
                and not (request.user.is_staff or request.user.role in ("operator", "courier")):
            raise DomainError("chat.forbidden", "Not a participant of this order.", status.HTTP_403_FORBIDDEN)
        thread = services.get_or_create_order_thread(order, request.user)
        return Response({"uuid": str(thread.uuid)})


class MessageListView(APIView):
    """Paged history, newest-last ordering by id (DR-006 offset pagination)."""

    def get(self, request, thread_uuid):
        thread = _thread_for(request, thread_uuid)
        qs = thread.messages.filter(hidden_at__isnull=True).order_by("-id")
        before = request.GET.get("before_id")
        if before:
            qs = qs.filter(id__lt=before)
        qs = qs[:50]
        data = [{"id": m.id, "kind": m.kind, "sender": m.sender.email, "body": m.body,
                 "meta": m.meta, "created_at": m.created_at} for m in list(qs)[::-1]]
        return Response({"messages": data})


class MessageSendView(APIView):
    def post(self, request, thread_uuid):
        thread = _thread_for(request, thread_uuid)
        services.can_send(request.user, thread)
        message = services.send(request.user, thread, request.data.get("body", ""))
        return Response({"id": message.id, "body": message.body, "created_at": message.created_at}, status=status.HTTP_201_CREATED)


class ReadView(APIView):
    """POST {message_id} advances this user's watermark (monotonic)."""

    def post(self, request, thread_uuid):
        thread = _thread_for(request, thread_uuid)
        services.advance_watermark(request.user, thread, message_id=_message_id(request))
        return Response({"unread": services.unread_count(thread, request.user)})


class ReportView(APIView):
    def post(self, request, thread_uuid):
        thread = _thread_for(request, thread_uuid)
        message = get_object_or_404(Message.objects.filter(thread=thread), id=_message_id(request))
        Report.objects.create(message=message, reported_by=request.user, reason=request.data.get("reason", "abuse"))
        return Response({"detail": "reported"}, status=status.HTTP_201_CREATED)