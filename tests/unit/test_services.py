import abc
from datetime import date, timedelta
import pytest
from allocation.adapters import repository
from allocation.domain import model
from allocation.service_layer import services, unit_of_work


class FakeRepository(repository.AbstractRepository):
    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)

    @staticmethod
    def for_batch(ref, sku, qty, eta=None):
        return FakeRepository(
            [
                model.Batch(ref, sku, qty, eta),
            ]
        )


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self, batches, *args):
        self.batches = FakeRepository(batches)
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_add_batch():
    uow = FakeUnitOfWork([])
    services.add_batch("b1", "CRUNCHY-ARMCHAIR", 100, None, uow)
    assert uow.batches.get("b1") is not None
    assert uow.committed


def test_allocate_returns_allocation():
    uow = FakeUnitOfWork([])
    services.add_batch("batch1", "COMPLICATED-LAMP", 100, None, uow)
    result = services.allocate("o1", "COMPLICATED-LAMP", 10, uow)
    assert result == "batch1"


def test_error_for_invalid_sku():
    uow = FakeUnitOfWork([])
    services.add_batch("b1", "AREALSKU", 100, None, uow)

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate("o1", "NONEXISTENTSKU", 10, uow)


def test_commits():
    uow = FakeUnitOfWork([])
    services.add_batch("b1", "OMINOUS-MIRROR", 100, None, uow)

    services.allocate("o1", "OMINOUS-MIRROR", 10, uow)
    assert uow.committed is True


today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_prefers_current_stock_batches_to_shipments():
    in_stock_batch = model.Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    shipment_batch = model.Batch("shipment-batch", "RETRO-CLOCK", 100, eta=tomorrow)
    uow = FakeUnitOfWork([in_stock_batch, shipment_batch])

    services.allocate("oref", "RETRO-CLOCK", 10, uow)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches():
    earliest = model.Batch("speedy-batch", "MINIMALIST-SPOON", 100, eta=today)
    medium = model.Batch("normal-batch", "MINIMALIST-SPOON", 100, eta=tomorrow)
    latest = model.Batch("slow-batch", "MINIMALIST-SPOON", 100, eta=later)
    uow = FakeUnitOfWork([medium, earliest, latest])

    services.allocate("order1", "MINIMALIST-SPOON", 10, uow)

    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = model.Batch("batch1", "SMALL-FORK", 10, eta=today)
    uow = FakeUnitOfWork([batch])

    services.allocate("order1", "SMALL-FORK", 10, uow)

    with pytest.raises(model.OutOfStock, match="SMALL-FORK"):
        services.allocate("order2", "SMALL-FORK", 1, uow)


def test_returns_allocated_batch_ref():
    in_stock_batch = model.Batch("in-stock-batch-ref", "HIGHBROW-POSTER", 100, eta=None)
    shipment_batch = model.Batch(
        "shipment-batch-ref", "HIGHBROW-POSTER", 100, eta=tomorrow
    )
    uow = FakeUnitOfWork([in_stock_batch, shipment_batch])

    allocation = services.allocate("oref", "HIGHBROW-POSTER", 10, uow)
    assert allocation == in_stock_batch.reference
