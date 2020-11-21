from typing import AnyStr

from gavel.models import db
import gavel.crowd_bt as crowd_bt
from sqlalchemy.orm.exc import NoResultFound

view_table = db.Table(
    'view',
    db.Column('item_id', db.Integer, db.ForeignKey('item.id')),
    db.Column('annotator_id', db.Integer, db.ForeignKey('annotator.id'))
)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Text, nullable=False)
    # location = db.Column(db.Text, nullable=False)
    identifier = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    team_name = db.Column(db.Text, nullable=False)
    presentation_link = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    viewed = db.relationship('Annotator', secondary=view_table)
    prioritized = db.Column(db.Boolean, default=False, nullable=False)

    mu = db.Column(db.Float)
    sigma_sq = db.Column(db.Float)

    # def __init__(self, name, location, description, identifier):
    def __init__(self, name: AnyStr, description: AnyStr, identifier: AnyStr, team_name: AnyStr, presentation_link: AnyStr):
        self.name = name
        # self.location = location
        self.description = description
        self.team_name = team_name
        self.presentation_link = presentation_link
        self.identifier = identifier
        self.mu = crowd_bt.MU_PRIOR
        self.sigma_sq = crowd_bt.SIGMA_SQ_PRIOR

    @classmethod
    def by_id(cls, uid):
        if uid is None:
            return None
        try:
            item: Item = cls.query.get(uid)
        except NoResultFound:
            return None
        return item

    @classmethod
    def by_identifier(cls, identifier):
        if identifier is None:
            return None
        try:
            item: Item = cls.query.filter(cls.identifier == identifier).one()
        except NoResultFound:
            return None
        return item

