from flask import (
    redirect,
    request,
    url_for,
)

import gavel.utils as utils
from gavel import app
from gavel.models import (
    Item,
    db,
    with_retries,
)


@app.route("/admin/item_patch", methods=["POST"])
@utils.requires_auth
def item_patch():
    item = Item.by_id(request.form["item_id"])

    def tx():
        if not item:
            return utils.user_error("Item %s not found " % request.form["item_id"])
        if "location" in request.form:
            item.location = request.form["location"]
        if "name" in request.form:
            item.name = request.form["name"]
        if "description" in request.form:
            item.description = request.form["description"]

    if "team_name" in request.form:
        item.description = request.form["team_name"]
    if "presentation_link" in request.form:
        item.description = request.form["presentation_link"]
        db.session.commit()

    with_retries(tx)

    return redirect(url_for("item_detail", item_id=item.id))
