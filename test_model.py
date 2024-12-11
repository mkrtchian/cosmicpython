from datetime import date, timedelta
import pytest

# from model import ...

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_allocating_to_a_batch_reduces_the_available_quantity():
    pytest.fail("todo")
