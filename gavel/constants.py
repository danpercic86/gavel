ANNOTATOR_ID = 'annotator_id'
TELEMETRY_URL = 'https://telemetry.anish.io/api/v1/submit'
TELEMETRY_DELTA = 20 * 60 # seconds
SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"

# Setting
# keys
SETTING_CLOSED = 'closed' # boolean
SETTING_TELEMETRY_LAST_SENT = 'telemetry_sent_time' # integer
# values
SETTING_TRUE = 'true'
SETTING_FALSE = 'false'

# Defaults
# these can be overridden via the config file
DEFAULT_WELCOME_MESSAGE = '''
Welcome to UniHack.

**Please read this important message carefully before continuing.**

Gavel is a fully automated judging system that both tells you where to go
and collects your votes.

The system is based on the model of <u>pairwise comparison</u>. You'll start off by
looking at a single project, and then for every project after that,
you'll decide whether it's better or worse than the one you looked at
**immediately beforehand.**

If at any point, you can't find a particular project, you can click the
'Skip' button and you will be assigned a new project. **Please don't skip
unless absolutely necessary.**

Gavel makes it really simple for you to submit votes, but please think hard
before you vote. **Once you make a decision, you can't take it back.**
'''.strip()

DEFAULT_EMAIL_SUBJECT = 'Welcome to the UniHack judging system!'

DEFAULT_EMAIL_BODY = '''
Hi {name},

Welcome to Gavel, the online expo judging system. This email contains your
magic link to the judging system.

DO NOT SHARE this email with others, as it contains your personal magic link.

To access the system, visit {link}.

Once you're in, please take the time to read the welcome message and
instructions before continuing.
'''.strip()

DEFAULT_CLOSED_MESSAGE = '''
The judging system is currently closed. Judging starts at 12:00 and ends at 13:30.
'''.strip()

DEFAULT_DISABLED_MESSAGE = '''
Your account is currently disabled. Reload the page to try again.
'''.strip()

DEFAULT_LOGGED_OUT_MESSAGE = '''
You are currently logged out. Open your magic link to get started.
'''.strip()

DEFAULT_WAIT_MESSAGE = '''
Wait for a little bit and reload the page to try again.

If you've looked at all the projects already, then you're done.
'''.strip()

DEFAULT_API_KEY = '89iuw4gtuyjfbsiukbkwhejbhu4b5'

IMPORT_URL = 'https://dev.unihack.eu/api/Export/GavelProjects'
