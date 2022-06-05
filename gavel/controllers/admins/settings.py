import json

import requests
from django.utils.html import strip_tags
from flask import (
    redirect,
    request,
    url_for,
)
from flask import (
    render_template,
)

import gavel.utils as utils
from gavel import app, stats, settings
from gavel.constants import SETTING_CLOSED, SETTING_TRUE, SETTING_FALSE
from gavel.models import (
    Annotator,
    Item,
    Decision,
    Setting,
    db,
)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


@app.route("/admin/settings")
@utils.requires_auth
def admin_settings():
    stats.check_send_telemetry()
    setting_closed = Setting.value_of(SETTING_CLOSED) == SETTING_TRUE

    return render_template(
        "admin/settings.html",
        is_admin=True,
        setting_closed=setting_closed,
        time_per_project=Setting.value_of("TIME_PER_PROJECT"),
        max_time_per_project=Setting.value_of("MAX_TIME_PER_PROJECT"),
        jury_end=Setting.value_of("JURY_END_DATETIME"),
    )


@app.route("/admin/settings/delete-skips/", methods=["POST"])
@utils.requires_auth
def delete_skips():
    db.session.execute("DELETE FROM ignore")
    return _save_and_go_to_dashboard()


@app.route("/admin/settings/import-teams/", methods=["POST"])
@utils.requires_auth
def import_teams():
    import_projects()
    db.session.commit()
    return redirect(url_for("admin_projects"))


@app.route("/admin/settings/wipe-data/", methods=["POST"])
@utils.requires_auth
def wipe_data():
    Decision.query.delete()
    db.session.execute("DELETE FROM ignore")
    db.session.execute("DELETE FROM view")
    db.session.commit()
    Annotator.query.delete()
    db.session.commit()
    Item.query.delete()
    return _save_and_go_to_dashboard()


@app.route("/admin/settings/update/", methods=["POST"])
@utils.requires_auth
def update_setting():
    return _update_setting(request.form["identifier"], request.form["value"])


def _update_setting(identifier: str, value: str):
    Setting.set(identifier, value)
    return _save_and_go_to_dashboard()


@app.route("/admin/settings/update-status/", methods=["POST"])
@utils.requires_auth
def update_status():
    raw_value = request.form["value"]
    value = SETTING_TRUE if raw_value == "Close" else SETTING_FALSE
    return _update_setting(SETTING_CLOSED, value)


def _save_and_go_to_dashboard():
    db.session.commit()

    return redirect(url_for("admin_dashboard"))


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
