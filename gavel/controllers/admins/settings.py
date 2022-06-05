from flask import (
    render_template,
)

import gavel.stats as stats
import gavel.utils as utils
from gavel import app
from gavel.constants import SETTING_CLOSED, SETTING_TRUE
from gavel.models import (
    Setting,
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
