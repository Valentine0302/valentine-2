from flask import Blueprint, jsonify, request
from calculators.europe_calculator import FreightCalculator
from calculators.multimodal_calculator import MultimodalFreightCalculator
from calculators.asian_calculator import AsianFreightCalculator

from email.message import EmailMessage
import base64
import os
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from disposable_email_domains import blocklist
from core.email_verifiers import verify_email, is_disposable, validate_email

api_bp = Blueprint('api', __name__)

europe_freight_calculator = FreightCalculator()
asian_freight_calculator = AsianFreightCalculator()
multimodal_freight_calculator = MultimodalFreightCalculator()

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_PATH = 'data/token.json'
CREDENTIALS_PATH = 'data/credentials.json'
DEFAULT_SENDER = 'onekaden17231@gmail.com'

def validate_postal_code(code: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9\- ]{3,10}", code))

@api_bp.route('/validate_email', methods=['POST'])
def validate_email_route():
    data = request.get_json()
    email = data.get('email', '').strip()

    if not verify_email(email):
        return jsonify({'error': 'Invalid email address'}), 400

    if is_disposable(email):
        return jsonify({'error': 'Disposable email addresses are not allowed.'}), 400

    return jsonify({'message': 'Valid email'}), 200

@api_bp.route('/calculate_rate_asia', methods=['POST'])
def calculate_rate_asia():
    data = request.get_json()
    required_fields = ['fromCountry', 'fromZip', 'ldm', 'weight', 'asiaCity', 'asiaCountry', 'email']

    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        result = asian_freight_calculator.calculate(
            eu_postal=data['fromZip'].strip(),
            eu_country=data['fromCountry'].strip().upper(),
            asia_country=data['asiaCountry'].strip().upper(),
            asia_city=data['asiaCity'].strip(),
            ldm=float(data['ldm']),
            weight=float(data['weight'])
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@api_bp.route('/calculate_rate_europe', methods=['POST'])
def calculate_rate_europe():
    data = request.get_json()
    required_fields = ['fromCountry', 'toCountry', 'fromZip', 'toZip', 'ldm', 'weight']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    if not validate_postal_code(data['fromZip']) or not validate_postal_code(data['toZip']):
        return jsonify({'error': 'Invalid postal code format'}), 400

    try:
        calculated_data = europe_freight_calculator.get_rate_of_transportation(
            from_country_code=data['fromCountry'],
            to_country_code=data['toCountry'],
            from_postal_code=data['fromZip'],
            to_postal_code=data['toZip'],
            ldm=float(data['ldm']),
            weight=float(data['weight']),
        )
        return jsonify(calculated_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return calculate_rate_europe()

@api_bp.route('/calculate_rate_multimodal', methods=['POST'])
def calculate_rate_multimodal():
    data = request.get_json()
    required_fields = ['originPort', 'destinationPort', 'containerType']

    if data['originPort'] == data['destinationPort']:
        return jsonify({'error': 'Origin and destination ports cannot be the same'}), 400

    try:
        calculated_data = multimodal_freight_calculator.calculate_freight_rate(origin=data['originPort'], destination=data['destinationPort'], container_type=data['containerType'])
        return jsonify(calculated_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_gmail_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

@api_bp.route('/send_email', methods=['POST'])
def send_email():
    data = request.get_json()
    to = data.get('to')
    subject = data.get('subject')
    rate = data.get('rate')
    distance = data.get('distance')
    chargeable_ldm = data.get('chargeable_ldm')

    html_body = f"""
        <h3>Calculation Result</h3>
        <p><strong>Distance:</strong> {distance} km</p>
        <p><strong>Chargeable Volume:</strong> {chargeable_ldm} LDM</p>
        <p><strong>Total Freight Cost:</strong> <span style=\"color:green; font-weight:bold;\">€{rate}</span></p>
    """

    message = EmailMessage()
    message.set_content("Your freight calculation result is ready.", subtype='plain')
    message.add_alternative(html_body, subtype='html')
    message['To'] = to
    message['From'] = DEFAULT_SENDER
    message['Subject'] = subject

    try:
        service = get_gmail_service()
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        result = service.users().messages().send(userId="me", body=create_message).execute()
        return jsonify({'message': 'Email sent successfully', 'id': result['id']})
    except Exception as e:
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500

@api_bp.route('/send_contact_form', methods=['POST'])
def send_contact_form():
    data = request.get_json()

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    company = data.get('company', '').strip()
    message_text = data.get('message', '').strip()

    # Простая валидация обязательных полей
    if not name or not email or not message_text:
        return jsonify({'error': 'Name, email, and message are required.'}), 400

    if not verify_email(email):
        return jsonify({'error': 'Invalid email address.'}), 400

    if is_disposable(email):
        return jsonify({'error': 'Disposable email addresses are not allowed.'}), 400

    # Формируем HTML-тело письма с информацией из формы
    html_body = f"""
    <h2>New Contact Form Submission</h2>
    <p><strong>Name:</strong> {name}</p>
    <p><strong>Email:</strong> {email}</p>
    <p><strong>Phone:</strong> {phone if phone else 'N/A'}</p>
    <p><strong>Company:</strong> {company if company else 'N/A'}</p>
    <p><strong>Message:</strong><br>{message_text}</p>
    """

    message = EmailMessage()
    message.set_content(f"New contact form submission from {name}.", subtype='plain')
    message.add_alternative(html_body, subtype='html')
    message['To'] = DEFAULT_SENDER  # Отправляем на свой email, чтобы получать заявки
    message['From'] = DEFAULT_SENDER
    message['Subject'] = f'Contact Form Submission from {name}'

    try:
        service = get_gmail_service()
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        result = service.users().messages().send(userId='me', body=create_message).execute()

        return jsonify({'message': 'Thank you! Your message has been sent.', 'id': result['id']})
    except Exception as e:
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500
