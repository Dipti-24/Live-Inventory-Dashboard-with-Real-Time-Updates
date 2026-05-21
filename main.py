import json
from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

# Your existing database and models imports
from database.database import SessionLocal, create_db_and_tables, engine
from database.models import Transaction, TransactionTypeEnum, Base
from helpers.sse_manager import trigger_update, update_event
from agents.agent_logic import get_agent_executor

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    user_input: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

class ClearDBRequest(BaseModel):
    """Schema for the password-protected database clearing endpoint."""
    password: str

# --- Agent Executor ---
# Load the agent executor once at startup
try:
    agent_executor = get_agent_executor()
    logger.info("Agent executor loaded successfully.")
except Exception as e:
    logger.critical(f"Failed to load agent executor: {e}")
    agent_executor = None


# The lifespan context manager to create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- FastAPI application starting up ---")
    create_db_and_tables()
    yield
    print("--- FastAPI application shutting down ---")

# Initialize the FastAPI app with the lifespan event handler
app = FastAPI(lifespan=lifespan)

# Setup Jinja2 templates to find your index.html
templates = Jinja2Templates(directory="templates")

# --- Helper function to serialize database objects ---
def serialize_transactions(transactions):
    """Converts a list of Transaction SQLAlchemy objects into a JSON-serializable list of dicts."""
    results = []
    for tx in transactions:
        results.append({
            "transaction_id": tx.transaction_id,
            "transaction_date": tx.transaction_date.isoformat(), # Convert date to string
            "product_name": tx.product_name,
            "transaction_type": tx.transaction_type.value, # Get the string value from Enum
            "quantity": tx.quantity,
            "unit_cost": float(tx.unit_cost), # Convert Decimal to float
            "unit_price": float(tx.unit_price),
            "total_profit_loss": float(tx.total_profit_loss)
        })
    return results

# ===== API ENDPOINTS =====

# --- 1. Endpoint to serve the main HTML page ---
@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- The LISTENER Endpoint ---
@app.get("/events")
async def sse_events(request: Request):
    """
    This endpoint now WAITS for the `update_event` signal
    instead of running on a timer.
    """
    async def event_generator():
        while True:
            # Check if client is still connected before waiting
            if await request.is_disconnected():
                print("Client disconnected.")
                break

            try:
                # Suspend execution until the global flag is raised
                await update_event.wait()
            finally:
                # Clear the flag immediately so we can catch the NEXT update
                update_event.clear()

            # Once the event is triggered, fetch the fresh data from the DB
            db = SessionLocal()
            transactions = db.query(Transaction).order_by(Transaction.transaction_id.desc()).all()
            yield f"data: {json.dumps(serialize_transactions(transactions))}\n\n"
            db.close()

    # When a client first connects, immediately trigger an initial data load.
    await trigger_update() 
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --- The TRIGGER Endpoint (Standard API Endpoint Example) ---
class TransactionCreate(BaseModel):
    product_name: str
    quantity: int
    unit_cost: float

@app.post("/transactions/sale")
async def create_sale(item: TransactionCreate):
    """
    Example function to change the database via a standard REST call (bypassing the AI).
    """
    print(f"Received request to log a new sale for: {item.product_name}")
    db = SessionLocal()
    try:
        new_sale = Transaction(
            product_name=item.product_name,
            transaction_type=TransactionTypeEnum.Sale,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            unit_price=item.unit_cost * 1.5 
        )
        db.add(new_sale)
        db.commit()
    finally:
        db.close()

    # Broadcast to all SSE clients that a change just happened
    await trigger_update()

    return {"status": "success", "message": f"Sale of {item.product_name} recorded."}


# --- The AI Agent Endpoint ---
@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """Handles the chat interaction with the agent."""
    logger.info(f"Received chat request for session: {request.session_id}")
    logger.debug(f"User input: {request.user_input}")

    if not agent_executor:
        logger.error("Agent executor is not available.")
        raise HTTPException(status_code=500, detail="Agent is not available")

    try:
        conversation_id = request.session_id
        
        # 1. Ask the AI to do its job
        result = agent_executor.invoke(
            {"messages": [("user", request.user_input)]},
            config={"configurable": {"thread_id": conversation_id}}
        )
        
        # 2. Extract the final text response from the LLM
        agent_response = result['messages'][-1].content
        logger.info(f"Agent response for session {request.session_id}: {agent_response}")
        
        # 3. CRITICAL FIX: Trigger the live UI update here!
        # If the AI used a tool, the database changed. We tell the SSE endpoint to push
        # the fresh database to the frontend right before we return the chat message.
        await trigger_update()
        
        # 4. Return the chat message to the frontend widget
        return ChatResponse(response=agent_response, session_id=request.session_id)

    except Exception as e:
        logger.error(f"Error during chat processing for session {request.session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


# --- The Database Wipe Endpoint ---
@app.post("/delete", status_code=status.HTTP_200_OK)
async def clear_database(request: ClearDBRequest):
    """
    DANGER ZONE: Deletes all tables and data from the database and recreates them.
    Requires a password for authorization.
    """
    SECRET_PASSWORD = "delete"

    if request.password != SECRET_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect password. You are not authorized to perform this action.",
        )
    
    print("Authorization successful. Clearing database...")
    try:
        # Drop all tables managed by the Base metadata
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped.")
        
        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        print("All tables recreated.")

        # Tell connected dashboards to clear their screens
        await trigger_update()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while clearing the database: {e}",
        )
    
    return {"status": "success", "message": "Database has been cleared and reset successfully."}