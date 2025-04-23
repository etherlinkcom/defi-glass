import os
import logging

from hanji import hanji_get_total_tvl

logging.basicConfig(level=logging.INFO)

functions_to_run = [
    hanji_get_total_tvl
]

def main():
    logging.info("Starting job")
    for func in functions_to_run:
        env_var = f"RUN_{func.__name__.upper()}"
        if os.environ.get(env_var, 'false').lower() == 'true':
            logging.info(f"Starting {func.__name__}")
            try:
                func() 
                logging.info(f"Completed {func.__name__}")
            except Exception as e:
                logging.error(f"Error running {func.__name__}: {e}")
    logging.info("Job completed")

if __name__ == '__main__':
    main()
