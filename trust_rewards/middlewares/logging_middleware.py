import logging
import time
from fastapi import Request

async def log_requests(request: Request, call_next):
    # Record start time
    start_time = time.time()
    
    # Log the request details
    logging.info(f"Starting request: {request.method} {request.url}")
    
    # Process the request
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log completion with timing
        logging.info(
            f"Request completed: {request.method} {request.url}\n"
            f"Processing time: {process_time:.2f} seconds\n"
            f"Status code: {response.status_code}"
        )
        
        # Add processing time header to response
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    except Exception as exc:
        # Log any errors with timing
        process_time = time.time() - start_time
        logging.error(
            f"Request failed: {request.method} {request.url}\n"
            f"Processing time: {process_time:.2f} seconds\n"
            f"Error: {str(exc)}"
        )
        raise
