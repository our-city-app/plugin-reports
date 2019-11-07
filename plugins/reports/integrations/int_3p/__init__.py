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

import logging

import dicttoxml
from google.appengine.api import app_identity
from google.appengine.ext import deferred, ndb
from mcfw.consts import DEBUG
from typing import Tuple

from framework.utils import guid, try_or_defer
from plugins.reports.bizz.elasticsearch import re_index_incident
from plugins.reports.bizz.gcs import is_file_available, upload_to_gcs
from plugins.reports.bizz.rogerthat import send_rogerthat_message
from plugins.reports.consts import INCIDENTS_QUEUE
from plugins.reports.dal import get_incident, get_rogerthat_user
from plugins.reports.models import RogerthatUser, Incident, IncidentDetails, ThreePSettings, IntegrationSettings, \
    IncidentStatus, IncidentParamsFlow
from plugins.rogerthat_api.to import MemberTO
from plugins.rogerthat_api.to.messaging.flow import FormFlowStepTO, MessageFlowStepTO


def create_incident(settings, rt_user, incident, steps):
    # type: (IntegrationSettings, RogerthatUser, Incident, list) -> None
    xml_content, details, user_consent = create_incident_xml(incident, rt_user, steps)
    if DEBUG:
        logging.debug('3P incident XML: %s', xml_content)
    incident.details = details
    incident.user_consent = user_consent
    config = settings.data  # type: ThreePSettings
    deferred.defer(create_incident_on_gcs, config.gcs_bucket_name, incident.id, xml_content,
                   _queue=INCIDENTS_QUEUE)


def create_incident_xml(incident, rt_user, steps):
    # type: (Incident, RogerthatUser, list) -> Tuple[str, IncidentDetails, bool]
    attachments = []
    result_text = []
    incident_type = None
    description = []
    place = None

    requestor = {'email': rt_user.email}
    latitude = None
    longitude = None
    user_consent = False
    for step in steps:
        if step.step_id == 'message_keuze':
            incident_type = step.button
            continue

        if isinstance(step, FormFlowStepTO):
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
        elif isinstance(step, MessageFlowStepTO):
            if step.step_id == 'message_consent':
                if step.answer_id == 'button_yes':
                    user_consent = True
                continue
            step_value = step.button
            if step_value is None:
                step_value = 'Ok'
            else:
                step_value = step.button
        else:
            step_value = None

        if step_value:
            result_text.append(step.message)
            result_text.append(step_value)

    result_text.append(u'\nJe kan deze melding beantwoorden door een e-mail te sturen naar:'
                       u'\nincident.%s.followup@%s.appspotmail.com' % (incident.id,
                                                                       app_identity.get_application_id()))

    comment = '\r\n'.join(result_text)
    work_order = {
        u'dateasked': incident.report_date.isoformat(),
        u'description': '\n'.join(description) if description else u'Nieuwe melding',
        u'comment': comment,
        u'type': incident_type,
        u'urgencyType': u'melding',
        u'place': place,
        u'latitude': latitude,
        u'longitude': longitude,
        u'requestor': requestor,
        u'contactmethod': u'app',
        u'externId': incident.id,
        u'attachments': attachments

    }
    xml = dicttoxml.dicttoxml(work_order, custom_root='Workorder', attr_type=False)
    prettyxml = dicttoxml.parseString(xml).toprettyxml(encoding='utf8')
    details = IncidentDetails()
    details.title = incident_type
    details.description = '\n'.join(description) if description else None
    if latitude and longitude:
        details.geo_location = ndb.GeoPt(latitude, longitude)
    # Remove encoding since 3p can't process it
    return prettyxml.replace('<?xml version="1.0" encoding="utf8"?>', '<?xml version="1.0"?>'), details, user_consent


def create_incident_on_gcs(gcs_bucket_name, incident_id, xml_content, attempt=1):
    if not is_file_available(u'/%s/reports/__syncing' % gcs_bucket_name):
        upload_to_gcs(xml_content, u'text/xml', u'/%s/reports/%s.xml' % (gcs_bucket_name, incident_id))
        return

    deferred.defer(create_incident_on_gcs, gcs_bucket_name, incident_id, xml_content,
                   attempt=attempt + 1,
                   _queue=INCIDENTS_QUEUE,
                   _countdown=10 * attempt)


def incident_follow_up(from_, regex, subject, body):
    # todo-later security validate from
    incident_id = regex.groupdict()['incident_id']
    incident = get_incident(incident_id)
    if not incident:
        logging.debug("Received incident update that is not in our database: '%s'", incident_id)
        return
    rt_user = get_rogerthat_user(incident.user_id)
    member = MemberTO(member=rt_user.email, app_id=rt_user.app_id, alert_flags=2)
    if incident.status == IncidentStatus.NEW:
        incident.set_status(IncidentStatus.IN_PROGRESS)
        incident.put()
        try_or_defer(re_index_incident, incident)
    if isinstance(incident.params, IncidentParamsFlow):
        parent_message_key = incident.params.parent_message_key
        settings = IntegrationSettings.create_key(incident.integration_id)  # type: IntegrationSettings
        try_or_defer(send_rogerthat_message, settings.sik, member, body, parent_message_key=parent_message_key,
                     json_rpc_id=guid())
    else:
        raise Exception('Can\'t process incident feedback with invalid params: %s', incident.params)
