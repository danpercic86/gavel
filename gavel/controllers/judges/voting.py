from flask import request, redirect, url_for

from gavel import app, crowd_bt, db, utils
from gavel.controllers.judges.common import (
    choose_next,
    get_current_judge,
    requires_open,
    requires_active_annotator,
)
from gavel.models import Decision, Annotator
from gavel.models.common import with_retries


def is_first_or_last_project(judge: Annotator):
    prev_id = int(request.form["prev_id"])
    next_id = int(request.form["next_id"])

    return judge.prev.id != prev_id or judge.next.id != next_id


@app.route("/vote", methods=["POST"])
@requires_open(redirect_to="index")
@requires_active_annotator(redirect_to="index")
def vote():
    def tx():
        judge = get_current_judge()

        if request.form["action"] == "Skip":
            return ignore_next_project(judge)

        if is_first_or_last_project(judge):
            return redirect(url_for("index"))

        # ignore things that were deactivated in the middle of judging
        if projects_are_still_active(judge):
            if request.form["action"] == "Previous":
                decision = vote_previous(judge)
            elif request.form["action"] == "Current":
                decision = vote_current(judge)
            else:
                return utils.user_error("Invalid action")
            db.session.add(decision)

        judge.next.viewed.append(judge)  # counted as viewed even if deactivated
        judge.prev = judge.next
        judge.ignore.append(judge.prev)
        judge.update_next(choose_next(judge))
        db.session.commit()

    with_retries(tx)

    return redirect(url_for("index"))


def projects_are_still_active(judge):
    return judge.prev.active and judge.next.active


def vote_previous(judge: Annotator):
    perform_vote(judge, next_won=False)
    return Decision(judge, winner=judge.prev, loser=judge.next)


def vote_current(judge: Annotator):
    perform_vote(judge, next_won=True)
    return Decision(judge, winner=judge.next, loser=judge.prev)


def ignore_next_project(judge: Annotator):
    judge.ignore.append(judge.next)
    return save_and_go_next(judge)


def save_and_go_next(judge: Annotator):
    judge.update_next(choose_next(judge))
    db.session.commit()

    return redirect(url_for("index"))


def perform_vote(annotator, next_won):
    if next_won:
        winner = annotator.next
        loser = annotator.prev
    else:
        winner = annotator.prev
        loser = annotator.next
    (
        u_alpha,
        u_beta,
        u_winner_mu,
        u_winner_sigma_sq,
        u_loser_mu,
        u_loser_sigma_sq,
    ) = crowd_bt.update(
        annotator.alpha,
        annotator.beta,
        winner.mu,
        winner.sigma_sq,
        loser.mu,
        loser.sigma_sq,
    )
    annotator.alpha = u_alpha
    annotator.beta = u_beta
    winner.mu = u_winner_mu
    winner.sigma_sq = u_winner_sigma_sq
    loser.mu = u_loser_mu
    loser.sigma_sq = u_loser_sigma_sq
