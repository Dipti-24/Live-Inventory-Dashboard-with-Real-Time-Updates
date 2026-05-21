# models.py

import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    Numeric,
    Enum,
    CheckConstraint,
    Computed,
    func
)
from sqlalchemy.orm import declarative_base

# Base class for our declarative models
Base = declarative_base()

# Define an Enum for our transaction types, matching the PostgreSQL ENUM
class TransactionTypeEnum(enum.Enum):
    Purchase = "Purchase"
    Sale = "Sale"


class Transaction(Base):
    __tablename__ = 'transactions'

    # --- Table Columns ---
    transaction_id = Column(Integer, primary_key=True)
    
    transaction_date = Column(Date, nullable=False, server_default=func.current_date())
    
    product_name = Column(String(255), nullable=False, index=True)
    
    transaction_type = Column(Enum(TransactionTypeEnum, name="transaction_type_enum", create_type=False), nullable=False)
    
    quantity = Column(Integer, nullable=False)
    
    unit_cost = Column(Numeric(10, 2), nullable=False)
    
    unit_price = Column(Numeric(10, 2), nullable=False, server_default="0.00")

    # This is the Python equivalent of the GENERATED ALWAYS AS column in PostgreSQL
    total_profit_loss = Column(
        Numeric(12, 2),
        Computed(
            "CASE WHEN transaction_type = 'Sale' THEN (unit_price - unit_cost) * quantity ELSE 0.00 END",
            persisted=True,
        ),
    )

    # --- Table-level Constraints ---
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('unit_cost >= 0', name='check_unit_cost_non_negative'),
        CheckConstraint('unit_price >= 0', name='check_unit_price_non_negative'),
    )

    def __repr__(self):
        return (f"<Transaction(id={self.transaction_id}, "
                f"type='{self.transaction_type.name}', "
                f"product='{self.product_name}', "
                f"quantity={self.quantity})>")