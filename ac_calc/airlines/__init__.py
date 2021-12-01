from collections import namedtuple
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
import json
from math import asin, cos, pow, radians, sin, sqrt

from ..aeroplan import AeroplanStatus, FareBrand
from ..locations import Airport


SegmentCalculation = namedtuple("SegmentCalculation", (
    "distance",
    "app", "app_earning_rate", "app_bonus_factor", "app_bonus",
    "sqm", "sqm_earning_rate",
))
EarthRadiusMi = 3959.0

FULL_BONUS_AIRLINES = {"air-canada", "copa-airlines", "united"}
FIXED25_BONUS_AIRLINES = {"austrian-airlines", "brussels-airlines", "lufthansa", "swiss"}


@dataclass
class Airline:

    id: str
    name: str
    region: str
    website: str
    logo: str
    star_alliance_member: bool
    codeshare_partner: bool
    earns_app: bool
    earns_sqm: bool
    earning_rates: dict

    def __eq__(self, other):
        return self.id == other.id

    def _distance(self, origin: Airport, destination: Airport):
        """Calculate the distance from origin to destination. If there isn't a pre-recorded
        Aeroplan distance, calculate the haversine distance.
        """

        if distance := origin.distances.get(destination.airport_code):
            return distance.distance or distance.old_distance
        else:
            d_lat = radians(destination.latitude - origin.latitude)
            d_lon = radians(destination.longitude - origin.longitude)
            origin_lat = radians(origin.latitude)
            destination_lat = radians(destination.latitude)

            a = pow(sin(d_lat / 2), 2) + pow(sin(d_lon / 2), 2) * cos(origin_lat) * cos(destination_lat)
            c = 2 * asin(sqrt(a))

            return EarthRadiusMi * c

    def _earning_rate(
        self,
        origin: Airport,
        destination: Airport,
        fare_brand: FareBrand,
        fare_class: str,
    ):
        region = self._region_for_segment(origin, destination)
        region_services = self.earning_rates.get(region, {})

        for fare_classes in region_services.values():
            if rate := fare_classes.get(fare_class) or fare_classes.get(fare_brand.name):
                return rate

        return 0

    def _region_for_segment(
        self,
        origin: Airport,
        destination: Airport,
    ):
        if self.id == "air-canada":
            if origin.country == destination.country == "Canada":
                return "Domestic"
            elif (
                (origin.country == "Canada" and destination.country == "United States")
                or (origin.country == "United States" and destination.country == "Canada")
            ):
                return "Transborder"
            else:
                return "International"
        elif self.id == "air-india":
            return "Domestic" if origin.country == destination.country == "India" else "International"
        elif self.id == "avianca":
            return "Domestic Colombia, Peru, Ecuador, and Intra-Central America" if origin.continent == destination.continent == "South America" else "All destinations"
        elif self.id == "eurowings-discover":
            return "Intra-European flights" if origin.continent == destination.continent == "Europe" else "Rest of the world"
        elif self.id == "south-african-airways":
            return "Domestic" if origin.country == destination.country == "South Africa" else "International"
        elif self.id == "virgin-australia":
            return "Domestic" if origin.country == destination.country == "Australia" else "International"
        elif self.id == "austrian-airlines":
            return "Intra-European flights" if origin.continent == destination.continent == "Europe" else "Rest of the world"
        elif self.id == "egyptair":
            return "Domestic" if origin.country == destination.country == "Egypt" else "International"
        elif self.id == "swiss":
            return "Intra-European flights" if origin.continent == destination.continent == "Europe" else "Rest of the world"
        elif self.id == "tap-air-portugal":
            lisbon_porto_codes = set(("LIS", "OPO", "PXO", "FNC"))
            return "Flights between Lisbon and Porto" if origin.airport_code in lisbon_porto_codes and destination.airport_code in lisbon_porto_codes else "All destinations"
        elif self.id == "asiana":
            return "Domestic South Korea" if origin.country == destination.country == "South Korea" else "International"
        elif self.id == "air-new-zealand":
            if origin.country == destination.country == "New Zealand":
                return "Domestic"
            elif origin.continent == destination.continent == "Oceania":
                return "Tasman"
            else:
                return "International"
        elif self.id == "lufthansa":
            return "Intra-European flights" if origin.continent == destination.continent == "Europe" else "Rest of the world"
        else:
            return "*"

    def calculate(
        self,
        origin: Airport,
        destination: Airport,
        fare_brand: FareBrand,
        fare_class: str,
        ticket_number: str,
        aeroplan_status: AeroplanStatus,
    ):
        distance = self._distance(origin, destination)
        if not distance:
            return SegmentCalculation(distance, 0, 0, 0, 0, 0, 0)

        app_earning_rate = self._earning_rate(origin, destination, fare_brand, fare_class)
        if self.id in FULL_BONUS_AIRLINES:
            app_bonus_factor = aeroplan_status.bonus_factor
        elif self.id in FIXED25_BONUS_AIRLINES:
            app_bonus_factor = max(0, min(aeroplan_status.bonus_factor, 0.25))
        else:
            app_bonus_factor = 0
        app = max(distance * app_earning_rate, aeroplan_status.min_earning_value) if self.earns_app else 0
        app_bonus = min(app, distance) * app_bonus_factor

        sqm_earning_rate = self._earning_rate(origin, destination, fare_brand, fare_class)
        sqm = max(distance * sqm_earning_rate, aeroplan_status.min_earning_value) if self.earns_sqm else 0

        return SegmentCalculation(
            distance,
            int(app),
            app_earning_rate,
            app_bonus_factor,
            int(app_bonus),
            int(sqm),
            sqm_earning_rate,
        )


class AirCanadaAirline(Airline):
    pass


@cache
def _load_airline_partners():
    with resources.open_text("ac_calc.airlines", "partners.json") as f:
        partners = json.load(f)

    return tuple(sorted((
        Airline(**partner)
        for partner in partners
    ), key=lambda airline: airline.name))


AirCanada = AirCanadaAirline(
    id="air-canada",
    name="Air Canada",
    region="Canada & U.S.",
    website="http://www.aircanda.com",
    logo=None,
    star_alliance_member=True,
    codeshare_partner=False,
    earns_app=True,
    earns_sqm=True,
    earning_rates={
        "Domestic": {
            "*": {
                "Basic": 0.10,
                "Standard": 0.25,
                "Flex": 1.0,
                "Comfort": 1.15,
                "Latitude": 1.25,
                "Premium Economy (Lowest)": 1.25,
                "Premium Economy (Flexible)": 1.25,
                "Business (Lowest)": 1.50,
                "Business (Flexible)": 1.50,
            },
        },
        "Transborder": {
            "*": {
                "Basic": 0.25,
                "Standard": 0.50,
                "Flex": 1.0,
                "Comfort": 1.15,
                "Latitude": 1.25,
                "Premium Economy (Lowest)": 1.25,
                "Premium Economy (Flexible)": 1.25,
                "Business (Lowest)": 1.50,
                "Business (Flexible)": 1.50,
            },
        },
        "International": {
            "*": {
                "Basic": 0.25,
                "Standard": 0.50,
                "Flex": 1.0,
                "Comfort": 1.15,
                "Latitude": 1.25,
                "Premium Economy (Lowest)": 1.25,
                "Premium Economy (Flexible)": 1.25,
                "Business (Lowest)": 1.50,
                "Business (Flexible)": 1.50,
            },
        },
    },
)


AIRLINES = (AirCanada,) + _load_airline_partners()
