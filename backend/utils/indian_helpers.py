"""
Helper utilities for Indian-specific features
"""
import re


def validate_indian_phone(phone_number):
    """
    Validate Indian phone number format
    Accepts: 10-digit numbers, with optional +91 or 91 prefix
    """
    if not phone_number:
        return False

    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone_number)

    # Check for valid Indian phone patterns
    patterns = [
        r'^[6-9]\d{9}$',           # 10 digits starting with 6-9
        r'^\+91[6-9]\d{9}$',       # +91 followed by 10 digits
        r'^91[6-9]\d{9}$',         # 91 followed by 10 digits
        r'^0[6-9]\d{9}$'           # 0 followed by 10 digits
    ]

    return any(re.match(pattern, cleaned) for pattern in patterns)


def format_indian_currency(amount, include_symbol=True):
    """
    Format amount in Indian currency style (lakhs, crores)
    Example: 150000 -> ₹1,50,000
    """
    if amount is None:
        return '₹0' if include_symbol else '0'

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return '₹0' if include_symbol else '0'

    # Format with Indian comma separation
    if amount < 0:
        negative = True
        amount = abs(amount)
    else:
        negative = False

    # Convert to string and split
    amount_str = f"{amount:.2f}"
    integer_part, decimal_part = amount_str.split('.')

    # Indian number system: last 3 digits, then groups of 2
    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]

        # Add commas every 2 digits from right to left
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]

        formatted = ','.join(reversed(groups)) + ',' + last_three

    result = f"{formatted}.{decimal_part}"

    if negative:
        result = '-' + result

    if include_symbol:
        result = '₹' + result

    return result


def calculate_gst(amount, gst_rate=18.0):
    """
    Calculate GST for a given amount
    Default GST rate is 18% (standard for fitness services in India)
    Returns: (base_amount, gst_amount, total_amount)
    """
    try:
        amount = float(amount)
        gst_rate = float(gst_rate)
    except (ValueError, TypeError):
        return (0, 0, 0)

    base_amount = amount / (1 + gst_rate / 100)
    gst_amount = amount - base_amount

    return (round(base_amount, 2), round(gst_amount, 2), round(amount, 2))


def calculate_gst_inclusive(base_amount, gst_rate=18.0):
    """
    Calculate GST-inclusive amount from base amount
    Returns: (base_amount, gst_amount, total_amount)
    """
    try:
        base_amount = float(base_amount)
        gst_rate = float(gst_rate)
    except (ValueError, TypeError):
        return (0, 0, 0)

    gst_amount = base_amount * (gst_rate / 100)
    total_amount = base_amount + gst_amount

    return (round(base_amount, 2), round(gst_amount, 2), round(total_amount, 2))


def format_indian_date(date_obj, format='short'):
    """
    Format date in Indian style
    short: DD/MM/YYYY
    long: DD Month YYYY
    """
    if not date_obj:
        return ''

    if format == 'short':
        return date_obj.strftime('%d/%m/%Y')
    elif format == 'long':
        return date_obj.strftime('%d %B %Y')
    else:
        return date_obj.isoformat()


def get_indian_state_list():
    """Return list of Indian states and union territories"""
    return [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
        'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
        'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
        'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
        'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu',
        'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry'
    ]


def get_payment_modes():
    """Return list of payment modes common in India"""
    return [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('card', 'Card (Debit/Credit)'),
        ('bank_transfer', 'Bank Transfer (NEFT/RTGS/IMPS)'),
        ('online', 'Online Payment Gateway'),
        ('cheque', 'Cheque'),
        ('other', 'Other')
    ]


def normalize_phone_number(phone_number):
    """
    Normalize Indian phone number to standard format
    Returns: 10-digit number without prefix
    """
    if not phone_number:
        return None

    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone_number)

    # Remove country code if present
    if cleaned.startswith('91') and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith('0') and len(cleaned) == 11:
        cleaned = cleaned[1:]

    # Validate and return
    if len(cleaned) == 10 and cleaned[0] in '6789':
        return cleaned

    return None
