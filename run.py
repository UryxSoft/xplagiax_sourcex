#!/usr/bin/env python3
"""
Flask Application Entry Point
"""
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.logging_config import setup_logging

# Setup logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
setup_logging(level=log_level)

# Create Flask app
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    # Get host and port from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f"🚀 Starting xplagiax_sourcex API")
    print(f"📍 Environment: {config_name}")
    print(f"🌐 Running on http://{host}:{port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"📚 Documentation: http://{host}:{port}/api/health")
    print()
    
    # Run the app
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )