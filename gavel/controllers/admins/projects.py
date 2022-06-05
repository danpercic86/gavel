from flask import (
    render_template,
)

import gavel.stats as stats
import gavel.utils as utils
from gavel import app
from gavel.models import (
    Annotator,
    Item, Decision,
)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


@app.route("/admin/projects")
@utils.requires_auth
def admin_projects():
    stats.check_send_telemetry()
    annotators = Annotator.query.order_by(Annotator.id).all()
    items = Item.query.order_by(Item.id).all()

    decisions = Decision.query.all()
    # counts = {}
    item_counts = {}

    for d in decisions:
        # jury_id = d.annotator_id
        winner_id = d.winner_id
        loser_id = d.loser_id
        # counts[jury_id] = counts.get(jury_id, 0) + 1
        item_counts[winner_id] = item_counts.get(winner_id, 0) + 1
        item_counts[loser_id] = item_counts.get(loser_id, 0) + 1

    viewed = {i.id: {a.id for a in i.viewed} for i in items}
    skipped = {}

    for jury_id in annotators:
        for i in jury_id.ignore:
            if jury_id.id not in viewed[i.id]:
                skipped[i.id] = skipped.get(i.id, 0) + 1

    return render_template(
        "admin/projects.html",
        is_admin=True,
        skipped=skipped,
        items=items,
        item_counts=item_counts,
    )
