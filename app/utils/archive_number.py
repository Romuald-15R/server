import random
import string
from datetime import datetime

def generate_archive_number():
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ARC-{date_part}-{random_part}"