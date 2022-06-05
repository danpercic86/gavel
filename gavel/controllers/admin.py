from typing import List

import psycopg2.errors
from flask import (
    redirect,
    request,
    url_for,
)
from sqlalchemy.exc import IntegrityError

import gavel.settings as settings
import gavel.utils as utils
from gavel import app
from gavel.controllers.admins.judges import judge_login_link
from gavel.controllers.admins.projects import parse_upload_form
from gavel.models import (
    Annotator,
    Item,
    db,
    with_retries,
    ignore_table,
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


@app.route("/admin/annotator", methods=["POST"])
@utils.requires_auth
def annotator_actions():
    action = request.form["action"]

    if action == "Submit":
        data = parse_upload_form()
        added = []
        if data:
            # validate data
            for index, row in enumerate(data):
                if len(row) != 3:
                    return utils.user_error(
                        "Bad data: row %d has %d elements (expecting 3)"
                        % (index + 1, len(row))
                    )

            def tx():
                for row in data:
                    annotator = Annotator(*row)
                    added.append(annotator)
                    db.session.add(annotator)
                db.session.commit()

            with_retries(tx)
            try:
                email_invite_links(added)
            except Exception as e:
                return utils.server_error(str(e))
    elif action == "Email":
        annotator_id = request.form["annotator_id"]
        try:
            email_invite_links(Annotator.by_id(annotator_id))
        except Exception as e:
            return utils.server_error(str(e))
    elif action == "Disable" or action == "Enable":
        annotator_id = request.form["annotator_id"]
        target_state = action == "Enable"

        def tx():
            Annotator.by_id(annotator_id).active = target_state
            db.session.commit()

        with_retries(tx)
    elif action == "Delete":
        annotator_id = request.form["annotator_id"]
        try:

            def tx():
                db.session.execute(
                    ignore_table.delete(ignore_table.c.annotator_id == annotator_id)
                )
                Annotator.query.filter_by(id=annotator_id).delete()
                db.session.commit()

            with_retries(tx)
        except IntegrityError as e:
            if isinstance(e.orig, psycopg2.errors.ForeignKeyViolation):
                return utils.server_error(
                    "Judges can't be deleted once they have voted on a project. You can use the 'disable' functionality instead, which has a similar effect, locking out the judge and preventing them from voting on any other projects."
                )
            else:
                return utils.server_error(str(e))
    return redirect(url_for("admin"))


def email_invite_links(annotators: List[Annotator] | Annotator):
    if settings.DISABLE_EMAIL or annotators is None:
        return
    if not isinstance(annotators, list):
        annotators = [annotators]

    emails = []
    for annotator in annotators:
        link = judge_login_link(annotator)
        raw_body = settings.EMAIL_BODY.format(name=annotator.name, link=link)
        body = "\n\n".join(utils.get_paragraphs(raw_body))
        emails.append((annotator.email, settings.EMAIL_SUBJECT, body))

    if settings.USE_SENDGRID and settings.SENDGRID_API_KEY is not None:
        utils.send_sendgrid_emails(emails)
    else:
        utils.send_emails.delay(emails)
