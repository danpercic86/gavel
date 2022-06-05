from flask import (
    render_template, url_for,
)

import gavel.stats as stats
import gavel.utils as utils
from gavel import app
from gavel.models import (
    Annotator,
    Decision, Item,
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
        "admin/judges/index.html",
        is_admin=True,
        annotators=annotators,
        counts=counts,
    )


@app.route("/admin/judges/<judge_id>/")
@utils.requires_auth
def judge_details(judge_id: str):
    judge = Annotator.by_id(judge_id)

    if not judge:
        return utils.user_error(f"Judge {judge_id} not found")

    seen = Item.query.filter(Item.viewed.contains(judge)).all()
    ignored_ids = {ignored.id for ignored in judge.ignore}

    if ignored_ids:
        skipped = Item.query.filter(
            Item.id.in_(ignored_ids) & ~Item.viewed.contains(judge)
        )
    else:
        skipped = []

    return render_template(
        "admin/judges/detail.html",
        annotator=judge,
        is_admin=True,
        login_link=judge_login_link(judge),
        seen=seen,
        skipped=skipped,
    )


def judge_login_link(judge: Annotator):
    return url_for("login", secret=judge.secret, _external=True)
