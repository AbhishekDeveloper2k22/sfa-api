from datetime import datetime
import pytz
from pymongo import ReturnDocument
from sfa.database import client1


def generate_unique_code(
    entity_type: str,
    prefix: str,
    date_value: str = None,
    db_collection=None,
    sequence_length: int = 3
) -> str:
    """
    Generic function to generate unique codes for any entity
    Format: PREFIX-YYYY-001
    
    Args:
        entity_type: Type of entity (e.g., 'order', 'lead', 'customer', 'invoice')
        prefix: Code prefix (e.g., 'PO', 'LD', 'CUST', 'INV')
        date_value: Date string in YYYY-MM-DD format (optional, uses current date if None)
        db_collection: MongoDB collection for counters (optional, uses default if None)
        sequence_length: Number of digits for sequence (default: 3, e.g., 001, 002)
    
    Returns:
        Unique code string (e.g., PO-2024-001, LD-2024-015)
    
    Examples:
        generate_unique_code('order', 'PO', '2024-01-15') -> 'PO-2024-001'
        generate_unique_code('lead', 'LD') -> 'LD-2024-001'
        generate_unique_code('customer', 'CUST', '2024-05-20') -> 'CUST-2024-001'
    """
    # Extract year from date_value or use current year
    try:
        if date_value:
            year_str = str(date_value)[0:4]
        else:
            timezone = pytz.timezone("Asia/Kolkata")
            year_str = str(datetime.now(timezone).year)
    except Exception:
        timezone = pytz.timezone("Asia/Kolkata")
        year_str = str(datetime.now(timezone).year)
    
    # Get counter collection
    if db_collection is None:
        client_database = client1["talbros"]
        counters_collection = client_database["counters"]
    else:
        counters_collection = db_collection
    
    # Counter key format: {entity_type}_code_{prefix}_{year}
    # Examples: order_code_PO_2024, lead_code_LD_2024
    counter_key = f"{entity_type}_code_{prefix}_{year_str}"
    
    # Atomic increment using findAndModify to get next sequence number
    counter_doc = counters_collection.find_one_and_update(
        {"_id": counter_key},
        {"$inc": {"sequence": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    
    sequence_number = counter_doc.get("sequence", 1)
    
    # Format sequence with leading zeros
    sequence_str = str(sequence_number).zfill(sequence_length)
    
    # Generate final code
    unique_code = f"{prefix}-{year_str}-{sequence_str}"
    
    return unique_code


def generate_order_code(order_type: str, order_date: str, db_collection=None) -> str:
    """
    Generate unique order code in format: PO-2024-001 or SO-2024-001
    Uses auto-increment counter to ensure uniqueness
    
    Args:
        order_type: Order type (Primary/Secondary)
        order_date: Order date in YYYY-MM-DD format
        db_collection: MongoDB collection for counters (optional, uses default if None)
    
    Returns:
        Unique order code string (e.g., PO-2024-001)
    """
    # Determine prefix based on order type
    order_type_clean = (order_type or "Primary").strip()
    code_prefix = "PO" if order_type_clean.lower() == "primary" else "SO"
    
    # Use generic function
    return generate_unique_code(
        entity_type="order",
        prefix=code_prefix,
        date_value=order_date,
        db_collection=db_collection,
        sequence_length=3
    )


def generate_lead_code(lead_date: str = None, db_collection=None) -> str:
    """
    Generate unique lead code in format: LD-2024-001
    
    Args:
        lead_date: Lead creation date in YYYY-MM-DD format (optional)
        db_collection: MongoDB collection for counters (optional, uses default if None)
    
    Returns:
        Unique lead code string (e.g., LD-2024-001)
    """
    return generate_unique_code(
        entity_type="lead",
        prefix="LD",
        date_value=lead_date,
        db_collection=db_collection,
        sequence_length=3
    )


def generate_customer_code(customer_date: str = None, db_collection=None) -> str:
    """
    Generate unique customer code in format: CUST-2024-001
    
    Args:
        customer_date: Customer creation date in YYYY-MM-DD format (optional)
        db_collection: MongoDB collection for counters (optional, uses default if None)
    
    Returns:
        Unique customer code string (e.g., CUST-2024-001)
    """
    return generate_unique_code(
        entity_type="customer",
        prefix="CUST",
        date_value=customer_date,
        db_collection=db_collection,
        sequence_length=3
    )


def generate_invoice_code(invoice_date: str = None, db_collection=None) -> str:
    """
    Generate unique invoice code in format: INV-2024-001
    
    Args:
        invoice_date: Invoice creation date in YYYY-MM-DD format (optional)
        db_collection: MongoDB collection for counters (optional, uses default if None)
    
    Returns:
        Unique invoice code string (e.g., INV-2024-001)
    """
    return generate_unique_code(
        entity_type="invoice",
        prefix="INV",
        date_value=invoice_date,
        db_collection=db_collection,
        sequence_length=3
    )
