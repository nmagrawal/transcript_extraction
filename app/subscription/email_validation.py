from email_validator import validate_email, EmailNotValidError
from disposable_email_domains import blocklist

def validate_email_address(email):
    try:
        # Check that the email address is valid. Turn on check_deliverability
        emailinfo = validate_email(email, check_deliverability=True)
        email = emailinfo.normalized

        # Inline disposable email check using blocklist from disposable_email_domains
        domain = email.split('@')[-1].lower()
        if domain in blocklist:
            return "Disposable email addresses are not allowed."

        return email
    except EmailNotValidError as e:
        return str(e)

    
