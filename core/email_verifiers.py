import re
import dns.resolver
import smtplib
from validate_email_address import validate_email
from disposable_email_domains import blocklist

DISPOSABLE_DOMAINS = blocklist

def is_valid_syntax(email):
    """Check basic email syntax using regex."""
    pattern = r"^[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$"
    return re.match(pattern, email) is not None

def has_mx_record(domain):
    """Check if domain has MX records."""
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return len(answers) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
        return False

def is_disposable(email):
    """Check if email belongs to a disposable domain."""
    domain = email.split("@")[-1]
    return domain.lower() in DISPOSABLE_DOMAINS

def verify_email(email):
    if not is_valid_syntax(email):
        return "❌ Invalid syntax"

    domain = email.split("@")[1]
    if not has_mx_record(domain):
        print("❌ No MX record")
        return False

    if is_disposable(email):
        print("❌ Disposable email")
        return False

    return True

# Test
if __name__ == "__main__":
    test_email = "kkadenovich@gmail.com"
    print(f"{test_email}: {verify_email(test_email)}")
