
# Import the database initializer — creates all tables on first run
from db.sqlite import initialize_database
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from routes import (
    analytics,
    auth,
    crafter,
    dev,
    emails,
    meetings,
    orders,
    pages,
    pipeline,
    settings,
    todos,
)


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
        version="0.1.0",
    )

  
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  
            "http://127.0.0.1:5173",  
        ],
        allow_credentials=True,  
        allow_methods=["*"], 
        allow_headers=["*"],  
    )

    
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
    app.include_router(dev.router, prefix="/api/dev", tags=["Dev"])
    app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
    app.include_router(crafter.router, prefix="/api/crafter", tags=["Crafter"])

    
    # This runs initialize_database() the moment the app starts.
    # It uses CREATE TABLE IF NOT EXISTS, so it's safe to call every
    # time — it only creates tables that don't exist yet.
    @app.on_event("startup")
    def on_startup():
        """
        Runs once when uvicorn starts the app. Ensures all SQLite
        tables exist before the first request is handled.
        """
        print("[STARTUP] Initializing database...")
        initialize_database()
        print("[STARTUP] Database ready.")

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
