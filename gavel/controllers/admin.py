import requests
from sqlalchemy.dialects.mssql import IMAGE
from django.utils.html import strip_tags
from gavel import app
from gavel.models import *
from gavel.constants import *
import gavel.settings as settings
import gavel.utils as utils
from flask import (
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import urllib.parse
import xlrd
import urllib.request
import json

ALLOWED_EXTENSIONS = set(['csv', 'xlsx', 'xls'])

@app.route('/admin/')
@utils.requires_auth
def admin():
    annotators = Annotator.query.order_by(Annotator.id).all()
    items = Item.query.order_by(Item.id).all()
    decisions = Decision.query.all()
    counts = {}
    item_counts = {}
    for d in decisions:
        a = d.annotator_id
        w = d.winner_id
        l = d.loser_id
        counts[a] = counts.get(a, 0) + 1
        item_counts[w] = item_counts.get(w, 0) + 1
        item_counts[l] = item_counts.get(l, 0) + 1
    viewed = {i.id: {a.id for a in i.viewed} for i in items}
    skipped = {}
    for a in annotators:
        for i in a.ignore:
            if a.id not in viewed[i.id]:
                skipped[i.id] = skipped.get(i.id, 0) + 1
    # settings
    setting_closed = Setting.value_of(SETTING_CLOSED) == SETTING_TRUE
    return render_template(
        'admin.html',
        is_admin=True,
        annotators=annotators,
        counts=counts,
        item_counts=item_counts,
        skipped=skipped,
        items=items,
        votes=len(decisions),
        setting_closed=setting_closed,
        time_per_project=Setting.value_of('TIME_PER_PROJECT'),
        max_time_per_project=Setting.value_of('MAX_TIME_PER_PROJECT'),
        jury_end=Setting.value_of('JURY_END_DATETIME')
    )

@app.route('/admin/item', methods=['POST'])
@utils.requires_auth
def item():
    action = request.form['action']
    if action == 'Submit':
        data = parse_upload_form()
        if data:
            # validate data
            for index, row in enumerate(data):
                if len(row) != 3:
                    return utils.user_error('Bad data: row %d has %d elements (expecting 3)' % (index + 1, len(row)))
            for row in data:
                _item = Item(*row)
                db.session.add(_item)
            db.session.commit()
    elif action == 'Prioritize' or action == 'Cancel':
        item_id = request.form['item_id']
        target_state = action == 'Prioritize'
        Item.by_id(item_id).prioritized = target_state
        db.session.commit()
    elif action == 'Disable' or action == 'Enable':
        item_id = request.form['item_id']
        target_state = action == 'Enable'
        Item.by_id(item_id).active = target_state
        db.session.commit()
    elif action == 'Delete':
        item_id = request.form['item_id']
        try:
            db.session.execute(ignore_table.delete(ignore_table.c.item_id == item_id))
            Item.query.filter_by(id=item_id).delete()
            db.session.commit()
        except IntegrityError as e:
            return utils.server_error(str(e))
    return redirect(url_for('admin'))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_upload_form():
    f = request.files.get('file')
    data = []
    if f and allowed_file(f.filename):
        extension = str(f.filename.rsplit('.', 1)[1].lower())
        if extension == "xlsx" or extension == "xls":
            workbook = xlrd.open_workbook(file_contents=f.read())
            worksheet = workbook.sheet_by_index(0)
            data = list(utils.cast_row(worksheet.row_values(rx, 0, 3)) for rx in range(worksheet.nrows) if worksheet.row_len(rx) == 3)
        elif extension == "csv":
            data = utils.data_from_csv_string(f.read().decode("utf-8"))
    else:
        csv = request.form['data']
        data = utils.data_from_csv_string(csv)
    return data


@app.route('/admin/item_patch', methods=['POST'])
@utils.requires_auth
def item_patch():
    item = Item.by_id(request.form['item_id'])
    if not item:
        return utils.user_error('Item %s not found ' % request.form['item_id'])
    if 'location' in request.form:
        item.location = request.form['location']
    if 'name' in request.form:
        item.name = request.form['name']
    if 'description' in request.form:
        item.description = request.form['description']
    db.session.commit()
    return redirect(url_for('item_detail', item_id=item.id))

@app.route('/admin/annotator', methods=['POST'])
@utils.requires_auth
def annotator():
    action = request.form['action']
    if action == 'Submit':
        data = parse_upload_form()
        added = []
        if data:
            # validate data
            for index, row in enumerate(data):
                if len(row) != 3:
                    return utils.user_error('Bad data: row %d has %d elements (expecting 3)' % (index + 1, len(row)))
            for row in data:
                annotator = Annotator(*row)
                added.append(annotator)
                db.session.add(annotator)
            db.session.commit()
            try:
                email_invite_links(added)
            except Exception as e:
                return utils.server_error(str(e))
    elif action == 'Email':
        annotator_id = request.form['annotator_id']
        try:
            email_invite_links(Annotator.by_id(annotator_id))
        except Exception as e:
            return utils.server_error(str(e))
    elif action == 'Disable' or action == 'Enable':
        annotator_id = request.form['annotator_id']
        target_state = action == 'Enable'
        Annotator.by_id(annotator_id).active = target_state
        db.session.commit()
    elif action == 'Delete':
        annotator_id = request.form['annotator_id']
        try:
            db.session.execute(ignore_table.delete(ignore_table.c.annotator_id == annotator_id))
            Annotator.query.filter_by(id=annotator_id).delete()
            db.session.commit()
        except IntegrityError as e:
            return utils.server_error(str(e))
    return redirect(url_for('admin'))

@app.route('/admin/setting', methods=['POST'])
@utils.requires_auth
def setting():
    action = request.form['action']
    if action == 'update-time-per-project':
        Setting.set('TIME_PER_PROJECT', request.form['time-per-project'])
        db.session.commit()
    if action == 'update-max-time-per-project':
        Setting.set('MAX_TIME_PER_PROJECT', request.form['max-time-per-project'])
        db.session.commit()
    if action == 'update-jury-end':
        Setting.set('JURY_END_DATETIME', request.form['jury-end-datetime'])
        db.session.commit()
    if action == 'update-voting-status':
        new_value = SETTING_TRUE if request.form['voting-status'] == 'Close' else SETTING_FALSE
        Setting.set(SETTING_CLOSED, new_value)
        db.session.commit()
    if action == 'delete-skips':
        db.session.execute("DELETE FROM ignore")
        db.session.commit()
    if action == 'wipe-data':
        Decision.query.delete()
        db.session.execute("DELETE FROM ignore")
        db.session.execute("DELETE FROM view")
        db.session.commit()
        Annotator.query.delete()
        db.session.commit()
        Item.query.delete()
        db.session.commit()
    if action == 'import-teams':
        response = requests.get(IMPORT_URL)
        data = json.loads(response.content.decode('utf-8'))

        for item in data:
            print('identifier' + item['_id'])
            exitingItem = Item.by_identifier(item['_id'])
            if exitingItem is None:
                if 'name' in item and 'location' in item:
                    description = '...'
                    if 'description' in item and item['description'] is not None:
                        description = strip_tags(item['description'])
                    _item = Item(strip_tags(item['name']), strip_tags(item['location']), description, item['_id'])
                    print('created')
                    print(_item)
                    db.session.add(_item)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/item/<item_id>/')
@utils.requires_auth
def item_detail(item_id):
    item = Item.by_id(item_id)
    if not item:
        return utils.user_error('Item %s not found ' % item_id)
    else:
        assigned = Annotator.query.filter(Annotator.next == item).all()
        viewed_ids = {i.id for i in item.viewed}
        if viewed_ids:
            skipped = Annotator.query.filter(
                Annotator.ignore.contains(item) & ~Annotator.id.in_(viewed_ids)
            )
        else:
            skipped = Annotator.query.filter(Annotator.ignore.contains(item))
        return render_template(
            'admin_item.html',
            is_admin=True,
            item=item,
            assigned=assigned,
            skipped=skipped
        )

@app.route('/admin/annotator/<annotator_id>/')
@utils.requires_auth
def annotator_detail(annotator_id):
    annotator = Annotator.by_id(annotator_id)
    if not annotator:
        return utils.user_error('Annotator %s not found ' % annotator_id)
    else:
        seen = Item.query.filter(Item.viewed.contains(annotator)).all()
        ignored_ids = {i.id for i in annotator.ignore}
        if ignored_ids:
            skipped = Item.query.filter(
                Item.id.in_(ignored_ids) & ~Item.viewed.contains(annotator)
            )
        else:
            skipped = []
        return render_template(
            'admin_annotator.html',
            annotator=annotator,
            is_admin=True,
            login_link=annotator_link(annotator),
            seen=seen,
            skipped=skipped
        )

def annotator_link(annotator):
        return urllib.parse.urljoin(settings.BASE_URL, url_for('login', secret=annotator.secret))

def email_invite_links(annotators):
    if settings.DISABLE_EMAIL or annotators is None:
        return
    if not isinstance(annotators, list):
        annotators = [annotators]

    emails = []
    for annotator in annotators:
        link = annotator_link(annotator)
        raw_body = settings.EMAIL_BODY.format(name=annotator.name, link=link)
        body = '\n\n'.join(utils.get_paragraphs(raw_body))
        emails.append((annotator.email, settings.EMAIL_SUBJECT, body))

    utils.send_emails.delay(emails)
