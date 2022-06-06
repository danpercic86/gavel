from datetime import datetime
from functools import wraps

from flask import session, redirect, url_for
from numpy.random import random, shuffle

from gavel import crowd_bt, settings
from gavel.constants import ANNOTATOR_ID, SETTING_CLOSED, SETTING_TRUE
from gavel.models import Annotator, Item, Setting


def get_current_judge() -> Annotator:
    return Annotator.by_id(session.get(ANNOTATOR_ID, None))


def choose_next(annotator):
    items = preferred_items(annotator)

    shuffle(items)  # useful for argmax case as well in the case of ties
    if items:
        if random() < crowd_bt.EPSILON:
            return items[0]
        else:
            return crowd_bt.argmax(
                lambda i: crowd_bt.expected_information_gain(
                    annotator.alpha,
                    annotator.beta,
                    annotator.prev.mu,
                    annotator.prev.sigma_sq,
                    i.mu,
                    i.sigma_sq,
                ),
                items,
            )
    else:
        return None


def preferred_items(annotator):
    """
    Return a list of preferred items for the given annotator to look at next.

    This method uses a variety of strategies to try to select good candidate
    projects.
    """
    ignored_ids = {i.id for i in annotator.ignore}
    if ignored_ids:
        available_items = Item.query.filter(
            (Item.active == True) & (~Item.id.in_(ignored_ids))
        ).all()
    else:
        available_items = Item.query.filter(Item.active == True).all()

    prioritized_items = [i for i in available_items if i.prioritized]

    items = prioritized_items if prioritized_items else available_items

    annotators = Annotator.query.filter(
        (Annotator.active == True)
        & (Annotator.next != None)
        & (Annotator.updated != None)
    ).all()
    busy = {
        i.next.id
        for i in annotators
        if (datetime.utcnow() - i.updated).total_seconds() < settings.TIMEOUT * 60
    }
    nonbusy = [i for i in items if i.id not in busy]
    preferred = nonbusy if nonbusy else items

    less_seen = [i for i in preferred if len(i.viewed) < settings.MIN_VIEWS]

    return less_seen if less_seen else preferred


def check_open():
    return Setting.value_of(SETTING_CLOSED) != SETTING_TRUE


def check_active_annotator():
    current = get_current_judge()
    return current and current.active


def check_has_decisions():
    current = get_current_judge()
    return current and len(current.decisions) >= 2


def requires(predicate, redirect_to):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not predicate():
                return redirect(url_for(redirect_to))
            else:
                return f(*args, **kwargs)

        return decorated

    return decorator


def requires_open(redirect_to):
    return requires(check_open, redirect_to)


def requires_active_annotator(redirect_to):
    return requires(check_active_annotator, redirect_to)
