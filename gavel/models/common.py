import time
from random import randint

import psycopg2.errors
import sqlalchemy.exc

from gavel import db


def with_retries(tx_func):
    """
    Keep retrying a function that involves a database transaction until it
    succeeds.

    This only retries due to serialization failures; all other types of
    exceptions are re-raised.
    """
    while True:
        try:
            return tx_func()
        except sqlalchemy.exc.OperationalError as err:
            if not isinstance(err.orig, psycopg2.errors.SerializationFailure):
                raise
            db.session.rollback()

        time.sleep(randint(1, 5) / 10)
