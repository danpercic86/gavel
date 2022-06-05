# Copyright (c) 2015-2021 Anish Athalye (me@anishathalye.com)
#
# This software is released under AGPLv3. See the included LICENSE.txt for
# details.

from gavel import app, settings

# extra_files = []
if settings.DEBUG:
    app.debug = True
    # extra_files.append("./config.yaml")
    app.jinja_env.auto_reload = True
    app.config["TEMPLATES_AUTO_RELOAD"] = True

# app.run(host="0.0.0.0", port=settings.PORT, extra_files=extra_files)
