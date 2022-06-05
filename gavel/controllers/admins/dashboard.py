from flask import (
    render_template,
)

import gavel.stats as stats
import gavel.utils as utils
from gavel import app
from gavel.models import (
    Annotator,
    Item,
    Decision,
)


@app.route("/admin/dashboard/")
@utils.requires_auth
def admin_dashboard():
    stats.check_send_telemetry()
    annotators = Annotator.query.order_by(Annotator.id).all()
    items = Item.query.order_by(Item.id).all()
    decisions = Decision.query.all()

    return render_template(
        "admin/dashboard.html",
        is_admin=True,
        annotators=annotators,
        items=items,
        votes=len(decisions),
    )
