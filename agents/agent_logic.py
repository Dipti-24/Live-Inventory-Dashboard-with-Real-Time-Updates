import os
import logging
from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict
from decimal import Decimal
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, BaseMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from database.database import SessionLocal
from database.models import Transaction, TransactionTypeEnum
from sqlalchemy import func, case
from database.agent_io_models import (
    RecordSaleToolInput, RecordPurchaseToolInput,
    GetStockLevelToolInput, StockLevelOutput, StockLevelItem,
    GetProfitReportToolInput, ProfitReportOutput, ProfitItem,
    GetBestsellersToolInput, BestsellersReportOutput, BestsellerItem
)

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are an expert inventory management assistant. 
Today's date is {datetime.now().strftime('%A, %B %d, %Y')}. 
CRITICAL: When the user asks to buy or add stock, YOU MUST call the 'record_purchase' tool. Do not just reply with text."""

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

@tool
def record_purchase(input_data: RecordPurchaseToolInput) -> str:
    """Records a purchase (stock in) transaction in the database."""
    db = SessionLocal()
    try:
        new_purchase = Transaction(
            product_name=input_data.product_name,
            transaction_type=TransactionTypeEnum.Purchase.value, 
            quantity=input_data.quantity,
            unit_cost=Decimal(str(input_data.unit_cost)),
            unit_price=Decimal('0.00') 
        )
        db.add(new_purchase)
        db.commit()
        return f"Success: Recorded {input_data.quantity} units of {input_data.product_name}."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        db.close()

# ... (Include other tools like record_sale, get_stock_level, etc.)

tools = [record_purchase] # Add your other tools here
tool_node = ToolNode(tools)

# Bind tools to the model
model = ChatOpenAI(
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.environ["OPEN_API_KEY"],
    model_name="openai/gpt-4o-mini",
).bind_tools(tools)

def call_model(state: State):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}

def should_continue(state: State):
    return "tools" if state["messages"][-1].tool_calls else END

def get_agent_executor():
    graph = StateGraph(State)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=InMemorySaver())