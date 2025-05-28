from flask import Flask, render_template
import json
import os
import csv

from api import api_bp

app = Flask(__name__)
app.register_blueprint(api_bp, url_prefix='/api')

def load_countries(filename):
    filepath = os.path.join(app.root_path, 'data', filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_expanded_ports_csv(filename):
    filepath = os.path.join(app.root_path, 'data', filename)
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)
    
def load_asian_cities(filename):
    filepath = os.path.join(app.root_path, 'data', filename)
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ru')
def index_ru():
    return render_template('index_ru.html')


@app.route('/et')
def index_et():
    return render_template('index_et.html')

@app.route('/multimodal_calculator')
def multimodal_calculator():
    container_types = [
        ('20dv', '20\' Dry Van (20DV)'),
        ('40dv', '40\' Dry Van (40DV)'),
        ('40hc', '40\' High Cube (40HC)')
    ]
    expanded_ports = load_expanded_ports_csv('ports.csv')

    return render_template('multimodal_calculator.html',
                         title="Multimodal Transportation",
                         description="Calculate multimodal shipping costs",
                         expanded_ports=expanded_ports,
                         container_types=container_types)

@app.route('/europe_calculator')
def europe_calculator():
    european_countries = load_countries('european_countries.json')
    return render_template('europe_calculator.html',
                         title="European Transportation",
                         description="Calculate shipping costs within Europe",
                         countries=european_countries)

@app.route('/asia_calculator')
def asia_calculator():
    european_countries = load_countries('european_countries.json')
    asian_countries = load_countries('asian_countries.json')
    asian_cities = load_asian_cities('central_asia_cities.csv')

    return render_template('asia_calculator.html',
                         title="Europe to Asia Transportation",
                         description="Calculate shipping costs from Europe to Central Asia",
                         asian_cities=asian_cities,
                         origin_countries=european_countries,
                         destination_countries=asian_countries)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5568)