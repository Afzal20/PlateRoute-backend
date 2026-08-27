from collections import defaultdict

from common.errors import DomainError
from menus.models import Option


def resolve_option(item, sel):
    """Resolve one {group_id, option_id} to stored snapshot fields (FR-CART-02)."""
    option = Option.objects.filter(
        group__item=item, group_id=sel.get("group_id"), id=sel.get("option_id"), available=True,
    ).first()
    if option is None:
        raise DomainError("cart.option_invalid", "A selected option is not available for this item.")
    return {"label": option.label, "price_delta_minor": option.price_delta_minor}


def check_group_rules(item, selected_options):
    """FR-CAT-04: every option group's min/max selection window is respected."""
    counts = defaultdict(int)
    for sel in selected_options:
        counts[sel.get("group_id")] += 1
    for group in item.groups.all():
        if not group.min_select <= counts.get(group.id, 0) <= group.max_select:
            raise DomainError("cart.group_rules", f"'{group.title}' requires {group.min_select}-{group.max_select} selection(s).")
