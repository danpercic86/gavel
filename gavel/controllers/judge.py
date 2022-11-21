import io

from flask import (
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_file,
)
from numpy.random import choice

import gavel.settings as settings
import gavel.utils as utils
from gavel import app
from gavel.constants import SETTING_CLOSED, SETTING_TRUE, ANNOTATOR_ID
from gavel.controllers.judges.common import (
    get_current_judge,
    preferred_items,
    choose_next,
    requires_open,
    requires_active_annotator,
    requires,
    check_has_decisions,
)
from gavel.models import Setting, Item, db, Annotator
from gavel.models.common import with_retries


@app.route("/")
def index():
    annotator = get_current_judge()

    if annotator is None:
        return render_template(
            "logged_out.html",
            content=utils.render_markdown(settings.LOGGED_OUT_MESSAGE),
        )

    items = Item.query.order_by(Item.id).all()
    seen = Item.query.filter(Item.viewed.contains(annotator)).all()
    if Setting.value_of(SETTING_CLOSED) == SETTING_TRUE:
        return render_template(
            "judge/closed.html", content=utils.render_markdown(settings.CLOSED_MESSAGE)
        )

    if not annotator.active:
        return render_template(
            "judge/disabled.html",
            content=utils.render_markdown(settings.DISABLED_MESSAGE),
        )

    if not annotator.read_welcome:
        return redirect(url_for("welcome"))

    maybe_init_annotator()

    if annotator.next is None:
        return render_template(
            "judge/wait.html", content=utils.render_markdown(settings.WAIT_MESSAGE)
        )

    time_per_project = Setting.value_of("TIME_PER_PROJECT")
    max_time_per_project = Setting.value_of("MAX_TIME_PER_PROJECT")
    jury_end = Setting.value_of("JURY_END_DATETIME")

    if annotator.prev is None:
        return render_template(
            "judge/begin.html",
            item=annotator.next,
            items=items,
            seen=seen,
            time_per_project=time_per_project,
            max_time_per_project=max_time_per_project,
            jury_end=jury_end,
        )

    return render_template(
        "judge/vote.html",
        prev=annotator.prev,
        next=annotator.next,
        items=items,
        seen=seen,
        time_per_project=time_per_project,
        max_time_per_project=max_time_per_project,
        jury_end_datetime=jury_end,
    )


@app.route("/begin", methods=["POST"])
@requires_open(redirect_to="index")
@requires_active_annotator(redirect_to="index")
def begin():
    def tx():
        annotator = get_current_judge()
        if annotator.next.id == int(request.form["item_id"]):
            annotator.ignore.append(annotator.next)
            if request.form["action"] == "Continue":
                annotator.next.viewed.append(annotator)
                annotator.prev = annotator.next
                annotator.update_next(choose_next(annotator))
            elif request.form["action"] == "Skip":
                annotator.next = None  # will be reset in index
            db.session.commit()

    with_retries(tx)
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop(ANNOTATOR_ID, None)
    return redirect(url_for("index"))


@app.route("/login/<secret>/")
def login(secret):
    annotator = Annotator.by_secret(secret)
    if annotator is None:
        session.pop(ANNOTATOR_ID, None)
        session.modified = True
    else:
        session[ANNOTATOR_ID] = annotator.id
    return redirect(url_for("index"))


@app.route("/welcome/")
@requires_open(redirect_to="index")
@requires_active_annotator(redirect_to="index")
def welcome():
    return render_template(
        "judge/welcome.html", content=utils.render_markdown(settings.WELCOME_MESSAGE)
    )


@app.route("/map/")
@requires_open(redirect_to="index")
@requires_active_annotator(redirect_to="index")
def map():
    return render_template("map.html")


@app.route("/decisions/")
@requires(check_has_decisions, redirect_to="index")
def plot_decisions():
    import graphviz

    judge = get_current_judge()
    projects = dict()
    edges = []

    def node_name(it: Item):
        return f"P{it.id}"

    def add_project(it: Item):
        projects[node_name(it)] = f"{it.name} -- {it.team_name}"

    def add_edge(winner: Item, loser: Item):
        edges.append((node_name(winner), node_name(loser)))

    for dec in judge.decisions:
        add_project(dec.winner)
        add_project(dec.loser)
        add_edge(dec.winner, dec.loser)

    title = f"HackTM votes from judge {judge.name}"
    dot = graphviz.Digraph(
        comment=title, graph_attr={"label": f"{title}, A -> B means A is better than B"}
    )
    for proj, team in projects.items():
        dot.node(proj, team)

    for edge in edges:
        dot.edge(*edge)

    graph = graphviz.pipe("dot", "png", dot.source.encode())
    return send_file(io.BytesIO(graph), mimetype="image/png")


@app.route("/welcome/done", methods=["POST"])
@requires_open(redirect_to="index")
@requires_active_annotator(redirect_to="index")
def welcome_done():
    def tx():
        annotator = get_current_judge()
        if request.form["action"] == "Continue":
            annotator.read_welcome = True
        db.session.commit()

    with_retries(tx)
    return redirect(url_for("index"))


def maybe_init_annotator():
    def tx():
        annotator = get_current_judge()
        if annotator.next is None:
            items = preferred_items(annotator)
            if items:
                annotator.update_next(choice(items))
                db.session.commit()

    with_retries(tx)
