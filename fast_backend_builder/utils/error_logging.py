import logging
import os
from logging.handlers import TimedRotatingFileHandler

from fast_backend_builder.utils.sentry import SentryService

# Ensure logs directory exists
if not os.path.exists('logs'):
    os.makedirs('logs')

# Function to set up the logger
def setup_logger(file_name='error', level=logging.ERROR):
    # Create a logger with a unique name
    logger = logging.getLogger(f'{__name__}-{file_name}')
    logger.setLevel(level)  # Set the logging level

    # Prevent duplicate handlers if the logger already exists
    if not logger.hasHandlers():
        # Create a TimedRotatingFileHandler
        file_handler = TimedRotatingFileHandler(f'logs/{file_name}.log', when='midnight', interval=1, backupCount=7)
        
        # Set the log file format
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Set suffix for log file names to include the date
        file_handler.suffix = "%Y-%m-%d"

        # Add the handler to the logger
        logger.addHandler(file_handler)
    
    return logger


# Initialize logger by calling setup_logger function
logger = setup_logger()

esb_logger = setup_logger('esb-calls', logging.INFO)


# Function to log exceptions
def log_exception(exception: Exception):
    logger.error("An error occurred: %s", exception, exc_info=True)
    try:
        SentryService.get_instance().capture_exception(exception)
    except Exception as e:
        logger.warning("Sentry is not initialized: %s", e, exc_info=True)
    
# Function to log exceptions
def log_critical(exception: Exception):
    logger.critical("Critical error occurred: %s", exception, exc_info=True)
    try:
        SentryService.get_instance().capture_exception(exception)
    except Exception as e:
        logger.warning("Sentry is not initialized: %s", e, exc_info=True)

# Function to log exceptions
def log_warning(str, *args):
    logger.warning(str, args, exc_info=True)
    
# Function to log exceptions
def log_message(str, *args):
    logger.info(str, args, exc_info=True)

# Function to log exceptions
def log_debug(str, *args):
    logger.debug(str, args, exc_info=True)
    
def log_esb_calls(api_code, request, response):
    esb_logger.info(f"""
    {f'Consumming from: {api_code}' if api_code else 'Api Call Received'}
    >>> Our Payload:
    {request}
    
    <<< Their Payload:
    {response}
    """)

# Example function that may throw an exception
def risky_operation():
    try:
        # Simulate a ZeroDivisionError
        result = 10 / 0
    except Exception as e:
        # Call the log_exception function in case of an error
        log_exception(e)

