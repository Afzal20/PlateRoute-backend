from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError
from orders.models import Order

from .models import Ticket, TicketMessage


class TicketView(APIView):
    """Open / list / status tickets (customer owns theirs; operators see all)."""

    def get(self, request):
        is_operator = request.user.is_staff or request.user.role == "operator"
        tickets = Ticket.objects.all() if is_operator else Ticket.objects.filter(opened_by=request.user)
        return Response([
            {"uuid": str(t.uuid), "subject": t.subject, "category": t.category, "priority": t.priority,
             "status": t.status, "order": str(t.order.uuid) if t.order_id else None, "created_at": t.created_at}
            for t in tickets.order_by("-created_at")
        ])

    def post(self, request):
        order = None
        if ref := request.data.get("order"):
            order = get_object_or_404(Order, uuid=ref)
            if order.customer_id != request.user.id and not (request.user.is_staff or request.user.role == "operator"):
                raise DomainError("ticket.forbidden", "Not your order.", status.HTTP_403_FORBIDDEN)
        ticket = Ticket.objects.create(opened_by=request.user, order=order,
                                       category=request.data.get("category", Ticket.Category.OTHER),
                                       subject=(request.data.get("subject") or "Support")[:150])
        body = (request.data.get("message") or "").strip()
        if body:
            TicketMessage.objects.create(ticket=ticket, sender=request.user, body=body)
        return Response({"uuid": str(ticket.uuid), "status": ticket.status}, status=status.HTTP_201_CREATED)


class TicketDetailView(APIView):
    """Thread of messages; operators see internal notes, customers do not."""

    def get(self, request, uuid):
        ticket = get_object_or_404(Ticket, uuid=uuid)
        is_operator = request.user.is_staff or request.user.role == "operator"
        if ticket.opened_by_id != request.user.id and not is_operator:
            raise DomainError("ticket.forbidden", "Not your ticket.", status.HTTP_403_FORBIDDEN)
        messages = ticket.messages.all()
        if not is_operator:
            messages = messages.filter(internal_note=False)
        return Response({
            "uuid": str(ticket.uuid), "status": ticket.status, "priority": ticket.priority,
            "messages": [{"sender": m.sender.email, "body": m.body, "internal": m.internal_note, "created_at": m.created_at}
                         for m in messages],
        })

    def post(self, request, uuid):
        ticket = get_object_or_404(Ticket, uuid=uuid)
        is_operator = request.user.is_staff or request.user.role == "operator"
        if ticket.opened_by_id != request.user.id and not is_operator:
            raise DomainError("ticket.forbidden", "Not your ticket.", status.HTTP_403_FORBIDDEN)
        note = bool(request.data.get("internal_note")) and is_operator
        TicketMessage.objects.create(ticket=ticket, sender=request.user,
                                     body=(request.data.get("message") or "")[:4000], internal_note=note)
        if is_operator and request.data.get("status"):
            ticket.status = request.data["status"]
            ticket.save(update_fields=["status"])
        return Response({"detail": "added"}, status=status.HTTP_201_CREATED)