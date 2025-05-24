# calculators/asian_calculator.py

import sys
import pandas as pd
import requests
from geopy.geocoders import Nominatim

EU_POSTAL_FILE = "data/eu_only.txt"
EU_RATES_FILE = "data/eu_tr_base_rates_v2.csv"
BACKHAUL_FILE = "data/backhaul_params.csv"
ASIA_RATES_FILE = "data/central_asia_cities.csv"
TERMINAL_COST = 50
MAX_LDM = 10

class AsianFreightCalculator:
    def __init__(self):
        self.postal_db = self.load_eu_postal_codes()
        self.rates = self.load_base_rates()
        self.backhaul = self.load_backhaul_params()
        self.asia_df = self.load_asia_rates()
        self.geolocator = Nominatim(user_agent="freight_calc_pro")

    def load_eu_postal_codes(self):
        return pd.read_csv(EU_POSTAL_FILE, sep='\t', header=None,
                           usecols=[0,1,2,9,10],
                           names=['country_code','postal_code','place_name','latitude','longitude'],
                           dtype={'postal_code': 'str'})

    def load_base_rates(self):
        df = pd.read_csv(EU_RATES_FILE)
        return df.set_index('country_code').to_dict('index')

    def load_backhaul_params(self):
        df = pd.read_csv(BACKHAUL_FILE)
        return df.set_index('country_code').to_dict('index')

    def load_asia_rates(self):
        return pd.read_csv(ASIA_RATES_FILE)

    def get_route_distance(self, origin, destination):
        lon1, lat1 = origin[1], origin[0]
        lon2, lat2 = destination[1], destination[0]
        url = f"http://router.project-osrm.org/route/v1/car/{lon1},{lat1};{lon2},{lat2}"
        response = requests.get(url, timeout=10)
        data = response.json()
        return data['routes'][0]['distance'] / 1000 if data.get('routes') else None

    def get_total_route_distance(self, origin_coords, asia_city_name):
        # Gebze coordinates
        gebze = self.geolocator.geocode("41400 Gebze Türkiye")
        if not gebze:
            raise ValueError("Gebze location not found!")
        gebze_coords = (gebze.latitude, gebze.longitude)

        # Geocode the Asian city
        asia_city = self.geolocator.geocode(asia_city_name)
        if not asia_city:
            raise ValueError("Asian city location not found!")
        asia_coords = (asia_city.latitude, asia_city.longitude)

        # Calculate both legs
        dist_eu_to_gebze = self.get_route_distance(origin_coords, gebze_coords)
        dist_gebze_to_asia = self.get_route_distance(gebze_coords, asia_coords)

        if not dist_eu_to_gebze or not dist_gebze_to_asia:
            raise ValueError("Route distance calculation error!")

        return dist_eu_to_gebze + dist_gebze_to_asia

    def calculate_eu_leg(self, distance_km, ldm, weight_kg, country):
        rate = self.rates[country]
        base_cost = max(
            rate['base_rate_per_loading_meter'] * ldm,
            rate['base_rate_per_km'] * distance_km * ldm
        ) * rate['coefficient']
        bh_params = self.backhaul.get(country, {'backhaul_probability': 0.5, 'max_discount': 0.2})
        discount = bh_params['backhaul_probability'] * bh_params['max_discount']
        discounted_cost = base_cost * (1 - discount)
        insurance = discounted_cost * 0.05
        co2_surcharge = weight_kg * 0.008
        return discounted_cost + insurance + co2_surcharge

    def calculate_asia_leg(self, asia_country, asia_city, ldm, weight_kg):
        row = self.asia_df[
            (self.asia_df['country_code'] == asia_country) &
            (self.asia_df['city'] == asia_city)
        ]
        if row.empty:
            raise ValueError("Asia city not found!")
        row = row.iloc[0]
        actual_ldm = max(ldm, weight_kg / 1850)
        transport_cost = row['rate_per_km'] * row['base_distance_km'] * actual_ldm
        customs_cost = row['customs_per_ldm'] * actual_ldm
        return transport_cost + customs_cost

    def calculate_terminal_cost(self, weight_kg):
        tons = int(weight_kg // 1000)
        if weight_kg % 1000 != 0:
            tons += 1
        return tons * TERMINAL_COST

    def calculate(self, eu_postal, eu_country, asia_country, asia_city, ldm, weight):
        if ldm < 1 or ldm > MAX_LDM:
            raise ValueError(f"LDM must be between 1 and {MAX_LDM}")
        if weight > ldm * 1850 or weight <= 0:
            raise ValueError(f"Max weight for {ldm} LDM: {ldm*1850} kg")

        location_data = self.postal_db[
            (self.postal_db['postal_code'] == eu_postal) &
            (self.postal_db['country_code'] == eu_country)
        ]
        if location_data.empty:
            raise ValueError("Origin location not found!")

        origin = (float(location_data.iloc[0]['latitude']), float(location_data.iloc[0]['longitude']))
        full_distance = self.get_total_route_distance(origin, f"{asia_city}, {asia_country}")

        eu_cost = self.calculate_eu_leg(full_distance, ldm, weight, eu_country)
        asia_cost = self.calculate_asia_leg(asia_country, asia_city, ldm, weight)
        terminal_cost = self.calculate_terminal_cost(weight)
        total = eu_cost + asia_cost + terminal_cost

        return {
            'total': round(total, 2),
            'distance': round(full_distance, 2),
            'chargeable_ldm': max(ldm, round(weight / 1850, 2))
        }
