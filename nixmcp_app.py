
#!/usr/bin/env python
"""NixMCP app module for hot reloading."""

# Import the app creation function
from server import create_starlette_app

# Create the app - this is what Uvicorn will import
app = create_starlette_app()
