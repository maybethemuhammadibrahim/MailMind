# backend/main.py
# ---------------------------------------------------------------
# Entry point for the MailMind FastAPI backend. Sets up CORS so
# the React frontend (localhost:5173) can talk to the API, and
# registers all route modules under their URL prefixes.
# ---------------------------------------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import each route module — these are separate files in routes/
from routes import auth, emails, pipeline, todos, meetings, orders, analytics, pages
from fastapi.staticfiles import StaticFiles

def create_app():
    """
    Creates and configures the FastAPI application.

    Returns:
        FastAPI: the fully configured app instance with CORS
                 and all route modules registered.
    """

    # Create the main FastAPI app with metadata for the auto-docs page
    app = FastAPI(
        title="MailMind API",
        description="AI-powered email assistant backend",
        version="0.1.0"
    )

    # --- CORS configuration ---
    # CORS (Cross-Origin Resource Sharing) allows the React frontend
    # running on a different port (5173) to make requests to this API
    # running on port 8000. Without this, the browser blocks the requests.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",   # Vite dev server
            "http://127.0.0.1:5173",  # Alternative localhost
        ],
        allow_credentials=True,       # Allow cookies / auth headers
        allow_methods=["*"],          # Allow all HTTP methods (GET, POST, etc.)
        allow_headers=["*"],          # Allow all headers
    )

    # --- Static Files ---
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # --- Register UI routes ---
    app.include_router(pages.router, tags=["Pages"])

    # --- Register API route modules ---
    # Each router handles a group of related endpoints.
    # The prefix sets the URL path for all routes in that module.
    # The tag groups them together in the API docs at /docs.
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(emails.router, prefix="/api/emails", tags=["Emails"])
    app.include_router(pipeline.router, prefix="/api", tags=["AI Pipeline"])
    app.include_router(todos.router, prefix="/api/todos", tags=["Todos"])
    app.include_router(meetings.router, prefix="/api/meetings", tags=["Meetings"])
    app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])

    return app

# Create the app instance — uvicorn looks for this variable
app = create_app()



@app.get("/api/health")
def root():
    """
    Health-check endpoint. Returns a simple JSON message to confirm
    the API is running. Useful for n8n connectivity checks.

    Returns:
        dict: a welcome message with the app name
    """
    return {"message": "MailMind API is running", "status": "ok"}
