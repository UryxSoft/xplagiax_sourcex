#!/usr/bin/env python3
"""
Flask Application Entry Point
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# Create app
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f"🚀 Starting xplagiax_sourcex API")
    print(f"🌐 Running on http://{host}:{port}")
    print(f"🔧 Debug mode: {debug}\n")
    
    app.run(host=host, port=port, debug=debug, threaded=True)