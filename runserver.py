# Copyright (c) 2015-2021 Anish Athalye (me@anishathalye.com)
#
# This software is released under AGPLv3. See the included LICENSE.txt for
# details.

if __name__ == "__main__":
    from gavel import app
    import os

    extra_files = []
    if os.environ.get("DEBUG", True):
        app.debug = True
        extra_files.append("./config.yaml")
        app.jinja_env.auto_reload = True
        app.config["TEMPLATES_AUTO_RELOAD"] = True

    app.run(host="0.0.0.0", port=os.environ.get("PORT", 5005), extra_files=extra_files)
