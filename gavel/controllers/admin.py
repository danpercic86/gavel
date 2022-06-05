import io
import json
from typing import List

import psycopg2.errors
import requests
import xlrd
from django.utils.html import strip_tags
from flask import (
    redirect,
    render_template,
    request,
    url_for,
    send_file,
)
from sqlalchemy.exc import IntegrityError

import gavel.settings as settings
import gavel.utils as utils
from gavel import app
from gavel.constants import SETTING_CLOSED, SETTING_TRUE, SETTING_FALSE
from gavel.models import (
    Annotator,
    Item,
    Decision,
    Setting,
    db,
    with_retries,
    ignore_table,
)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


@app.route("/admin/item", methods=["POST"])
@utils.requires_auth
def item_actions():
    action = request.form["action"]

    if action == "Submit":
        data = parse_upload_form()
        if data:
            # validate data
            for index, row in enumerate(data):
                if len(row) != 6:
                    return utils.user_error(
                        "Bad data: row %d has %d elements (expecting 6)"
                        % (index + 1, len(row))
                    )

            def tx():
                for row in data:
                    _item = Item(*row)
                    db.session.add(_item)
                db.session.commit()

            with_retries(tx)
    elif action == "Prioritize" or action == "Cancel":
        item_id = request.form["item_id"]
        target_state = action == "Prioritize"

        def tx():
            Item.by_id(item_id).prioritized = target_state
            db.session.commit()

        with_retries(tx)
    elif action == "Disable" or action == "Enable":
        item_id = request.form["item_id"]
        target_state = action == "Enable"

        def tx():
            Item.by_id(item_id).active = target_state
            db.session.commit()

        with_retries(tx)
    elif action == "Delete":
        item_id = request.form["item_id"]
        try:

            def tx():
                db.session.execute(
                    ignore_table.delete(ignore_table.c.item_id == item_id)
                )
                Item.query.filter_by(id=item_id).delete()
                db.session.commit()

            with_retries(tx)
        except IntegrityError as e:
            if isinstance(e.orig, psycopg2.errors.ForeignKeyViolation):
                return utils.server_error(
                    "Projects can't be deleted once they have been voted on by a judge. You can use the 'disable' functionality instead, which has a similar effect, preventing the project from being shown to judges."
                )

            return utils.server_error(str(e))
    return redirect(url_for("admin"))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_upload_form():
    f = request.files.get("file")
    data = []
    if f and allowed_file(f.filename):
        extension = str(f.filename.rsplit(".", 1)[1].lower())
        if extension == "xlsx" or extension == "xls":
            workbook = xlrd.open_workbook(file_contents=f.read())
            worksheet = workbook.sheet_by_index(0)
            data = list(
                utils.cast_row(worksheet.row_values(rx, 0, 3))
                for rx in range(worksheet.nrows)
                if worksheet.row_len(rx) == 3
            )
        elif extension == "csv":
            data = utils.data_from_csv_string(f.read().decode("utf-8"))
    else:
        csv = request.form["data"]
        data = utils.data_from_csv_string(csv)
    return data


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


def import_projects():
    response = requests.get(settings.IMPORT_URL)
    data = json.loads(response.content.decode("utf-8"))
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    for item in data:
        if "_id" not in item:
            print("no id...", item)
            continue
        if "teamName" not in item:
            print("no team name...", item)
            continue

        name = strip_tags(item.get("name", None) or "")
        location = strip_tags(item.get("location", None) or "")

        if not name or not location:
            print("Project has no name...", item)
            continue

        description = strip_tags(item.get("description", None) or "") or "..."
        team_name = strip_tags(item.get("teamName", None) or "") or "..."
        presentation_link = (
            strip_tags(item.get("presentationLink", None) or "") or "..."
        )

        existing = Item.by_identifier(item["_id"])
        if existing is None:
            _item = Item(
                name, location, description, item["_id"], team_name, presentation_link
            )
            print("insert", item["_id"])
            db.session.add(_item)
        else:
            existing.name = name
            existing.location = location
            existing.description = description
            existing.team_name = team_name
            existing.presentation_link = presentation_link
            print("update", item["_id"])

    db.session.commit()


@app.route("/admin/setting", methods=["POST"])
@utils.requires_auth
def setting():
    action = request.form["action"]
    if action == "update-time-per-project":
        Setting.set("TIME_PER_PROJECT", request.form["time-per-project"])
        db.session.commit()
    if action == "update-max-time-per-project":
        Setting.set("MAX_TIME_PER_PROJECT", request.form["max-time-per-project"])
        db.session.commit()
    if action == "update-jury-end":
        Setting.set("JURY_END_DATETIME", request.form["jury-end-datetime"])
        db.session.commit()
    if action == "update-voting-status":
        new_value = (
            SETTING_TRUE if request.form["voting-status"] == "Close" else SETTING_FALSE
        )
        Setting.set(SETTING_CLOSED, new_value)
        db.session.commit()
    if action == "delete-skips":
        db.session.execute("DELETE FROM ignore")
        db.session.commit()
    if action == "wipe-data":
        Decision.query.delete()
        db.session.execute("DELETE FROM ignore")
        db.session.execute("DELETE FROM view")
        db.session.commit()
        Annotator.query.delete()
        db.session.commit()
        Item.query.delete()
        db.session.commit()
    if action == "import-teams":
        import_projects()

    return redirect(url_for("admin"))


@app.route("/admin/annotator/<annotator_id>/")
@utils.requires_auth
def annotator_detail(annotator_id):
    annotator = Annotator.by_id(annotator_id)
    if not annotator:
        return utils.user_error("Annotator %s not found " % annotator_id)
    else:
        seen = Item.query.filter(Item.viewed.contains(annotator)).all()
        ignored_ids = {i.id for i in annotator.ignore}
        if ignored_ids:
            skipped = Item.query.filter(
                Item.id.in_(ignored_ids) & ~Item.viewed.contains(annotator)
            )
        else:
            skipped = []
        return render_template(
            "admin_annotator.html",
            annotator=annotator,
            is_admin=True,
            login_link=annotator_link(annotator),
            seen=seen,
            skipped=skipped,
        )


@app.route("/admin/project-decisions/<item_id>/")
@utils.requires_auth
def plot_decisions_project(item_id):
    app.logger.info("yoloooo")
    import graphviz

    item = Item.by_id(item_id)
    decisions = Decision.query.filter(
        (Decision.winner_id == item_id) | (Decision.loser_id == item_id)
    )
    projects = dict()
    edges = []

    def node_name(it: Item):
        return f"P{it.id}"

    def add_project(it: Item):
        projects[node_name(it)] = f'"{it.name}" by {it.team_name}'

    def add_edge(winner: Item, loser: Item):
        edges.append((node_name(winner), node_name(loser)))

    for dec in decisions:
        add_project(dec.winner)
        add_project(dec.loser)
        add_edge(dec.winner, dec.loser)

    title = f"HackTM votes for project {item.name}"
    dot = graphviz.Digraph(
        comment=title, graph_attr={"label": f"{title}, A -> B means A is better than B"}
    )
    for proj, team in projects.items():
        if proj == node_name(item):
            node_kwargs = {"fillcolor": "red", "color": "red", "style": "filled"}
        else:
            node_kwargs = {}
        dot.node(proj, team, **node_kwargs)

    for edge in edges:
        dot.edge(*edge)

    graph = graphviz.pipe("dot", "png", dot.source.encode())
    return send_file(io.BytesIO(graph), mimetype="image/png")


def annotator_link(annotator):
    return url_for("login", secret=annotator.secret, _external=True)


def email_invite_links(annotators: List[Annotator] | Annotator):
    if settings.DISABLE_EMAIL or annotators is None:
        return
    if not isinstance(annotators, list):
        annotators = [annotators]

    emails = []
    for annotator in annotators:
        link = annotator_link(annotator)
        raw_body = settings.EMAIL_BODY.format(name=annotator.name, link=link)
        body = "\n\n".join(utils.get_paragraphs(raw_body))
        emails.append((annotator.email, settings.EMAIL_SUBJECT, body))

    if settings.USE_SENDGRID and settings.SENDGRID_API_KEY is not None:
        utils.send_sendgrid_emails(emails)
    else:
        utils.send_emails.delay(emails)
