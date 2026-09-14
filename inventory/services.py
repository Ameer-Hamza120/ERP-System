from .models import StockMovement


def record_stock_movement(item, warehouse, quantity, movement_type, user, balance_after,
                           reference_document="", reference_number="", reason=""):
    StockMovement.objects.create(
        item=item, warehouse=warehouse, quantity=quantity, balance_after=balance_after,
        movement_type=movement_type, reference_document=reference_document,
        reference_number=reference_number, user=user, reason=reason,
    )
