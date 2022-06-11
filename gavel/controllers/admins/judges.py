from typing import List

import psycopg2.errors
from flask import (
    redirect,
    request,
    url_for,
)
from flask import (
    render_template,
)
from sqlalchemy.exc import IntegrityError

import gavel.settings as settings
import gavel.stats as stats
import gavel.utils as utils
from gavel import app
from gavel.controllers.admins.projects import parse_upload_form
from gavel.models import (
    Annotator,
    Item,
    db,
    ignore_table,
)
from gavel.models import (
    Decision,
)
from gavel.models.common import with_retries

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
FOREIGN_KEY_ERROR = "Judges can't be deleted once they have voted on a project. You can use the 'disable' functionality instead, which has a similar effect, locking out the judge and preventing them from voting on any other projects."


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

    login_links = {judge.id: judge_login_link(judge) for judge in annotators}
    print(login_links)

    return render_template(
        "admin/judges/index.html",
        is_admin=True,
        annotators=annotators,
        counts=counts,
        login_links=login_links,
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


@app.route("/admin/judges", methods=["POST"])
@utils.requires_auth
def upload_judge():
    data = parse_upload_form()

    if not data:
        return utils.user_error("No judges uploaded")

    added = []

    for index, row in enumerate(data):
        if len(row) != 3:
            return utils.user_error(
                f"Bad data: row {index + 1:d} has {len(row):d} elements (expecting 3)"
            )

    def tx():
        for row in data:
            annotator = Annotator(*map(lambda x: x.strip(), row))
            added.append(annotator)
            db.session.add(annotator)
        db.session.commit()

    with_retries(tx)

    # if not settings.DEBUG:
    #     try_send_emails(added)
    # else:
    #     print("DEBUG: Not sending emails")

    return redirect(url_for("admin_judges"))


@app.route("/admin/judges/send-email", methods=["POST"])
@utils.requires_auth
def email_judges():
    try:
        email_invite_links(Annotator.query.filter(Annotator.active).all())
    except Exception as e:
        return utils.server_error(str(e))

    return redirect(url_for("admin_judges"))


@app.route("/admin/judges/<judge_id>/delete", methods=["POST"])
@utils.requires_auth
def delete_judge(judge_id: str):
    try:

        def tx():
            db.session.execute(
                ignore_table.delete(ignore_table.c.annotator_id == judge_id)
            )
            Annotator.query.filter_by(id=judge_id).delete()
            db.session.commit()

        with_retries(tx)
    except IntegrityError as e:
        if isinstance(e.orig, psycopg2.errors.ForeignKeyViolation):
            return utils.server_error(FOREIGN_KEY_ERROR)
        else:
            return utils.server_error(str(e))

    return redirect(url_for("admin_judges"))


@app.route("/admin/judges/<judge_id>/send-email", methods=["POST"])
@utils.requires_auth
def email_judge(judge_id: str):
    try:
        email_invite_links(Annotator.by_id(judge_id))
    except Exception as e:
        return utils.server_error(str(e))

    return redirect(url_for("admin_judges"))


@app.route("/admin/judges/<judge_id>/update-status", methods=["POST"])
@utils.requires_auth
def update_judge_status(judge_id: str):
    new_state = request.form["value"] == "Enable"

    def tx():
        Annotator.by_id(judge_id).active = new_state
        db.session.commit()

    with_retries(tx)

    return redirect(url_for("admin_judges"))


def try_send_emails(added: List[Annotator]):
    try:
        email_invite_links(added)
    except Exception as e:
        return utils.server_error(str(e))


def email_invite_links(annotators: List[Annotator] | Annotator):
    if settings.DISABLE_EMAIL or annotators is None:
        return
    if not isinstance(annotators, list):
        annotators = [annotators]

    emails = []
    for annotator in annotators:
        link = judge_login_link(annotator)
        link = f'<a clicktracking=off href="{link}">{link}</a>'
        raw_body = settings.EMAIL_BODY.format(name=annotator.name, link=link)
        body = "\n\n".join(utils.get_paragraphs(raw_body))
        emails.append((annotator.email, settings.EMAIL_SUBJECT, body))

    print(emails)
    if settings.USE_SENDGRID and settings.SENDGRID_API_KEY is not None:
        utils.send_sendgrid_emails(emails)
    else:
        utils.send_emails.delay(emails)


def judge_login_link(judge: Annotator):
    return url_for("login", secret=judge.secret, _external=True)
