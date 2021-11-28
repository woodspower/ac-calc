from dataclasses import dataclass, field
from functools import cache
from importlib import resources
import json


from ..aeroplan import AeroplanStatus, FareBrand
from ..locations import Airport


@dataclass
class Airline:

    id: str
    name: str
    region: str
    website: str
    logo: str
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


@cache
def _load_airline_partners():
    with resources.open_text("ac_calc.airlines", "partners.json") as f:
        partners = json.load(f)

    return tuple((
        Airline(**partner)
        for partner in partners
    ))


AirCanada = AirCanadaAirline(
    id="air-canada",
    name="Air Canada",
    region="Canada & U.S.",
    website="http://www.aircanda.com",
    logo=None,
    star_alliance_member=True,
    earns_app=True,
    earns_sqm=True,
    earning_rates={
        "Basic-domestic": 0.10,
        "Basic-transborder": 0.25,
        "Basic-international": 0.25,
        "Standard-domestic": 0.25,
        "Standard-transborder": 0.50,
        "Standard-international": 0.50,
        "Flex": 1.0,
        "Comfort": 1.15,
        "Latitude": 1.25,
        "Premium Economy (Lowest)": 1.25,
        "Premium Economy (Flexible)": 1.25,
        "Business (Lowest)": 1.50,
        "Business (Flexible)": 1.50,
    },
)


AIRLINES = (AirCanada,) + _load_airline_partners()


DEFAULT_AIRLINE, DEFAULT_AIRLINE_INDEX = AirCanada, 0
