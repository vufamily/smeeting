"""
Meeting Assistant - Main Entry Point
AI-powered meeting transcription and minutes generation
"""

import os
import sys
import logging
from flask import Flask

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import CONFIG
from src.services.processing_service import ProcessingService


def create_app(config: dict = None) -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        config: Optional configuration override
        
    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    
    # Load configuration
    cfg = config or CONFIG
    
    # Configure Flask
    app.config['MAX_CONTENT_LENGTH'] = cfg['flask']['max_content_length']
    
    # Setup logging
    _setup_logging(cfg['logging'])
    logger = logging.getLogger(__name__)
    
    # Ensure directories exist
    for key, path in cfg['storage'].items():
        os.makedirs(path, exist_ok=True)
    
    # Initialize database (if SQLAlchemy is configured)
    db_session = None
    
    # Initialize processing service
    processing_service = ProcessingService(cfg, db_session)
    
    # Register API routes
    from src.api import init_api_routes
    init_api_routes(app, cfg, processing_service)
    
    logger.info("Meeting Assistant Flask app initialized")
    
    return app


def _setup_logging(log_config: dict):
    """Setup logging configuration"""
    os.makedirs(log_config['file'].rsplit('/', 1)[0], exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_config['level']),
        format=log_config['format'],
        handlers=[
            logging.FileHandler(log_config['file'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main entry point"""
    app = create_app()
    
    config = CONFIG['flask']
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting Meeting Assistant API on {config['host']}:{config['port']}")
    
    app.run(
        host=config['host'],
        port=config['port'],
        debug=config['debug']
    )


if __name__ == '__main__':
    main()
