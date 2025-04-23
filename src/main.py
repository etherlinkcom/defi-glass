import os
import logging
import psycopg2

from hanji import hanji_get_total_tvl
from superlend import superlend_get_total_tvl

logging.basicConfig(level=logging.INFO)

functions_to_run = [
    hanji_get_total_tvl,
    superlend_get_total_tvl
]

DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

def main():
    logging.info("Starting job")

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    for func in functions_to_run:
        env_var = f"RUN_{func.__name__.upper()}"
        if os.environ.get(env_var, 'false').lower() == 'true':
            logging.info(f"Starting {func.__name__}")
            try:
                func(cursor)
                logging.info(f"Completed {func.__name__}")
                conn.commit() 
            except Exception as e:
                logging.error(f"Error running {func.__name__}: {e}")
                conn.rollback()
    
    cursor.close()
    conn.close()
    logging.info("Job completed")

if __name__ == '__main__':
    main()
