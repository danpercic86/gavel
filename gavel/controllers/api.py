import json

from flask import Response, request
from sqlalchemy import desc

import gavel.utils as utils
from gavel import app, settings
from gavel.controllers.admin import import_projects
from gavel.controllers.admins.judges import judge_login_link
from gavel.models import Item, Annotator, Decision, db


@app.route("/api/items.csv")
@app.route("/api/projects.csv")
@utils.requires_auth
def item_dump():
    items = Item.query.order_by(desc(Item.mu)).all()
    data = [["Mu", "Sigma Squared", "Name", "Location", "Description", "Active"]]
    data += [
        [
            str(item.mu),
            str(item.sigma_sq),
            item.name,
            item.location,
            item.description,
            item.active,
        ]
        for item in items
    ]
    return Response(utils.data_to_csv_string(data), mimetype="text/csv")


@app.route("/api/annotators.csv")
@app.route("/api/judges.csv")
@utils.requires_auth
def annotator_dump():
    annotators = Annotator.query.all()
    data = [["Name", "Email", "Description", "Secret"]]
    data += [[str(a.name), a.email, a.description, a.secret] for a in annotators]
    return Response(utils.data_to_csv_string(data), mimetype="text/csv")


@app.route("/api/decisions.csv")
@utils.requires_auth
def decisions_dump():
    decisions = Decision.query.all()
    data = [["Annotator ID", "Winner ID", "Loser ID", "Time"]]
    data += [
        [str(d.annotator.id), str(d.winner.id), str(d.loser.id), str(d.time)]
        for d in decisions
    ]
    return Response(utils.data_to_csv_string(data), mimetype="text/csv")


@app.route("/api/submissions.json")
@utils.requires_auth
def item_json_dump():
    if not request.args["key"] == settings.API_KEY:
        return Response(
            json.dumps({"error": "Invalid api key."}), mimetype="application/json"
        )

    items = Item.query.order_by(desc(Item.mu)).all()
    data = []
    data += [
        {
            "description": item.description.strip(),
            "id": item.id,
            "mu": str(item.mu).strip(),
            "sigma Squared": str(item.sigma_sq).strip(),
            "location": item.location.strip(),
            "active": item.active,
            "name": item.name.strip(),
            "teamId": item.identifier.strip(),
        }
        for item in items
    ]
    return Response(json.dumps(data), mimetype="application/json")


@app.route("/api/import-projects", methods=["POST"])
@utils.requires_auth
def trigger_import_projects():
    import_projects()
    return Response(status=204)


@app.route("/api/register-judge", methods=["POST"])
@utils.requires_auth
def register_judge():
    name = request.form["name"]
    email = request.form["email"]
    description = request.form.get("description", None) or ""

    if Annotator.query.filter(Annotator.email == email).first():
        return Response(f"judge {email} already exists", status=409)

    judge = Annotator(name, email, description)
    db.session.add(judge)
    db.session.commit()

    response = {"loginUrl": judge_login_link(judge)}
    return Response(json.dumps(response), mimetype="application/json")
