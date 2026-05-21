from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional, Literal
from decimal import Decimal

class RecordSaleToolInput(BaseModel):
    product_name: str = Field(..., description="The name of the product being sold.")
    quantity: int = Field(..., gt=0, description="The number of units sold. Must be a positive integer.")
    unit_price: float = Field(..., gt=0, description="The selling price for a single unit.")

class RecordPurchaseToolInput(BaseModel):
    product_name: str = Field(..., description="The name of the product being purchased.")
    quantity: int = Field(..., gt=0, description="The number of units purchased. Must be a positive integer.")
    unit_cost: float = Field(..., ge=0, description="The cost for a single unit of the product.")

class GetStockLevelToolInput(BaseModel):
    product_name: Optional[str] = Field(None, description="The specific product to check stock for.")

class StockLevelItem(BaseModel):
    product_name: str
    stock_on_hand: int

class StockLevelOutput(BaseModel):
    stock_levels: List[StockLevelItem]

class GetProfitReportToolInput(BaseModel):
    product_name: Optional[str] = Field(None, description="Optional: Filter report for a single product.")
    start_date: Optional[date] = Field(None, description="Optional: Start date (YYYY-MM-DD).")
    end_date: Optional[date] = Field(None, description="Optional: End date (YYYY-MM-DD).")

class ProfitItem(BaseModel):
    product_name: str
    total_profit: Decimal

class ProfitReportOutput(BaseModel):
    query_details: str = Field(..., description="A human-readable summary of the report query.")
    total_profit_all_products: Decimal
    profit_by_product: List[ProfitItem]

class GetBestsellersToolInput(BaseModel):
    rank_by: Literal['quantity', 'profit'] = Field('quantity', description="Rank by 'quantity' or 'profit'.")
    limit: int = Field(5, gt=0, description="The number of top products to return.")
    start_date: Optional[date] = Field(None)
    end_date: Optional[date] = Field(None)

class BestsellerItem(BaseModel):
    rank: int
    product_name: str
    units_sold: Optional[int] = None
    total_profit: Optional[Decimal] = None

class BestsellersReportOutput(BaseModel):
    query_details: str = Field(..., description="A human-readable summary.")
    bestsellers: List[BestsellerItem]