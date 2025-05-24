#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Консольный калькулятор ставок фрахта с нелинейной моделью расчета
и использованием индексов из CSV-файла с весами, зависящими от маршрута
"""

import os
import csv
import sys
import math
import random
import argparse
from datetime import datetime

# Константы
DATA_DIR = '.\\data'
DEFAULT_CONTAINER_TYPE = '40hc'
DEFAULT_WEIGHT = 20000
VOLATILITY_ALPHA = 1.2  # Коэффициент волатильности для нелинейной формулы

class MultimodalFreightCalculator:
    """Калькулятор ставок фрахта с нелинейной моделью расчета"""
    
    def __init__(self, data_dir=DATA_DIR):
        """
        Инициализация калькулятора
        
        Args:
            data_dir (str): Путь к директории с CSV-файлами
        """
        self.data_dir = data_dir
        self.ports = {}
        self.basic_rates = {}
        self.fuel_surcharges = {}
        self.ecological_charges = {}
        self.seasonal_factors = {}
        self.port_congestion = {}
        self.crisis_coefficients = {}
        self.freight_indices = {}
        self.route_index_weights = {}
        
        # Загрузка данных из CSV-файлов
        self.load_ports()
        self.load_basic_rates()
        self.load_fuel_surcharges()
        self.load_ecological_charges()
        self.load_seasonal_factors()
        self.load_port_congestion()
        self.load_crisis_coefficients()
        self.load_freight_indices()
        self.load_route_index_weights()
    
    def load_ports(self):
        """Загрузка данных о портах из CSV"""
        try:
            ports_file = os.path.join(self.data_dir, 'ports.csv')
            with open(ports_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    port_id = row['id']
                    self.ports[port_id] = {
                        'name': row['name'],
                        'country': row['country'],
                        'region': row['region'],
                        'latitude': float(row['latitude']),
                        'longitude': float(row['longitude'])
                    }
            print(f"Загружено {len(self.ports)} портов")
        except Exception as e:
            print(f"Ошибка при загрузке портов: {e}")
            sys.exit(1)
    
    def load_basic_rates(self):
        """Загрузка базовых ставок между регионами из CSV"""
        try:
            rates_file = os.path.join(self.data_dir, 'basic_rates.csv')
            with open(rates_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    origin_region = row['origin_region']
                    destination_region = row['destination_region']
                    container_type = row['container_type']
                    avg_rate = float(row['avg_rate'])
                    carriers = row['carriers']
                    notes = row['notes']
                    
                    # Создаем структуру для хранения ставок
                    if origin_region not in self.basic_rates:
                        self.basic_rates[origin_region] = {}
                    if destination_region not in self.basic_rates[origin_region]:
                        self.basic_rates[origin_region][destination_region] = {}
                    
                    self.basic_rates[origin_region][destination_region][container_type] = {
                        'avg_rate': avg_rate,
                        'carriers': carriers,
                        'notes': notes
                    }
            
            # Подсчитываем количество загруженных ставок
            rate_count = sum(
                len(dest_rates) 
                for origin_rates in self.basic_rates.values() 
                for dest_rates in origin_rates.values()
            )
            print(f"Загружено {rate_count} базовых ставок")
        except Exception as e:
            print(f"Ошибка при загрузке базовых ставок: {e}")
            sys.exit(1)
    
    def load_fuel_surcharges(self):
        """Загрузка топливных надбавок из CSV"""
        try:
            surcharges_file = os.path.join(self.data_dir, 'fuel_surcharges.csv')
            with open(surcharges_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    origin_region = row['origin_region']
                    destination_region = row['destination_region']
                    min_percent = float(row['min_percent'])
                    max_percent = float(row['max_percent'])
                    date_updated = row['date_updated']
                    
                    # Создаем структуру для хранения топливных надбавок
                    if origin_region not in self.fuel_surcharges:
                        self.fuel_surcharges[origin_region] = {}
                    
                    self.fuel_surcharges[origin_region][destination_region] = {
                        'min_percent': min_percent,
                        'max_percent': max_percent,
                        'date_updated': date_updated
                    }
            
            # Подсчитываем количество загруженных топливных надбавок
            surcharge_count = sum(len(dest_surcharges) for dest_surcharges in self.fuel_surcharges.values())
            print(f"Загружено {surcharge_count} топливных надбавок")
        except Exception as e:
            print(f"Ошибка при загрузке топливных надбавок: {e}")
            sys.exit(1)
    
    def load_ecological_charges(self):
        """Загрузка экологических сборов из CSV"""
        try:
            charges_file = os.path.join(self.data_dir, 'ecological_charges.csv')
            with open(charges_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    region = row['region']
                    charge_type = row['charge_type']
                    container_type = row['container_type']
                    amount = float(row['amount'])
                    currency = row['currency']
                    date_updated = row['date_updated']
                    
                    # Создаем структуру для хранения экологических сборов
                    if region not in self.ecological_charges:
                        self.ecological_charges[region] = {}
                    if charge_type not in self.ecological_charges[region]:
                        self.ecological_charges[region][charge_type] = {}
                    
                    self.ecological_charges[region][charge_type][container_type] = {
                        'amount': amount,
                        'currency': currency,
                        'date_updated': date_updated
                    }
            
            # Подсчитываем количество загруженных экологических сборов
            charge_count = sum(
                len(charge_types) 
                for region_charges in self.ecological_charges.values() 
                for charge_types in region_charges.values()
            )
            print(f"Загружено {charge_count} экологических сборов")
        except Exception as e:
            print(f"Ошибка при загрузке экологических сборов: {e}")
            sys.exit(1)
    
    def load_seasonal_factors(self):
        """Загрузка сезонных коэффициентов из CSV"""
        try:
            factors_file = os.path.join(self.data_dir, 'seasonal_factors.csv')
            with open(factors_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    origin_region = row['origin_region']
                    destination_region = row['destination_region']
                    quarter = row['quarter']
                    factor = float(row['factor'])
                    date_updated = row['date_updated']
                    
                    # Создаем структуру для хранения сезонных коэффициентов
                    if origin_region not in self.seasonal_factors:
                        self.seasonal_factors[origin_region] = {}
                    if destination_region not in self.seasonal_factors[origin_region]:
                        self.seasonal_factors[origin_region][destination_region] = {}
                    
                    self.seasonal_factors[origin_region][destination_region][quarter] = {
                        'factor': factor,
                        'date_updated': date_updated
                    }
            
            # Подсчитываем количество загруженных сезонных коэффициентов
            factor_count = sum(
                len(dest_factors) 
                for origin_factors in self.seasonal_factors.values() 
                for dest_factors in origin_factors.values()
            )
            print(f"Загружено {factor_count} сезонных коэффициентов")
        except Exception as e:
            print(f"Ошибка при загрузке сезонных коэффициентов: {e}")
            sys.exit(1)
    
    def load_port_congestion(self):
        """Загрузка надбавок за перегрузку портов из CSV"""
        try:
            congestion_file = os.path.join(self.data_dir, 'port_congestion.csv')
            with open(congestion_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    port_id = row['port_id']
                    congestion_level = row['congestion_level']
                    container_type = row['container_type']
                    amount = float(row['amount'])
                    currency = row['currency']
                    date_updated = row['date_updated']
                    
                    # Создаем структуру для хранения надбавок за перегрузку
                    if port_id not in self.port_congestion:
                        self.port_congestion[port_id] = {}
                    if congestion_level not in self.port_congestion[port_id]:
                        self.port_congestion[port_id][congestion_level] = {}
                    
                    self.port_congestion[port_id][congestion_level][container_type] = {
                        'amount': amount,
                        'currency': currency,
                        'date_updated': date_updated
                    }
            
            # Подсчитываем количество загруженных надбавок за перегрузку
            congestion_count = sum(
                len(level_charges) 
                for port_charges in self.port_congestion.values() 
                for level_charges in port_charges.values()
            )
            print(f"Загружено {congestion_count} надбавок за перегрузку портов")
        except Exception as e:
            print(f"Ошибка при загрузке надбавок за перегрузку портов: {e}")
            sys.exit(1)
    
    def load_crisis_coefficients(self):
        """Загрузка кризисных коэффициентов из CSV"""
        try:
            crisis_file = os.path.join(self.data_dir, 'crisis_coefficients.csv')
            with open(crisis_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    region_pair = row['region_pair']
                    start_date = datetime.strptime(row['start_date'], '%Y-%m-%d')
                    end_date = datetime.strptime(row['end_date'], '%Y-%m-%d')
                    multiplier = float(row['multiplier'])
                    description = row['description']
                    
                    # Разбиваем пару регионов
                    regions = region_pair.split('-')
                    if len(regions) != 2:
                        continue
                    
                    origin_region = regions[0]
                    destination_region = regions[1]
                    
                    # Создаем структуру для хранения кризисных коэффициентов
                    if origin_region not in self.crisis_coefficients:
                        self.crisis_coefficients[origin_region] = {}
                    if destination_region not in self.crisis_coefficients[origin_region]:
                        self.crisis_coefficients[origin_region][destination_region] = []
                    
                    self.crisis_coefficients[origin_region][destination_region].append({
                        'start_date': start_date,
                        'end_date': end_date,
                        'multiplier': multiplier,
                        'description': description
                    })
            
            # Подсчитываем количество загруженных кризисных коэффициентов
            crisis_count = sum(
                len(dest_crisis) 
                for origin_crisis in self.crisis_coefficients.values() 
                for dest_crisis in origin_crisis.values()
            )
            print(f"Загружено {crisis_count} кризисных коэффициентов")
        except Exception as e:
            print(f"Ошибка при загрузке кризисных коэффициентов: {e}")
            sys.exit(1)
    
    def load_freight_indices(self):
        """Загрузка индексов фрахта из CSV"""
        try:
            indices_file = os.path.join(self.data_dir, 'freight_indices.csv')
            with open(indices_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    index_name = row['index_name']
                    current_value = float(row['current_value'])
                    base_value = float(row['base_value'])
                    weight = float(row['weight'])
                    description = row['description']
                    date_updated = row['date_updated']
                    
                    self.freight_indices[index_name] = {
                        'current_value': current_value,
                        'base_value': base_value,
                        'weight': weight,  # Этот вес будет использоваться только если нет маршрутно-зависимых весов
                        'description': description,
                        'date_updated': date_updated
                    }
            
            print(f"Загружено {len(self.freight_indices)} индексов фрахта")
        except Exception as e:
            print(f"Ошибка при загрузке индексов фрахта: {e}")
            sys.exit(1)
    
    def load_route_index_weights(self):
        """Загрузка весов индексов по маршрутам из CSV"""
        try:
            weights_file = os.path.join(self.data_dir, 'route_index_weights.csv')
            with open(weights_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    route = row['route']
                    index_name = row['index_name']
                    weight = float(row['weight'])
                    date_updated = row['date_updated']
                    
                    # Создаем структуру для хранения весов индексов по маршрутам
                    if route not in self.route_index_weights:
                        self.route_index_weights[route] = {}
                    
                    self.route_index_weights[route][index_name] = {
                        'weight': weight,
                        'date_updated': date_updated
                    }
            
            # Подсчитываем количество загруженных весов индексов по маршрутам
            weight_count = sum(len(index_weights) for index_weights in self.route_index_weights.values())
            print(f"Загружено {weight_count} весов индексов по маршрутам")
        except Exception as e:
            print(f"Ошибка при загрузке весов индексов по маршрутам: {e}")
            sys.exit(1)
    
    def get_port_region(self, port_id):
        """
        Получение региона порта
        
        Args:
            port_id (str): ID порта
            
        Returns:
            str: Регион порта или None, если порт не найден
        """
        if port_id in self.ports:
            return self.ports[port_id]['region']
        return None
    
    def get_basic_rate(self, origin_region, destination_region, container_type):
        """
        Получение базовой ставки между регионами
        
        Args:
            origin_region (str): Регион отправления
            destination_region (str): Регион назначения
            container_type (str): Тип контейнера
            
        Returns:
            dict: Данные ставки или None, если ставка не найдена
        """
        try:
            return self.basic_rates[origin_region][destination_region][container_type]
        except KeyError:
            return None
    
    def get_fuel_surcharge(self, origin_region, destination_region):
        """
        Получение топливной надбавки
        
        Args:
            origin_region (str): Регион отправления
            destination_region (str): Регион назначения
            
        Returns:
            dict: Данные топливной надбавки или None, если надбавка не найдена
        """
        try:
            return self.fuel_surcharges[origin_region][destination_region]
        except KeyError:
            return None
    
    def get_ecological_charge(self, region, charge_type, container_type):
        """
        Получение экологического сбора
        
        Args:
            region (str): Регион
            charge_type (str): Тип сбора
            container_type (str): Тип контейнера
            
        Returns:
            dict: Данные экологического сбора или None, если сбор не найден
        """
        try:
            return self.ecological_charges[region][charge_type][container_type]
        except KeyError:
            return None
    
    def get_seasonal_factor(self, origin_region, destination_region, quarter):
        """
        Получение сезонного коэффициента
        
        Args:
            origin_region (str): Регион отправления
            destination_region (str): Регион назначения
            quarter (str): Квартал (Q1, Q2, Q3, Q4)
            
        Returns:
            dict: Данные сезонного коэффициента или None, если коэффициент не найден
        """
        try:
            return self.seasonal_factors[origin_region][destination_region][quarter]
        except KeyError:
            return None
    
    def get_port_congestion_charge(self, port_id, congestion_level, container_type):
        """
        Получение надбавки за перегрузку порта
        
        Args:
            port_id (str): ID порта
            congestion_level (str): Уровень перегрузки
            container_type (str): Тип контейнера
            
        Returns:
            dict: Данные надбавки за перегрузку или None, если надбавка не найдена
        """
        try:
            return self.port_congestion[port_id][congestion_level][container_type]
        except KeyError:
            return None
    
    def get_crisis_multiplier(self, origin_region, destination_region):
        """
        Получение кризисного коэффициента для пары регионов
        
        Args:
            origin_region (str): Регион отправления
            destination_region (str): Регион назначения
            
        Returns:
            float: Кризисный коэффициент или 1.0, если коэффициент не найден
        """
        try:
            # Получаем список кризисных коэффициентов для пары регионов
            crisis_list = self.crisis_coefficients[origin_region][destination_region]
            
            # Текущая дата
            today = datetime.now()
            
            # Проверяем, есть ли активные кризисные ситуации
            active_crisis = [
                crisis for crisis in crisis_list
                if crisis['start_date'] <= today <= crisis['end_date']
            ]
            
            if active_crisis:
                # Если есть несколько активных кризисов, берем максимальный коэффициент
                return max(crisis['multiplier'] for crisis in active_crisis)
            
            return 1.0
        except KeyError:
            return 1.0
    
    def get_route_key(self, origin_region, destination_region):
        """
        Получение ключа маршрута для поиска весов индексов
        
        Args:
            origin_region (str): Регион отправления
            destination_region (str): Регион назначения
            
        Returns:
            str: Ключ маршрута или None, если маршрут не найден
        """
        # Прямой маршрут
        direct_route = f"{origin_region}-{destination_region}"
        if direct_route in self.route_index_weights:
            return direct_route
        
        # Проверяем обобщенные маршруты
        # Например, если нет точного "Asia-North America East", проверяем "Asia-North America"
        if origin_region == "North America East" or origin_region == "North America West":
            generalized_origin = "North America"
            generalized_route = f"{generalized_origin}-{destination_region}"
            if generalized_route in self.route_index_weights:
                return generalized_route
        
        if destination_region == "North America East" or destination_region == "North America West":
            generalized_destination = "North America"
            generalized_route = f"{origin_region}-{generalized_destination}"
            if generalized_route in self.route_index_weights:
                return generalized_route
        
        # Проверяем внутрирегиональные маршруты
        if origin_region == destination_region:
            intra_route = f"Intra-{origin_region}"
            if intra_route in self.route_index_weights:
                return intra_route
        
        # Если регион содержит пробел, пробуем без пробела
        if " " in origin_region:
            no_space_origin = origin_region.replace(" ", "")
            no_space_route = f"{no_space_origin}-{destination_region}"
            if no_space_route in self.route_index_weights:
                return no_space_route
        
        if " " in destination_region:
            no_space_destination = destination_region.replace(" ", "")
            no_space_route = f"{origin_region}-{no_space_destination}"
            if no_space_route in self.route_index_weights:
                return no_space_route
        
        # Если ничего не найдено, возвращаем None
        return None
    
    def get_index_weights_for_route(self, origin_region, destination_region):
        """
        Получение весов индексов для конкретного маршрута
        
        Args:
            origin_region (str): Регион отправления
            destination_region (str): Регион назначения
            
        Returns:
            dict: Словарь с весами индексов для маршрута или None, если маршрут не найден
        """
        route_key = self.get_route_key(origin_region, destination_region)
        
        if route_key and route_key in self.route_index_weights:
            return self.route_index_weights[route_key]
        
        # Если не нашли веса для маршрута, используем обратный маршрут
        reverse_route_key = self.get_route_key(destination_region, origin_region)
        if reverse_route_key and reverse_route_key in self.route_index_weights:
            return self.route_index_weights[reverse_route_key]
        
        # Если не нашли веса для маршрута, возвращаем None
        return None
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Расчет расстояния между двумя точками на сфере (формула гаверсинуса)
        
        Args:
            lat1 (float): Широта первой точки
            lon1 (float): Долгота первой точки
            lat2 (float): Широта второй точки
            lon2 (float): Долгота второй точки
            
        Returns:
            float: Расстояние в морских милях
        """
        # Радиус Земли в морских милях
        R = 3440.07
        
        # Перевод в радианы
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Разница координат
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        
        # Формула гаверсинуса
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def get_current_quarter(self):
        """
        Получение текущего квартала
        
        Returns:
            str: Текущий квартал в формате Q1, Q2, Q3, Q4
        """
        month = datetime.now().month
        quarter = (month - 1) // 3 + 1
        return f"Q{quarter}"
    
    def calculate_weighted_index_change(self, origin_region, destination_region):
        """
        Расчет взвешенного изменения индексов с учетом маршрута
        
        Args:
            origin_region (str): Регион отправления
            destination_region (str): Регион назначения
            
        Returns:
            float: Взвешенное изменение индексов в процентах
        """
        weighted_change = 0.0
        total_weight = 0.0
        
        # Получаем веса индексов для маршрута
        route_weights = self.get_index_weights_for_route(origin_region, destination_region)
        
        # Если нашли веса для маршрута, используем их
        if route_weights:
            for index_name, index_data in self.freight_indices.items():
                if index_name in route_weights:
                    current_value = index_data['current_value']
                    base_value = index_data['base_value']
                    weight = route_weights[index_name]['weight']
                    
                    # Расчет процентного изменения индекса
                    change_percent = ((current_value - base_value) / base_value) * 100
                    
                    # Добавление взвешенного изменения
                    weighted_change += change_percent * weight
                    total_weight += weight
        else:
            # Если не нашли веса для маршрута, используем общие веса из freight_indices
            for index_name, index_data in self.freight_indices.items():
                current_value = index_data['current_value']
                base_value = index_data['base_value']
                weight = index_data['weight']
                
                # Расчет процентного изменения индекса
                change_percent = ((current_value - base_value) / base_value) * 100
                
                # Добавление взвешенного изменения
                weighted_change += change_percent * weight
                total_weight += weight
        
        # Нормализация по сумме весов
        if total_weight > 0:
            weighted_change /= total_weight
        
        return weighted_change
    
    def calculate_fallback_rate(self, origin, destination, container_type):
        """
        Расчет ставки при отсутствии данных о регионах
        
        Args:
            origin (str): ID порта отправления
            destination (str): ID порта назначения
            container_type (str): Тип контейнера
            
        Returns:
            dict: Данные ставки
        """
        # Получаем координаты портов
        origin_lat = self.ports[origin]['latitude']
        origin_lon = self.ports[origin]['longitude']
        dest_lat = self.ports[destination]['latitude']
        dest_lon = self.ports[destination]['longitude']
        
        # Расчет расстояния между портами
        distance = self.calculate_distance(origin_lat, origin_lon, dest_lat, dest_lon)
        
        # Базовая ставка на основе расстояния и типа контейнера
        base_rate = distance * 0.5  # $0.5 за морскую милю
        
        # Корректировка для разных типов контейнеров
        if container_type == '20dv':
            base_rate *= 1.0
        elif container_type == '40dv':
            base_rate *= 1.4
        elif container_type == '40hc':
            base_rate *= 1.5
        
        # Минимальная ставка
        base_rate = max(base_rate, 1000)
        
        return {
            'avg_rate': base_rate,
            'carriers': 'Расчетная ставка',
            'notes': 'Рассчитано на основе расстояния'
        }
    
    def calculate_freight_rate(self, origin, destination, container_type, weight=DEFAULT_WEIGHT):
        """
        Расчет ставки фрахта с использованием нелинейной модели
        
        Args:
            origin (str): ID порта отправления
            destination (str): ID порта назначения
            container_type (str): Тип контейнера
            weight (float): Вес груза в кг
            
        Returns:
            dict: Результат расчета
        """
        # Проверяем наличие портов
        if origin not in self.ports:
            return {'error': f'Порт отправления {origin} не найден'}
        if destination not in self.ports:
            return {'error': f'Порт назначения {destination} не найден'}
        
        # Получаем регионы портов
        origin_region = self.get_port_region(origin)
        destination_region = self.get_port_region(destination)
        
        origin_lat = self.ports[origin]['latitude']
        origin_lon = self.ports[origin]['longitude']
        dest_lat = self.ports[destination]['latitude']
        dest_lon = self.ports[destination]['longitude']
        
        # Расчет расстояния между портами
        distance = self.calculate_distance(origin_lat, origin_lon, dest_lat, dest_lon)

        # 1. Получение базовой ставки между регионами
        basic_rate_data = self.get_basic_rate(origin_region, destination_region, container_type)
        
        # Если ставка не найдена, используем расчет на основе расстояния
        if basic_rate_data is None:
            basic_rate_data = self.calculate_fallback_rate(origin, destination, container_type)
        
        base_rate = basic_rate_data['avg_rate']
        carriers = basic_rate_data['carriers']
        notes = basic_rate_data['notes']
        
        # 2. Получение взвешенного изменения индексов с учетом маршрута
        weighted_index_change = self.calculate_weighted_index_change(origin_region, destination_region)
        
        # 3. Применение нелинейной формулы с учетом волатильности
        # Финальная ставка = B × (1 + ΔFBX/100)^α
        volatility_factor = (1 + weighted_index_change / 100) ** VOLATILITY_ALPHA
        adjusted_rate = base_rate * volatility_factor
        
        # 4. Применение кризисного коэффициента
        crisis_multiplier = self.get_crisis_multiplier(origin_region, destination_region)
        adjusted_rate *= crisis_multiplier
        
        # 5. Расчет топливной надбавки
        fuel_surcharge_data = self.get_fuel_surcharge(origin_region, destination_region)
        fuel_surcharge = 0
        fuel_surcharge_percent = 0
        
        if fuel_surcharge_data:
            # Используем среднее значение между min и max
            fuel_surcharge_percent = (fuel_surcharge_data['min_percent'] + fuel_surcharge_data['max_percent']) / 2 / 100
            fuel_surcharge = adjusted_rate * fuel_surcharge_percent
        
        # 6. Расчет экологических сборов
        eco_charge_origin = 0
        eco_charge_destination = 0
        
        # Экологические сборы в регионе отправления
        for charge_type in ['ECA', 'CLS']:
            eco_charge = self.get_ecological_charge(origin_region, charge_type, container_type)
            if eco_charge:
                eco_charge_origin += eco_charge['amount']
        
        # Экологические сборы в регионе назначения
        for charge_type in ['ECA', 'CLS']:
            eco_charge = self.get_ecological_charge(destination_region, charge_type, container_type)
            if eco_charge:
                eco_charge_destination += eco_charge['amount']
        
        # 7. Применение сезонного фактора
        current_quarter = self.get_current_quarter()
        seasonal_factor = 1.0
        
        seasonal_data = self.get_seasonal_factor(origin_region, destination_region, current_quarter)
        if seasonal_data:
            seasonal_factor = seasonal_data['factor']
        
        # Применяем сезонный фактор к ставке
        adjusted_rate *= seasonal_factor
        
        # 8. Учет перегрузки портов
        congestion_charge_origin = 0
        congestion_charge_destination = 0
        
        # Определяем уровень перегрузки (для примера используем фиксированные значения)
        origin_congestion_level = 'medium'
        destination_congestion_level = 'medium'
        
        # Проверяем наличие порта в списке перегруженных
        if origin in self.port_congestion:
            for level in self.port_congestion[origin]:
                if container_type in self.port_congestion[origin][level]:
                    origin_congestion_level = level
                    congestion_charge_origin = self.port_congestion[origin][level][container_type]['amount']
                    break
        
        if destination in self.port_congestion:
            for level in self.port_congestion[destination]:
                if container_type in self.port_congestion[destination][level]:
                    destination_congestion_level = level
                    congestion_charge_destination = self.port_congestion[destination][level][container_type]['amount']
                    break
        
        # 9. Расчет итоговой ставки
        total_rate = adjusted_rate + fuel_surcharge + eco_charge_origin + eco_charge_destination + congestion_charge_origin + congestion_charge_destination
        
        # Округляем ставки
        base_rate = round(base_rate)
        adjusted_rate = round(adjusted_rate)
        total_rate = round(total_rate)
        
        # 10. Формирование результата
        result = {
            'origin': origin,
            'origin_name': self.ports[origin]['name'],
            'origin_country': self.ports[origin]['country'],
            'origin_region': origin_region,
            'destination': destination,
            'destination_name': self.ports[destination]['name'],
            'destination_country': self.ports[destination]['country'],
            'destination_region': destination_region,
            'container_type': container_type,
            'weight': weight,
            'base_rate': base_rate,
            'carriers': carriers,
            'notes': notes,
            'weighted_index_change': round(weighted_index_change, 2),
            'volatility_factor': round(volatility_factor, 4),
            'crisis_multiplier': crisis_multiplier,
            'adjusted_rate': adjusted_rate,
            'fuel_surcharge': round(fuel_surcharge),
            'fuel_surcharge_percent': round(fuel_surcharge_percent * 100, 1),
            'eco_charge_origin': round(eco_charge_origin),
            'eco_charge_destination': round(eco_charge_destination),
            'seasonal_factor': seasonal_factor,
            'current_quarter': current_quarter,
            'origin_congestion_level': origin_congestion_level,
            'congestion_charge_origin': round(congestion_charge_origin),
            'destination_congestion_level': destination_congestion_level,
            'congestion_charge_destination': round(congestion_charge_destination),
            'total_rate': total_rate,
            'calculation_date': datetime.now().strftime('%Y-%m-%d'),
            'distance': round(distance, 2),
        }
        
        # Добавляем информацию о маршрутно-зависимых весах индексов
        route_key = self.get_route_key(origin_region, destination_region)
        if route_key:
            result['route_key'] = route_key
            
            # Добавляем веса индексов для маршрута
            route_weights = self.route_index_weights[route_key]
            index_weights = {}
            for index_name, index_data in route_weights.items():
                index_weights[index_name] = index_data['weight']
            
            result['index_weights'] = index_weights
        
        return result
    
    def list_ports(self):
        """
        Вывод списка доступных портов
        
        Returns:
            list: Список портов
        """
        port_list = []
        for port_id, port_data in self.ports.items():
            port_list.append({
                'id': port_id,
                'name': port_data['name'],
                'country': port_data['country'],
                'region': port_data['region']
            })
        
        # Сортировка по региону и названию
        port_list.sort(key=lambda x: (x['region'], x['name']))
        return port_list
    
    def list_container_types(self):
        """
        Вывод списка доступных типов контейнеров
        
        Returns:
            list: Список типов контейнеров
        """
        # Поддерживаемые типы контейнеров
        return ['20dv', '40dv', '40hc']
    
    def list_indices(self):
        """
        Вывод списка индексов фрахта
        
        Returns:
            list: Список индексов
        """
        index_list = []
        for index_name, index_data in self.freight_indices.items():
            index_list.append({
                'name': index_name,
                'current_value': index_data['current_value'],
                'base_value': index_data['base_value'],
                'weight': index_data['weight'],
                'description': index_data['description'],
                'date_updated': index_data['date_updated']
            })
        
        # Сортировка по весу (от большего к меньшему)
        index_list.sort(key=lambda x: x['weight'], reverse=True)
        return index_list
    
    def list_route_index_weights(self):
        """
        Вывод списка весов индексов по маршрутам
        
        Returns:
            dict: Словарь с весами индексов по маршрутам
        """
        route_weights = {}
        for route, index_weights in self.route_index_weights.items():
            route_weights[route] = {}
            for index_name, weight_data in index_weights.items():
                route_weights[route][index_name] = weight_data['weight']
        
        return route_weights

def print_port_list(ports):
    """
    Вывод списка портов в консоль
    
    Args:
        ports (list): Список портов
    """
    print("\nДоступные порты:")
    print("-" * 80)
    print(f"{'ID':<8} {'Название':<25} {'Страна':<20} {'Регион':<15}")
    print("-" * 80)
    
    current_region = None
    for port in ports:
        if current_region != port['region']:
            current_region = port['region']
            print(f"\n{current_region}:")
        
        print(f"{port['id']:<8} {port['name']:<25} {port['country']:<20} {port['region']:<15}")

def print_container_types(container_types):
    """
    Вывод списка типов контейнеров в консоль
    
    Args:
        container_types (list): Список типов контейнеров
    """
    print("\nДоступные типы контейнеров:")
    print("-" * 50)
    
    container_names = {
        '20dv': '20\' Dry Van (стандартный)',
        '40dv': '40\' Dry Van (стандартный)',
        '40hc': '40\' High Cube (увеличенной высоты)'
    }
    
    for container_type in container_types:
        name = container_names.get(container_type, container_type)
        print(f"{container_type:<8} - {name}")

def print_indices(indices):
    """
    Вывод списка индексов фрахта в консоль
    
    Args:
        indices (list): Список индексов
    """
    print("\nИндексы фрахта:")
    print("-" * 100)
    print(f"{'Индекс':<8} {'Текущее значение':<18} {'Базовое значение':<18} {'Вес':<8} {'Описание':<30} {'Обновлено':<12}")
    print("-" * 100)
    
    for index in indices:
        print(f"{index['name']:<8} {index['current_value']:<18.2f} {index['base_value']:<18.2f} {index['weight']:<8.2f} {index['description']:<30} {index['date_updated']:<12}")

def print_route_index_weights(route_weights):
    """
    Вывод весов индексов по маршрутам в консоль
    
    Args:
        route_weights (dict): Словарь с весами индексов по маршрутам
    """
    print("\nВеса индексов по маршрутам:")
    print("-" * 100)
    
    for route, index_weights in route_weights.items():
        print(f"\nМаршрут: {route}")
        print("-" * 50)
        print(f"{'Индекс':<8} {'Вес':<8}")
        print("-" * 50)
        
        for index_name, weight in index_weights.items():
            print(f"{index_name:<8} {weight:<8.2f}")

def print_calculation_result(result):
    """
    Вывод результата расчета в консоль
    
    Args:
        result (dict): Результат расчета
    """
    if 'error' in result:
        print(f"\nОшибка: {result['error']}")
        return
    
    print("\n" + "=" * 80)
    print(f"РАСЧЕТ СТАВКИ ФРАХТА (НЕЛИНЕЙНАЯ МОДЕЛЬ С МАРШРУТНО-ЗАВИСИМЫМИ ВЕСАМИ ИНДЕКСОВ)")
    print("=" * 80)
    
    print(f"\nМаршрут: {result['origin']} {result['origin_name']} ({result['origin_country']}, {result['origin_region']}) → "
          f"{result['destination']} {result['destination_name']} ({result['destination_country']}, {result['destination_region']})")
    print(f"Тип контейнера: {result['container_type']}")
    print(f"Вес груза: {result['weight']} кг")
    print(f"Дата расчета: {result['calculation_date']}")
    print(f"Перевозчики: {result['carriers']}")
    
    print("\n" + "-" * 80)
    print("ИНДЕКСЫ И МОДИФИКАТОРЫ")
    print("-" * 80)
    
    if 'route_key' in result:
        print(f"Ключ маршрута для весов индексов:      {result['route_key']}")
        print("Веса индексов для маршрута:")
        for index_name, weight in result['index_weights'].items():
            print(f"  - {index_name}: {weight:.2f}")
    
    print(f"Взвешенное изменение индексов:         {result['weighted_index_change']}%")
    print(f"Коэффициент волатильности (α):         {VOLATILITY_ALPHA}")
    print(f"Фактор волатильности:                  {result['volatility_factor']}")
    print(f"Кризисный коэффициент:                 {result['crisis_multiplier']}")
    print(f"Сезонный фактор ({result['current_quarter']}):               {result['seasonal_factor']}")
    
    print("\n" + "-" * 80)
    print("СТРУКТУРА СТАВКИ")
    print("-" * 80)
    
    print(f"Базовая ставка:                        ${result['base_rate']}")
    print(f"Ставка с учетом индексов и факторов:   ${result['adjusted_rate']}")
    print(f"Топливная надбавка ({result['fuel_surcharge_percent']}%):          ${result['fuel_surcharge']}")
    print(f"Экологические сборы (регион отправления): ${result['eco_charge_origin']}")
    print(f"Экологические сборы (регион назначения):  ${result['eco_charge_destination']}")
    print(f"Перегрузка порта отправления ({result['origin_congestion_level']}):    ${result['congestion_charge_origin']}")
    print(f"Перегрузка порта назначения ({result['destination_congestion_level']}):   ${result['congestion_charge_destination']}")
    
    print("\n" + "-" * 80)
    print("ИТОГОВАЯ СТАВКА")
    print("-" * 80)
    
    print(f"Итоговая ставка:                       ${result['total_rate']}")
    
    print("\n" + "-" * 80)
    print("ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ")
    print("-" * 80)
    
    print(f"Примечания: {result['notes']}")
    print(f"Формула расчета: B × (1 + ΔIndex/100)^α × crisis_multiplier × seasonal_factor + сборы")
    print(f"где B = ${result['base_rate']}, ΔIndex = {result['weighted_index_change']}%, α = {VOLATILITY_ALPHA}")

def select_from_list(items, prompt, display_func=None, id_key='id'):
    """
    Выбор элемента из списка с помощью интерактивного меню
    
    Args:
        items (list): Список элементов для выбора
        prompt (str): Приглашение к выбору
        display_func (function, optional): Функция для отображения списка
        id_key (str, optional): Ключ для получения ID элемента
        
    Returns:
        str: ID выбранного элемента
    """
    if display_func:
        display_func(items)
    
    # Создаем нумерованный список для выбора
    print("\n" + prompt)
    for i, item in enumerate(items, 1):
        if isinstance(item, dict):
            if 'name' in item and 'country' in item and 'region' in item:
                print(f"{i}. {item['id']} - {item['name']}, {item['country']} ({item['region']})")
            elif 'name' in item and 'country' in item:
                print(f"{i}. {item['id']} - {item['name']}, {item['country']}")
            elif 'name' in item:
                print(f"{i}. {item['id']} - {item['name']}")
            else:
                print(f"{i}. {item[id_key]}")
        else:
            print(f"{i}. {item}")
    
    # Получаем выбор пользователя
    while True:
        try:
            choice = input("\nВведите номер (1-" + str(len(items)) + "): ")
            index = int(choice) - 1
            if 0 <= index < len(items):
                selected = items[index]
                if isinstance(selected, dict):
                    return selected[id_key]
                return selected
            print(f"Пожалуйста, введите число от 1 до {len(items)}.")
        except ValueError:
            print("Пожалуйста, введите корректное число.")

def interactive_mode_with_selection():
    """Запуск калькулятора в интерактивном режиме с выбором из списка"""
    print("\n" + "=" * 80)
    print("КОНСОЛЬНЫЙ КАЛЬКУЛЯТОР СТАВОК ФРАХТА (НЕЛИНЕЙНАЯ МОДЕЛЬ С МАРШРУТНО-ЗАВИСИМЫМИ ВЕСАМИ ИНДЕКСОВ)")
    print("=" * 80)
    
    # Инициализация калькулятора
    calculator = MultimodalFreightCalculator()
    
    # Получение списка портов и типов контейнеров
    ports = calculator.list_ports()
    container_types = calculator.list_container_types()
    
    # Выбор порта отправления
    origin = select_from_list(
        ports, 
        "Выберите порт отправления:", 
        display_func=None  # Не выводим полный список, только нумерованный
    )
    
    # Выбор порта назначения
    while True:
        destination = select_from_list(
            ports, 
            "Выберите порт назначения:", 
            display_func=None  # Не выводим полный список, только нумерованный
        )
        if destination != origin:
            break
        print("Порт назначения не может совпадать с портом отправления.")
    
    # Выбор типа контейнера
    container_type = select_from_list(
        container_types, 
        "Выберите тип контейнера:", 
        display_func=print_container_types
    )
    
    # Ввод веса груза
    while True:
        weight_input = input(f"Вес груза в кг (по умолчанию {DEFAULT_WEIGHT}): ").strip()
        if not weight_input:
            weight = DEFAULT_WEIGHT
            break
        try:
            weight = float(weight_input)
            if weight > 0:
                break
            print("Вес должен быть положительным числом.")
        except ValueError:
            print("Пожалуйста, введите корректное числовое значение.")
    
    # Расчет ставки
    result = calculator.calculate_freight_rate(origin, destination, container_type, weight)
    
    # Вывод результата
    print_calculation_result(result)

def main():
    multimodal_freight_calculator = MultimodalFreightCalculator()
    origin = input("Введите ID порта отправления: ")
    destination = input("Введите ID порта назначения: ")
    container_type = input("Введите тип контейнера (20dv, 40dv, 40hc): ")

    result = multimodal_freight_calculator.calculate_freight_rate(origin, destination, container_type)

    print(result)

if __name__ == '__main__':
    main()
