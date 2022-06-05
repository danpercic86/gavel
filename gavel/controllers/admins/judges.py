from flask import (
    render_template,
)

import gavel.stats as stats
import gavel.utils as utils
from gavel import app
from gavel.models import (
    Annotator, Decision,
)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


@app.route("/admin/judges")
@utils.requires_auth
def admin_judges():
    stats.check_send_telemetry()
    annotators = Annotator.query.order_by(Annotator.id).all()

    decisions = Decision.query.all()
    counts = {}

    for decision in decisions:
        jury_id = decision.annotator_id
        counts[jury_id] = counts.get(jury_id, 0) + 1

    return render_template(
        "admin/judges.html",
        is_admin=True,
        annotators=annotators,
        counts=counts,
    )
