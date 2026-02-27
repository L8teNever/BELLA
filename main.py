#!/usr/bin/env python
"""
Bella - Docker Container Backup System
Main entry point for the application
"""

import os
import sys
import logging
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Start the Bella application"""

    logger.info("=" * 70)
    logger.info("Starting Bella - Docker Container Backup System")
    logger.info("=" * 70)

    try:
        # Create Flask app
        app = create_app()

        # Get configuration
        host = os.getenv('FLASK_HOST', '0.0.0.0')
        port = int(os.getenv('FLASK_PORT', 5000))
        debug = os.getenv('FLASK_ENV', 'production') == 'development'

        logger.info(f"Server configuration:")
        logger.info(f"  Host: {host}")
        logger.info(f"  Port: {port}")
        logger.info(f"  Debug: {debug}")
        logger.info(f"  Environment: {os.getenv('FLASK_ENV', 'production')}")
        logger.info("")
        logger.info("Bella is running! Access it at: http://localhost:5000")
        logger.info("")

        # Run application
        app.run(host=host, port=port, debug=debug)

    except Exception as e:
        logger.error(f"Failed to start Bella: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
