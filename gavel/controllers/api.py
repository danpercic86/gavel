from gavel import app
from gavel.models import *
from gavel.constants import *
import gavel.settings as settings
import gavel.utils as utils
import json
from flask import ( Response, request)

@app.route('/api/items.csv')
@utils.requires_auth
def item_dump():
    items = Item.query.order_by(desc(Item.mu)).all()
    data = [['Mu', 'Sigma Squared', 'Name', 'Location', 'Description', 'Active']]
    data += [[
        str(item.mu),
        str(item.sigma_sq),
        item.name,
        item.location,
        item.description,
        item.active
    ] for item in items]
    return Response(utils.data_to_csv_string(data), mimetype='text/csv')

@app.route('/api/annotators.csv')
@utils.requires_auth
def annotator_dump():
    annotators = Annotator.query.all()
    data = [['Name', 'Email', 'Description', 'Secret']]
    data += [[
        str(a.name),
        a.email,
        a.description,
        a.secret
    ] for a in annotators]
    return Response(utils.data_to_csv_string(data), mimetype='text/csv')

@app.route('/api/decisions.csv')
@utils.requires_auth
def decisions_dump():
    decisions = Decision.query.all()
    data = [['Annotator ID', 'Winner ID', 'Loser ID', 'Time']]
    data += [[
        str(d.annotator.id),
        str(d.winner.id),
        str(d.loser.id),
        str(d.time)
    ] for d in decisions]
    return Response(utils.data_to_csv_string(data), mimetype='text/csv')

@app.route('/api/submissions.json')
def item_json_dump():

    if not request.args['key'] == settings.API_KEY:
        return Response(json.dumps({'error' : 'Invalid api key.'}), mimetype='application/json')

    items = Item.query.order_by(desc(Item.mu)).all()
    data = []
    data += [{
        'description'   : item.description.strip(),
        'id'            : item.id,
        'mu'            : str(item.mu).strip(),
        'sigma Squared' : str(item.sigma_sq).strip(),
        'location'      : item.location.strip(),
        'active'        : item.active,
        'name'          : item.name.strip(),
        'teamId'          : item.identifier.strip()
    } for item in items]
    return Response(json.dumps(data), mimetype='application/json')
