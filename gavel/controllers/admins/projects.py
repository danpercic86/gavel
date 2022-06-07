import io

import psycopg2.errors
import xlrd
from flask import (
    redirect,
    request,
    url_for,
    send_file,
)
from flask import (
    render_template,
)
from sqlalchemy.exc import IntegrityError

import gavel.stats as stats
import gavel.utils as utils
from gavel import app
from gavel.models import (
    Annotator,
    Item,
    Decision,
    db,
    with_retries,
    ignore_table,
)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
FOREIGN_KEY_ERROR = "Projects can't be deleted once they have been voted on by a judge. You can use the 'disable' functionality instead, which has a similar effect, preventing the project from being shown to judges."


@app.route("/admin/projects", methods=["GET"])
@utils.requires_auth
def admin_projects():
    stats.check_send_telemetry()
    annotators = Annotator.query.order_by(Annotator.id).all()
    items = Item.query.order_by(Item.id).all()

    decisions = Decision.query.all()
    item_counts = {}

    for d in decisions:
        winner_id = d.winner_id
        loser_id = d.loser_id
        item_counts[winner_id] = item_counts.get(winner_id, 0) + 1
        item_counts[loser_id] = item_counts.get(loser_id, 0) + 1

    viewed = {i.id: {a.id for a in i.viewed} for i in items}
    skipped = {}

    for jury_id in annotators:
        for i in jury_id.ignore:
            if jury_id.id not in viewed[i.id]:
                skipped[i.id] = skipped.get(i.id, 0) + 1

    return render_template(
        "admin/projects/index.html",
        is_admin=True,
        skipped=skipped,
        items=items,
        item_counts=item_counts,
    )


@app.route("/admin/projects/<project_id>/update", methods=["POST"])
@utils.requires_auth
def update_project(project_id: str):
    project = Item.by_id(project_id)
    if not project:
        return utils.user_error(f"Project {project_id} not found ")

    def tx():
        if "location" in request.form:
            project.location = request.form["location"]
        if "name" in request.form:
            project.name = request.form["name"]
        if "description" in request.form:
            project.description = request.form["description"]
        if "team_name" in request.form:
            project.team_name = request.form["team_name"]
        if "presentation_link" in request.form:
            project.presentation_link = request.form["presentation_link"]
        db.session.commit()

    with_retries(tx)

    return redirect(url_for("project_details", project_id=project.id))


@app.route("/admin/projects/<project_id>/", methods=["GET"])
@utils.requires_auth
def project_details(project_id: str):
    project = Item.by_id(project_id)

    if not project:
        return utils.user_error(f"Project {project_id} not found ")

    assigned = Annotator.query.filter(Annotator.next == project).all()
    viewed_ids = {i.id for i in project.viewed}

    if viewed_ids:
        skipped = Annotator.query.filter(
            Annotator.ignore.contains(project) & ~Annotator.id.in_(viewed_ids)
        )
    else:
        skipped = Annotator.query.filter(Annotator.ignore.contains(project))

    return render_template(
        "admin/projects/detail.html",
        is_admin=True,
        item=project,
        assigned=assigned,
        skipped=skipped,
    )


@app.route("/admin/projects", methods=["POST"])
@utils.requires_auth
def upload_project():
    data = parse_upload_form()

    if not data:
        return utils.user_error("No projects uploaded")

    for index, row in enumerate(data):
        if len(row) != 6:
            return utils.user_error(
                f"Bad data: row {index + 1:d} has {len(row):d} elements (expecting 6)"
            )

    def tx():
        for row in data:
            db.session.add(Item(*map(lambda x: x.strip(), row)))
        db.session.commit()

    with_retries(tx)

    return redirect(url_for("admin_projects"))


@app.route("/admin/projects/<project_id>/delete", methods=["POST"])
@utils.requires_auth
def delete_project(project_id: str):
    try:

        def tx():
            db.session.execute(
                ignore_table.delete(ignore_table.c.item_id == project_id)
            )
            Item.query.filter_by(id=project_id).delete()
            db.session.commit()

        with_retries(tx)
    except IntegrityError as e:
        if isinstance(e.orig, psycopg2.errors.ForeignKeyViolation):
            return utils.server_error(FOREIGN_KEY_ERROR)

        return utils.server_error(str(e))

    return redirect(url_for("admin_projects"))


@app.route("/admin/projects/<project_id>/update-status", methods=["POST"])
@utils.requires_auth
def update_project_status(project_id: str):
    new_state = request.form["value"] == "Enable"

    def tx():
        Item.by_id(project_id).active = new_state
        db.session.commit()

    with_retries(tx)

    return redirect(url_for("admin_projects"))


@app.route("/admin/projects/<project_id>/update-importance", methods=["POST"])
@utils.requires_auth
def update_project_importance(project_id: str):
    new_state = request.form["value"] == "Prioritize"

    def tx():
        Item.by_id(project_id).prioritized = new_state
        db.session.commit()

    with_retries(tx)

    return redirect(url_for("admin_projects"))


@app.route("/admin/projects/<project_id>/plot-decisions", methods=["GET"])
@utils.requires_auth
def plot_decisions_project(project_id: str):
    app.logger.info("yoloooo")
    import graphviz

    item = Item.by_id(project_id)
    decisions = Decision.query.filter(
        (Decision.winner_id == project_id) | (Decision.loser_id == project_id)
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


def parse_upload_form():
    f = request.files.get("file")
    data: list[list[str]] = []
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


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
