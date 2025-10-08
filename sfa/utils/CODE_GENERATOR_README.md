# Code Generator Utility

## Overview
Generic utility to generate unique sequential codes for any entity in the system using MongoDB atomic counters.

## Features
- ✅ **Guaranteed Uniqueness**: Uses MongoDB atomic `$inc` operations
- ✅ **Year-based Counters**: Automatic reset for each year
- ✅ **Entity-specific**: Separate sequences for different entities
- ✅ **Customizable**: Configurable prefix and sequence length
- ✅ **Thread-safe**: Atomic operations prevent race conditions

## Usage

### 1. Import the Function
```python
from sfa.utils.code_generator import generate_unique_code, generate_order_code, generate_lead_code
```

### 2. Use Pre-built Functions

#### For Orders
```python
order_code = generate_order_code(
    order_type="Primary",  # or "Secondary"
    order_date="2024-01-15"
)
# Result: PO-2024-001 or SO-2024-001
```

#### For Leads
```python
lead_code = generate_lead_code(
    lead_date="2024-01-15"  # optional
)
# Result: LD-2024-001
```

#### For Customers
```python
from sfa.utils.code_generator import generate_customer_code

customer_code = generate_customer_code(
    customer_date="2024-01-15"  # optional
)
# Result: CUST-2024-001
```

#### For Invoices
```python
from sfa.utils.code_generator import generate_invoice_code

invoice_code = generate_invoice_code(
    invoice_date="2024-01-15"  # optional
)
# Result: INV-2024-001
```

### 3. Create Custom Entity Codes

#### Example: Generate Quotation Code
```python
from sfa.utils.code_generator import generate_unique_code

quotation_code = generate_unique_code(
    entity_type="quotation",
    prefix="QT",
    date_value="2024-01-15",
    sequence_length=4  # QT-2024-0001
)
# Result: QT-2024-0001
```

#### Example: Generate Payment Code
```python
payment_code = generate_unique_code(
    entity_type="payment",
    prefix="PAY",
    date_value="2024-01-15"
)
# Result: PAY-2024-001
```

## Implementation in Services

### Step 1: Import in Service File
```python
from sfa.utils.code_generator import generate_lead_code  # or any other function
```

### Step 2: Generate Code After Insert
```python
def create_lead(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    # ... validation code ...
    
    # Insert document
    result = self.leads_collection.insert_one(lead_doc)
    
    # Generate unique code
    lead_id_str = str(result.inserted_id)
    lead_code = generate_lead_code(
        lead_date=lead_doc.get("created_at")
    )
    
    # Update document with code
    self.leads_collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"lead_code": lead_code}}
    )
    
    return {
        "success": True,
        "data": {
            "lead_id": lead_id_str,
            "lead_code": lead_code
        }
    }
```

## Database Structure

### Counters Collection
The utility uses a `counters` collection to store sequence numbers:

```json
{
  "_id": "order_code_PO_2024",
  "sequence": 15
}
```

```json
{
  "_id": "lead_code_LD_2024",
  "sequence": 42
}
```

### Counter Key Format
`{entity_type}_code_{prefix}_{year}`

Examples:
- `order_code_PO_2024`
- `order_code_SO_2024`
- `lead_code_LD_2024`
- `customer_code_CUST_2024`
- `invoice_code_INV_2024`

## Adding New Entity Types

### Option 1: Use Generic Function Directly
```python
from sfa.utils.code_generator import generate_unique_code

# In your service
ticket_code = generate_unique_code(
    entity_type="ticket",
    prefix="TKT",
    date_value="2024-01-15"
)
```

### Option 2: Create Helper Function (Recommended)
Add to `code_generator.py`:

```python
def generate_ticket_code(ticket_date: str = None, db_collection=None) -> str:
    """
    Generate unique ticket code in format: TKT-2024-001
    
    Args:
        ticket_date: Ticket creation date in YYYY-MM-DD format (optional)
        db_collection: MongoDB collection for counters (optional)
    
    Returns:
        Unique ticket code string (e.g., TKT-2024-001)
    """
    return generate_unique_code(
        entity_type="ticket",
        prefix="TKT",
        date_value=ticket_date,
        db_collection=db_collection,
        sequence_length=3
    )
```

## Code Format Examples

| Entity | Prefix | Format | Example |
|--------|--------|--------|---------|
| Primary Order | PO | PO-YYYY-NNN | PO-2024-001 |
| Secondary Order | SO | SO-YYYY-NNN | SO-2024-001 |
| Lead | LD | LD-YYYY-NNN | LD-2024-001 |
| Customer | CUST | CUST-YYYY-NNN | CUST-2024-001 |
| Invoice | INV | INV-YYYY-NNN | INV-2024-001 |
| Quotation | QT | QT-YYYY-NNNN | QT-2024-0001 |
| Payment | PAY | PAY-YYYY-NNN | PAY-2024-001 |

## Benefits

1. **No Duplicates**: Atomic MongoDB operations ensure uniqueness
2. **Scalable**: Works in multi-threaded/multi-process environments
3. **Year-based**: Counters automatically reset each year
4. **Readable**: Human-friendly sequential codes
5. **Flexible**: Easy to add new entity types
6. **Maintainable**: Centralized code generation logic

## Notes

- Counters are created automatically on first use (upsert=True)
- Each entity type + prefix + year combination has its own counter
- Sequence numbers start from 1 and increment atomically
- If date is not provided, current date is used
- Default sequence length is 3 digits (001, 002, ..., 999)
