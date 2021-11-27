from ..aeroplan import AeroplanStatus, FareBrand
from ..data import Airport


class Carrier(object):

    def __init__(
        self,
        name: str,
        codes=None,
        status_factors: dict={},
    ):
        self.name = name
        self.codes = codes if codes else (self.__class__.__name__,)
        self.status_factors = status_factors

    def __eq__(self, other):
        return self.name == other.name

    def status_factor(self, fare_brand: FareBrand, fare_basis: str):
        return factors[fare_basis[0]]

    def redeemable_factor(self, fare_brand: FareBrand, fare_basis: str):
        return self.status_factor(fare_brand, fare_basis)

    def calculate(
        self,
        origin: Airport,
        destination: Airport,
        fare_brand: FareBrand,
        fare_basis: str,
        ticket_number: str,
        aeroplan_status: AeroplanStatus,
    ):
        return 0.0
