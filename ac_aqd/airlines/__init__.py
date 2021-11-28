from dataclasses import dataclass, field

from ..aeroplan import AeroplanStatus, FareBrand
from ..data import Airport


@dataclass
class Airline:

    id: str
    name: str
    region: str
    website: str
    star_alliance_member: bool
    earns_app: bool
    earns_sqm: bool
    earning_rates: dict

    def __eq__(self, other):
        return self.id == other.id

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


class AirCanadaAirline(Airline):
    pass


AirCanada = AirCanadaAirline("Air Canada")


AIRLINES = (AirCanada,)


DEFAULT_AIRLINE, DEFAULT_AIRLINE_INDEX = AirCanada, 0
