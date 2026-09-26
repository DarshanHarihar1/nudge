import uuid

from bot.handlers.expense import CB_CAT, pack_uuid, unpack_uuid


def test_category_callback_fits_telegram_limit_and_round_trips():
    expense_id, category_id = str(uuid.uuid4()), str(uuid.uuid4())
    data = f"{CB_CAT}{pack_uuid(expense_id)}:{pack_uuid(category_id)}"
    assert len(data.encode()) <= 64  # Telegram rejects the whole message above this
    packed_expense, packed_category = data[len(CB_CAT):].split(":")
    assert unpack_uuid(packed_expense) == expense_id
    assert unpack_uuid(packed_category) == category_id
