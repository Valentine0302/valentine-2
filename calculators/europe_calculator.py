import pandas as pd
import json
import os
from geopy.geocoders import Nominatim
import requests
import datetime
import time
import pickle
import math

# Константы
REGIONS_FILE = os.path.join("data", "europe_regions.csv")
RATES_FILE = os.path.join("data", "europe_regional_rates.csv")
REGION_DETAILS_FILE = os.path.join("data", "region_details.json")
CORRECTION_FACTORS_FILE = os.path.join("data", "correction_factors.json")
DENSITY_FACTOR = 1850  # кг/м для расчета тарифицируемого объема
CACHE_FILE = os.path.join("data", "geocode_cache.pkl")

class FreightCalculator:
    def __init__(self):
        """Инициализация калькулятора ставок"""
        self.regions_dict = {}
        self.rates_dict = {}
        self.region_details = {}
        self.correction_factors = {}
        self.geocode_cache = {}
        self.load_data()
        self.load_geocode_cache()
        
    def load_data(self):
        """Загрузка данных о регионах и ставках"""
        try:
            # Загружаем соответствие почтовых индексов и регионов
            regions_df = pd.read_csv(REGIONS_FILE)
            
            # Создаем словарь для быстрого поиска региона по почтовому индексу и стране
            for _, row in regions_df.iterrows():
                key = f"{row['country_code']}_{row['postal_code']}"
                self.regions_dict[key] = {
                    'region': row['region'],
                    'place_name': row['place_name'],
                    'country_code': row['country_code']
                }
            
            # Загружаем базовые ставки между регионами
            rates_df = pd.read_csv(RATES_FILE)
            
            # Преобразуем JSON-строки обратно в словари
            rates_df['seasonal_factors'] = rates_df['seasonal_factors'].apply(json.loads)
            rates_df['urgency_factors'] = rates_df['urgency_factors'].apply(json.loads)
            
            # Создаем словарь для быстрого поиска ставки по паре регионов
            for _, row in rates_df.iterrows():
                key = (row['from_region'], row['to_region'])
                self.rates_dict[key] = {
                    'distance_km': row['distance_km'],
                    'base_rate_per_ldm': row['base_rate_per_ldm'],
                    'base_rate_per_km': row['base_rate_per_km'],
                    'coefficient': row['coefficient'],
                    'seasonal_factors': row['seasonal_factors'],
                    'urgency_factors': row['urgency_factors']
                }
            
            # Загружаем детали регионов
            with open(REGION_DETAILS_FILE, 'r', encoding='utf-8') as f:
                self.region_details = json.load(f)
            
            # Загружаем коэффициенты корректировки
            with open(CORRECTION_FACTORS_FILE, 'r', encoding='utf-8') as f:
                self.correction_factors = json.load(f)
                
            print(f"Загружено {len(self.regions_dict)} почтовых индексов и {len(self.rates_dict)} ставок")
            
        except Exception as e:
            print(f"Ошибка загрузки данных: {str(e)}")
            raise
    
    def load_geocode_cache(self):
        """Загрузка кэша геокодирования"""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'rb') as f:
                    self.geocode_cache = pickle.load(f)
                print(f"Загружено {len(self.geocode_cache)} кэшированных координат")
        except Exception as e:
            print(f"Ошибка загрузки кэша: {str(e)}")
            self.geocode_cache = {}
    
    def save_geocode_cache(self):
        """Сохранение кэша геокодирования"""
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(self.geocode_cache, f)
        except Exception as e:
            print(f"Ошибка сохранения кэша: {str(e)}")
    
    def get_coordinates(self, address):
        """Получение координат через OpenStreetMap с кэшированием и повторными попытками"""
        # Проверяем кэш
        if address in self.geocode_cache:
            return self.geocode_cache[address]
        
        # Если адрес не в кэше, делаем запрос с повторными попытками
        max_retries = 3
        retry_delay = 2  # секунды
        
        for attempt in range(max_retries):
            try:
                geolocator = Nominatim(user_agent="europe_freight_calculator_v3")
                location = geolocator.geocode(address, timeout=10)  # Увеличенный таймаут
                
                if location:
                    coords = (location.latitude, location.longitude)
                    # Сохраняем в кэш
                    self.geocode_cache[address] = coords
                    self.save_geocode_cache()
                    return coords
                
                # Если локация не найдена, но запрос выполнен успешно
                if attempt == max_retries - 1:
                    print(f"Адрес не найден: {address}")
                    return (None, None)
                
            except Exception as e:
                print(f"Ошибка геокодирования (попытка {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    return (None, None)
                
                # Ждем перед следующей попыткой
                time.sleep(retry_delay)
                retry_delay *= 2  # Экспоненциальная задержка
        
        return (None, None)
    
    def get_road_distance(self, coord1, coord2):
        """Получение реального расстояния через OSRM с повторными попытками"""
        if None in coord1 or None in coord2:
            return None
            
        max_retries = 3
        retry_delay = 2  # секунды
        
        for attempt in range(max_retries):
            try:
                # Формат: lon1,lat1;lon2,lat2
                url = f"http://router.project-osrm.org/route/v1/car/" \
                      f"{coord1[1]},{coord1[0]};{coord2[1]},{coord2[0]}?overview=full"
                
                response = requests.get(url, timeout=15)  # Увеличенный таймаут
                
                if response.status_code != 200:
                    print(f"OSRM Error: HTTP {response.status_code} (попытка {attempt+1}/{max_retries})")
                    if attempt == max_retries - 1:
                        return None
                else:
                    data = response.json()
                    
                    if not data.get('routes') or data['code'] != 'Ok':
                        print(f"No route found (попытка {attempt+1}/{max_retries})")
                        if attempt == max_retries - 1:
                            return None
                    else:
                        return data['routes'][0]['distance'] / 1000  # в км
                
            except Exception as e:
                print(f"OSRM Error (попытка {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    return None
            
            # Ждем перед следующей попыткой
            time.sleep(retry_delay)
            retry_delay *= 2  # Экспоненциальная задержка
        
        return None
    
    def get_region_by_postal(self, postal_code, country_code):
        """Определение региона по почтовому индексу и коду страны"""
        key = f"{country_code}_{postal_code}"
        region_info = self.regions_dict.get(key)
        if region_info:
            return region_info['region'], region_info['place_name']
        
        # Если точное совпадение не найдено, ищем по первым цифрам
        for i in range(len(postal_code) - 1, 0, -1):
            prefix = postal_code[:i]
            for k, v in self.regions_dict.items():
                if k.startswith(f"{country_code}_{prefix}"):
                    return v['region'], v['place_name']
        
        return None, None
    
    def get_distance_from_matrix(self, from_region, to_region):
        """Получение расстояния из матрицы ставок"""
        # Ищем прямую ставку
        rate_info = self.rates_dict.get((from_region, to_region))
        if rate_info:
            return rate_info['distance_km']
        
        # Если прямой ставки нет, ищем обратную (может быть асимметрия, но для расстояния это не критично)
        rate_info = self.rates_dict.get((to_region, from_region))
        if rate_info:
            return rate_info['distance_km']
        
        # Если ставки нет в обоих направлениях, используем приблизительное расстояние
        # на основе координат центров регионов
        from_details = self.region_details.get(from_region, {})
        to_details = self.region_details.get(to_region, {})
        
        if from_details and to_details:
            from_lat = from_details.get('center_lat')
            from_lon = from_details.get('center_lon')
            to_lat = to_details.get('center_lat')
            to_lon = to_details.get('center_lon')
            
            if from_lat and from_lon and to_lat and to_lon:
                # Рассчитываем расстояние по формуле гаверсинуса
                
                # Переводим в радианы
                from_lat_rad = math.radians(from_lat)
                from_lon_rad = math.radians(from_lon)
                to_lat_rad = math.radians(to_lat)
                to_lon_rad = math.radians(to_lon)
                
                # Разница координат
                delta_lat = to_lat_rad - from_lat_rad
                delta_lon = to_lon_rad - from_lon_rad
                
                # Формула гаверсинуса
                a = math.sin(delta_lat/2)**2 + math.cos(from_lat_rad) * math.cos(to_lat_rad) * math.sin(delta_lon/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                
                # Радиус Земли в км
                R = 6371
                
                # Расстояние по прямой
                distance = R * c
                
                # Учитываем дорожный фактор (дороги обычно на 20-40% длиннее прямой)
                road_factor = 1.3
                road_distance = distance * road_factor
                
                return round(road_distance, 1)
        
        # Если не удалось рассчитать расстояние, возвращаем значение по умолчанию
        return 1000
    
    def get_distance_correction_factor(self, distance_km):
        """Получение коэффициента корректировки по расстоянию"""
        if distance_km < 500:
            return self.correction_factors['distance_factors']['0-500']
        elif distance_km < 1000:
            return self.correction_factors['distance_factors']['500-1000']
        elif distance_km < 1500:
            return self.correction_factors['distance_factors']['1000-1500']
        elif distance_km < 2000:
            return self.correction_factors['distance_factors']['1500-2000']
        else:
            return self.correction_factors['distance_factors']['2000+']
    
    def get_ldm_correction_factor(self, ldm):
        """Получение коэффициента корректировки по LDM"""
        if ldm <= 1:
            return self.correction_factors['ldm_factors']['0-1']
        elif ldm <= 5:
            return self.correction_factors['ldm_factors']['1-5']
        elif ldm <= 10:
            return self.correction_factors['ldm_factors']['5-10']
        else:
            return self.correction_factors['ldm_factors']['10+']
    
    def get_weight_correction_factor(self, weight_kg):
        """Получение коэффициента корректировки по весу"""
        if weight_kg <= 1000:
            return self.correction_factors['weight_factors']['0-1000']
        elif weight_kg <= 3000:
            return self.correction_factors['weight_factors']['1000-3000']
        elif weight_kg <= 6000:
            return self.correction_factors['weight_factors']['3000-6000']
        else:
            return self.correction_factors['weight_factors']['6000+']
    
    def calculate_rate(self, distance_km, ldm, weight_kg, from_region, to_region, month=None):
        """Расчёт стоимости перевозки с учетом региональных ставок и рыночных корректировок"""
        # Расчет тарифицируемого объема (максимум из LDM и вес/1850)
        chargeable_ldm = max(ldm, weight_kg / DENSITY_FACTOR)
        
        # Проверяем, есть ли прямая ставка между регионами
        rate_info = self.rates_dict.get((from_region, to_region))
        
        # Если нет прямой ставки, используем базовую модель
        if not rate_info:
            # Базовые параметры для расчета с корректировкой
            base_rate_per_ldm = 350 * self.correction_factors['base_rate_ldm_correction']  # Базовая ставка за 1 LDM в евро
            base_rate_per_km = 0.45 * self.correction_factors['base_rate_km_correction']  # Базовая ставка за 1 км за 1 LDM в евро
            
            # Коэффициенты для разных расстояний (с корректировкой)
            distance_factor = self.get_distance_correction_factor(distance_km)
            
            # Сезонные коэффициенты
            seasonal_factors = {
                "1": 0.9, "2": 0.9, "3": 0.95, "4": 1.0, "5": 1.0, "6": 1.05,
                "7": 0.9, "8": 0.85, "9": 1.1, "10": 1.15, "11": 1.1, "12": 1.0
            }
        else:
            # Используем данные из матрицы ставок с корректировкой
            base_rate_per_ldm = rate_info['base_rate_per_ldm'] * self.correction_factors['base_rate_ldm_correction']
            base_rate_per_km = rate_info['base_rate_per_km'] * self.correction_factors['base_rate_km_correction']
            
            # Корректируем коэффициент по расстоянию
            distance_factor = self.get_distance_correction_factor(distance_km)
            
            seasonal_factors = rate_info['seasonal_factors']
        
        # Корректировка по LDM
        ldm_correction = self.get_ldm_correction_factor(ldm)
        
        # Корректировка по весу
        weight_correction = self.get_weight_correction_factor(weight_kg)
        
        # Выбираем наиболее подходящую корректировку (по LDM или весу)
        volume_correction = min(ldm_correction, weight_correction)
        
        # Рассчитываем базовую стоимость с нелинейной формулой
        # Используем степенную функцию для учета эффекта масштаба
        ldm_power = 0.9  # Показатель степени для LDM (меньше 1 для эффекта масштаба)
        distance_power = 0.95  # Показатель степени для расстояния (меньше 1 для эффекта масштаба)
        
        # Нелинейная формула с эффектом масштаба
        base_cost = max(
            base_rate_per_ldm * (chargeable_ldm ** ldm_power),
            base_rate_per_km * (distance_km ** distance_power) * (chargeable_ldm ** ldm_power)
        ) * distance_factor * volume_correction
        
        # Применяем общий коэффициент корректировки
        base_cost *= self.correction_factors['general_correction']
        
        # Применяем сезонный коэффициент, если указан месяц
        if month and str(month) in seasonal_factors:
            base_cost *= seasonal_factors[str(month)]
        
        # Добавляем страховку (3.5%)
        insurance = base_cost * 0.035
        
        # Добавляем CO2 сбор
        co2_surcharge = weight_kg * 0.02 / 1000  # 0.02 евро за тонну
        
        final_cost = base_cost + insurance + co2_surcharge
        
        return round(final_cost, 2)
    
    def get_rate_of_transportation(self, from_country_code, from_postal_code, to_country_code, to_postal_code, ldm, weight):
        """Запуск калькулятора"""
        try:
            current_month = datetime.datetime.now().month
            
            from_region, from_place = self.get_region_by_postal(from_postal_code, from_country_code)

            if from_country_code == to_country_code and from_postal_code == to_postal_code:
                return {'error': 'Origin and destination cannot be the same.'}
            
            if not from_region:
                return {'error': 'Country code or postal code not found: {from_country_code}, {from_postal_code}'}
            
            to_region, to_place = self.get_region_by_postal(to_postal_code, to_country_code)
            
            if not to_region:
                return {'error': 'Country code or postal code not found: {from_country_code}, {from_postal_code}'}
            
            from_address = f"{from_postal_code}, {from_place}, {from_country_code}"
            to_address = f"{to_postal_code}, {to_place}, {to_country_code}"
            
            from_coords = self.get_coordinates(from_address)
            to_coords = self.get_coordinates(to_address)
            
            if not from_coords or None in from_coords or not to_coords or None in to_coords:
                distance = self.get_distance_from_matrix(from_region, to_region)
            else:
                distance = self.get_road_distance(from_coords, to_coords)
                
                if not distance:
                    distance = self.get_distance_from_matrix(from_region, to_region)
            
            # Расчёт
            rate = self.calculate_rate(distance, ldm, weight, from_region, to_region, current_month)
            
            # Расчет тарифицируемого объема
            chargeable_ldm = max(ldm, weight / DENSITY_FACTOR)

            return {
                'distance': round(distance, 2),
                'ldm': ldm,
                'weight': weight,
                'chargeable_ldm': round(chargeable_ldm, 2),
                'month': current_month,
                'rate': rate
            }
        
        except Exception as e:
            return {'error': 'Something went wrong, please try again later.'}

if __name__ == "__main__":
    calculator = FreightCalculator()
    for i in range(5):
        print(calculator.get_rate_of_transportation('DE', '10115', 'FR', '75001', 5, 1000))
