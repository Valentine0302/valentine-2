import os
import re
import smtplib

from flask import Blueprint, jsonify, request
from calculators.europe_calculator import FreightCalculator
from calculators.multimodal_calculator import MultimodalFreightCalculator
from calculators.asian_calculator import AsianFreightCalculator

from email.message import EmailMessage
from disposable_email_domains import blocklist
from core.email_verifiers import verify_email, is_disposable, validate_email

api_bp = Blueprint('api', __name__)

europe_freight_calculator = FreightCalculator()
asian_freight_calculator = AsianFreightCalculator()
multimodal_freight_calculator = MultimodalFreightCalculator()

DEFAULT_SENDER = 'requests@tspgrupp.ee'
EMAIL_PASSWORD = 'TsTr25Req'

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

    mail_strings = {
        'distance': f'<p><strong>Distance:</strong> to_replace km</p>',
        'chargeable_ldm': f'<p><strong>Chargeable Volume:</strong> to_replace LDM</p>',
        'rate': f'<p><strong>Total Freight Cost:</strong> <span style="color:green; font-weight:bold;">€to_replace</span></p>',
        'container_type': f'<p><strong>Container Type:</strong> to_replace</p>',
        'origin_port': f'<p><strong>Origin Port:</strong> to_replace</p>',
        'destination_port': f'<p><strong>Destination Port:</strong> to_replace</p>',
        'weight': f'<p><strong>Weight:</strong> to_replace kg</p>',
        'loading_meters': f'<p><strong>Loading Meters:</strong> to_replace m</p>',
        'origin_place': f'<p><strong>Origin Place:</strong> to_replace</p>',
        'destination_place': f'<p><strong>Destination Place:</strong> to_replace</p>'
    }

    html_body = '<h2>Calculation result</h2>\n\n' + '\n'.join([mail_strings[key].replace('to_replace', str(value)) for key, value in data.items() if key in mail_strings])

    message = EmailMessage()
    message.set_content("Your freight calculation result is ready.", subtype='plain')
    message.add_alternative(html_body, subtype='html')

    if to == 'me':
        to = DEFAULT_SENDER

    message['To'] = to
    message['From'] = DEFAULT_SENDER
    message['Subject'] = subject

    try:
        with smtplib.SMTP_SSL('mail.tspgrupp.ee', 465) as smtp:
            smtp.login(DEFAULT_SENDER, EMAIL_PASSWORD)
            smtp.send_message(message)
        return jsonify({'message': 'Email sent successfully'})
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

    # Basic validation
    if not name or not email or not message_text:
        return jsonify({'error': 'Name, email, and message are required.'}), 400

    if not verify_email(email):
        return jsonify({'error': 'Invalid email address.'}), 400

    if is_disposable(email):
        return jsonify({'error': 'Disposable email addresses are not allowed.'}), 400

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
    message['To'] = DEFAULT_SENDER  # Send to self to receive submissions
    message['From'] = DEFAULT_SENDER
    message['Subject'] = f'Contact Form Submission from {name}'

    try:
        with smtplib.SMTP_SSL('mail.tspgrupp.ee', 465) as smtp:
            smtp.login(DEFAULT_SENDER, EMAIL_PASSWORD)
            smtp.send_message(message)
        return jsonify({'message': 'Thank you! Your message has been sent.'})
    except Exception as e:
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500
    