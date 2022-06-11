import psycopg2.errors
import sqlalchemy.exc
from flask_sqlalchemy import SQLAlchemy


class SerializableAlchemy(SQLAlchemy):
    def apply_driver_hacks(self, app, info, options):
        if "isolation_level" not in options:
            # XXX is this slow? are there better ways?
            options["isolation_level"] = "REPEATABLE READ"
        return super(SerializableAlchemy, self).apply_driver_hacks(app, info, options)


db = SerializableAlchemy()

from gavel.models.annotator import Annotator, ignore_table
from gavel.models.item import Item, view_table
from gavel.models.decision import Decision
from gavel.models.setting import Setting


def with_retries(tx_func):
    """
    Keep retrying a function that involves a database transaction until it
    succeeds.

    This only retries due to serialization failures; all other types of
    exceptions are re-raised.
    """
    while True:
        try:
            tx_func()
        except sqlalchemy.exc.OperationalError as err:
            if not isinstance(err.orig, psycopg2.errors.SerializationFailure):
                raise
            db.session.rollback()
        else:
            break
