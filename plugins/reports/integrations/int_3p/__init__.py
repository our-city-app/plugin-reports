# -*- coding: utf-8 -*-
# Copyright 2019 Green Valley Belgium NV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# @@license_version:1.5@@

from datetime import datetime
import logging

from google.appengine.api import app_identity
from google.appengine.ext import deferred

import dicttoxml
from framework.utils import guid
from mcfw.consts import DEBUG
from plugins.reports.bizz.gcs import is_file_available, upload_to_gcs
from plugins.reports.bizz.rogerthat import send_rogerthat_message
from plugins.reports.consts import INCIDENTS_QUEUE
from plugins.reports.dal import get_incident, get_rogerthat_user
from plugins.rogerthat_api.to import MemberTO


def create_incident(settings, rt_user, incident, steps):
    xml_content = create_incident_xml(incident, rt_user, steps)
    if DEBUG:
        logging.warn(xml_content)
    # todo settings.gcs_bucket_name
    deferred.defer(create_incident_on_gcs, settings.gcs_bucket_name, incident.incident_id, xml_content, _queue=INCIDENTS_QUEUE)

    title = description = lat = lon = None
    return {}, title, description, lat, lon


def create_incident_xml(incident, rt_user, steps):
    attachments = []
    result_text = []
    incident_type = None
    description = []
    place = None

    requestor = dict(email=rt_user.email)
    latitude = None
    longitude = None
    for step in steps:
        if step.step_id == 'message_keuze':
            incident_type = step.button
            continue

        if step.step_type == "form_step":
            if step.answer_id == "positive":
                if step.step_id == 'message_description':
                    description.append(step.get_value())
                    continue

                if step.step_id == 'message_explanation':
                    result_text.append(step.get_value())
                    continue

                if step.form_type == "photo_upload":
                    attachments.append(step.get_value())
                    continue

                if step.step_id == 'message_location-text':
                    place = step.get_value()
                    continue

                if step.form_type == "gps_location":
                    latitude = step.get_value().latitude
                    longitude = step.get_value().longitude
                    continue

                if step.step_id == 'message_my-firstname':
                    requestor['firstname'] = step.get_value()
                    continue

                if step.step_id == 'message_my-lastname':
                    requestor['name'] = step.get_value()
                    continue

                if step.step_id == 'message_my-phone':
                    requestor['phone'] = step.get_value()
                    continue

                if step.step_id == 'message_my-address':
                    requestor['street'] = step.get_value()
                    continue

                step_value = step.display_value
            else:
                step_value = None
        else:
            if step.step_type == "message_step":
                step_value = step.button
                if step_value == None:
                    step_value = "Rogerthat"
            else:
                step_value = step.button

        if step_value:
            result_text.append(step.message)
            result_text.append(step_value)

    result_text.append(u'\nJe kan deze melding beantwoorden door een e-mail te sturen naar:\nincident.%s.followup@%s.appspotmail.com' % (incident.incident_id, app_identity.get_application_id()))

    comment = '\r\n'.join(result_text)
    workOrder = {
        u'dateasked': incident.report_time.isoformat(),
        u'description': '\n'.join(description) if description else u'Nieuwe melding',
        u'comment': comment,
        u'type': incident_type,
        u'urgencyType': u'melding',
        u'place': place,
        u'latitude': latitude,
        u'longitude': longitude,
        u'requestor': requestor,
        u'contactmethod': u'app',
        u'externId': incident.incident_id,
        u'attachments': attachments

    }
    xml = dicttoxml.dicttoxml(workOrder, custom_root='Workorder', attr_type=False)
    prettyxml = dicttoxml.parseString(xml).toprettyxml(encoding='utf8')
    return prettyxml.replace('<?xml version="1.0" encoding="utf8"?>', '<?xml version="1.0"?>')  # 3p can't process xml with encoding...


def create_incident_on_gcs(gcs_bucket_name, incident_id, xml_content, attempt=1):
    if not is_file_available(u'/%s/reports/__syncing' % gcs_bucket_name):
        upload_to_gcs(xml_content, u'text/xml', u'/%s/reports/%s.xml' % (gcs_bucket_name, incident_id))
        return

    deferred.defer(create_incident_on_gcs, gcs_bucket_name, incident_id, xml_content,
                   attempt=attempt + 1,
                   _queue=INCIDENTS_QUEUE,
                   _countdown=10 * attempt)


def incident_follow_up(from_, regex, subject, body):
    # todo security validate from
    incident_id = long(regex.groupdict()['incident_id'])
    incident = get_incident(incident_id)
    if not incident:
        logging.debug("Recieved incident update that is not in our database: '%s'" % (incident_id))
        return
    rt_user = get_rogerthat_user(incident.user_id)
    member = MemberTO(member=rt_user.email, app_id=rt_user.app_id, alert_flags=2)
    deferred.defer(send_rogerthat_message, incident.sik, member, body, json_rpc_id=guid())  # todo incident.parent_message_key
