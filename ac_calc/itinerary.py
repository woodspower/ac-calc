from dataclasses import dataclass, field

from .aeroplan import AeroplanStatus, FareBrand, DEFAULT_AEROPLAN_STATUS, DEFAULT_FARE_BRAND, DEFAULT_FARE_CLASS
from .airlines import Airline, DEFAULT_AIRLINE
from .locations import Airport, DEFAULT_ORIGIN_AIRPORT, DEFAULT_DESTINATION_AIRPORT


@dataclass
class Segment:
    airline: Airline = DEFAULT_AIRLINE
    origin: Airport = DEFAULT_ORIGIN_AIRPORT
    destination: Airport = DEFAULT_DESTINATION_AIRPORT
    fare_brand: FareBrand = DEFAULT_FARE_BRAND
    fare_class: str = DEFAULT_FARE_CLASS

    def calculate(
        self,
        ticket_number: str,
        aeroplan_status: AeroplanStatus
    ):
        return self.airline.calculate(
            self.origin,
            self.destination,
            self.fare_brand,
            self.fare_class,
            ticket_number,
            aeroplan_status,
        )
