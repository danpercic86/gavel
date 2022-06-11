from flask_sqlalchemy import SQLAlchemy


class SerializableAlchemy(SQLAlchemy):
    def apply_driver_hacks(self, app, info, options):
        if "isolation_level" not in options:
            # XXX is this slow? are there better ways?
            options["isolation_level"] = "SERIALIZABLE"
        return super(SerializableAlchemy, self).apply_driver_hacks(app, info, options)


db = SerializableAlchemy()

from gavel.models.annotator import Annotator, ignore_table
from gavel.models.item import Item, view_table
from gavel.models.decision import Decision
from gavel.models.setting import Setting
