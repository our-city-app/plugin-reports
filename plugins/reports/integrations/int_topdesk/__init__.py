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

import base64
from collections import defaultdict
import json
import logging
import urllib

from google.appengine.api import urlfetch
from google.appengine.ext import deferred, ndb
from urllib3 import encode_multipart_formdata

from framework.plugin_loader import get_config
from framework.utils import try_or_defer, guid
from mcfw.exceptions import HttpBadRequestException
from plugins.reports.bizz.rogerthat import send_rogerthat_message
from plugins.reports.consts import NAMESPACE
from plugins.reports.dal import get_integration_settings, get_incident, \
    get_rogerthat_user
from plugins.reports.integrations.int_topdesk.consts import ENDPOINTS, PropertyName, \
    FieldMappingType
from plugins.reports.integrations.int_topdesk.topdesk import upload_attachment, \
    topdesk_api_call
from plugins.reports.models import IncidentDetails, Incident
from plugins.reports.utils import get_step
from plugins.rogerthat_api.to import MemberTO
from plugins.rogerthat_api.to.messaging.flow import FormFlowStepTO, \
    MessageFlowStepTO, BaseFlowStepTO
from plugins.rogerthat_api.to.messaging.forms import Widget, FormTO, \
    OpenIdWidgetResultTO, LocationWidgetResultTO

SINGLE_LINE_FORM_TYPES = (Widget.TYPE_SINGLE_SELECT, Widget.TYPE_MULTI_SELECT, Widget.TYPE_DATE_SELECT,
                          Widget.TYPE_RANGE_SLIDER)


def create_incident(settings, rt_user, incident, steps):
    name_step = get_step(steps, 'message_name')
    if name_step:
        pass  # details.name = name_step.get_value().strip() # todo fix
    openid_step = find_step_by_type(steps, Widget.TYPE_OPENID)
    openid_result = openid_step and openid_step.form_result.result  # type: OpenIdWidgetResultTO
    # todo fix openid_result
    attachments = []

    brief_description = 'Nieuwe melding door %s' % rt_user.name

    data = {
        PropertyName.CALL_TYPE: {
            'id': settings.call_type_id
        },
        PropertyName.ENTRY_TYPE: {
            'id': settings.entry_type_id
        },
        PropertyName.CATEGORY: {
            'id': settings.category_id
        },
        PropertyName.SUB_CATEGORY: {
            'id': settings.sub_category_id
        },
        PropertyName.LOCATION: {
            'id': None
        },
        PropertyName.OPERATOR: {
            'id': settings.operator_id
        },
        PropertyName.OPERATOR_GROUP: {
            'id': settings.operator_group_id
        },
        PropertyName.BRANCH: {
            'id': settings.branch_id
        },
        'briefDescription': brief_description[:75],
    }
    if settings.unregistered_users:
        data['caller'] = {
            'email': rt_user.email,
            'dynamicName': rt_user.name
        }
        if settings.caller_branch_id:
            data['caller']['branch'] = {'id': settings.caller_branch_id}
    else:
        data['callerLookup'] = {
            'id': rt_user.topdesk_id
        }
    details = IncidentDetails(status=Incident.STATUS_TODO,
                              title=u'todo')
    custom_values, included_step_ids = get_field_mapping_values(settings, steps, details)
    logging.info('Updating request data with %s', custom_values)
    data.update(custom_values)
    result_text = []
    request_step_ids = {mapping.step_id for mapping in settings.field_mapping
                        if mapping.property == PropertyName.REQUEST and mapping.step_id not in included_step_ids}
    # Populate the 'request' field and upload attachments
    for step in steps:
        if isinstance(step, FormFlowStepTO) and step.answer_id == FormTO.POSITIVE:
            if step.form_type == Widget.TYPE_PHOTO_UPLOAD:
                attachments.append(step.get_value())
                continue
            elif isinstance(step.form_result.result, OpenIdWidgetResultTO):
                continue
        if step.step_id not in request_step_ids:
            continue
        if isinstance(step, FormFlowStepTO):
            if step.answer_id == FormTO.POSITIVE:
                if isinstance(step.get_value(), LocationWidgetResultTO):
                    details.geo_location = ndb.GeoPt(step.get_value().latitude, step.get_value().longitude)
                    address = reverse_geocode_location(step.get_value())
                    if address:
                        step_value = '%s\n%s' % (step.display_value, address)
                    else:
                        step_value = step.display_value
                else:
                    step_value = step.display_value
            else:
                step_value = step.button
        elif isinstance(step, MessageFlowStepTO):
            if step.step_type == BaseFlowStepTO.TYPE_MESSAGE:
                step_value = step.button
                if step_value is None:
                    step_value = "Ok"
            else:
                step_value = step.button
        else:
            raise Exception('Unsupported step type %s' % step.step_type)
        step_value = step_value.replace('\n', '<br>')
        if step.step_type == BaseFlowStepTO.TYPE_MESSAGE or step.form_type in SINGLE_LINE_FORM_TYPES:
            # Question and answer on the same line
            result_text.append('<b>%s:</b> %s' % (step.message, step_value))
        else:
            # Question and answer on a new line
            result_text.append('<b>%s</b>' % step.message)
            result_text.append(step_value)
        result_text.append('<br>')
    result_text = '<br>'.join(result_text)
    data['request'] = result_text

    for key, value in data.items():
        if isinstance(value, dict):
            if 'id' in value and not value['id']:
                del data[key]
    logging.debug('Creating incident: %s', data)
    response = topdesk_api_call(settings, '/api/incidents', urlfetch.POST, data)
    logging.debug('Result from server: %s', response)

    count = 0
    for url in attachments:
        count += 1
        deferred.defer(upload_attachment, settings.sik, response['id'], url, 'foto-%s.jpg' % count)

    visible = details.title and details.description and details.geo_location
    params = {
        'id': response['id'],
        'number': response['number'],
        'status': response['status']
    }
    return visible, params, details


def get_field_mapping_values(settings, steps, details):
    # Maps form step values to fields for a topdesk incident
    custom_values = defaultdict(dict)
    included_step_ids = set()
    for mapping in settings.field_mapping:
        if mapping.type == FieldMappingType.FIXED_VALUE:
            custom_values[mapping.property][mapping.value_properties[0]] = mapping.default_value
            continue
        if mapping.property == PropertyName.REQUEST:
            # request field is a special snowflake that gets populated later
            continue
        step = get_step(steps, mapping.step_id)
        if isinstance(step, FormFlowStepTO):
            if step.answer_id != FormTO.POSITIVE:
                continue
            result = step.get_value()
            if mapping.type == FieldMappingType.TEXT:
                result = result and result.strip() or ''
                if mapping.property in (PropertyName.OPTIONAL_FIELDS_1, PropertyName.OPTIONAL_FIELDS_2):
                    custom_values[mapping.property][mapping.value_properties[0]] = result or mapping.default_value
                    included_step_ids.add(step.step_id)
                else:
                    if mapping.property == PropertyName.BRIEF_DESCRIPTION:
                        if result:
                            custom_values[mapping.property] = result[:80] or mapping.default_value
                            details.description = custom_values[mapping.property]
                    else:
                        custom_values[mapping.property]['id'] = result or mapping.default_value
                        included_step_ids.add(step.step_id)
            elif mapping.type == FieldMappingType.GPS_SINGLE_FIELD:
                assert isinstance(result, LocationWidgetResultTO)
                custom_values[mapping.property][mapping.value_properties[0]] = '%s,%s' % (result.latitude,
                                                                                          result.longitude)
                included_step_ids.add(step.step_id)
            elif mapping.type == FieldMappingType.GPS_URL:
                assert isinstance(result, LocationWidgetResultTO)
                custom_values[mapping.property][mapping.value_properties[0]] = \
                    'https://www.google.com/maps/search/?api=1&query=%s,%s' % (result.latitude, result.longitude)
                included_step_ids.add(step.step_id)
            elif mapping.type == FieldMappingType.REVERSE_MAPPING:
                assert isinstance(result, unicode)
                value_id = get_reverse_value(settings, mapping.property, result, custom_values)
                if value_id:
                    custom_values[mapping.property]['id'] = value_id
                    included_step_ids.add(step.step_id)
        elif isinstance(step, MessageFlowStepTO):
            custom_values[mapping.property]['id'] = step.answer_id.lstrip('button_')
            included_step_ids.add(step.step_id)
    return custom_values, included_step_ids


def reverse_geocode_location(result):
    # type: (LocationWidgetResultTO) -> str
    url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    maps_key = get_config(NAMESPACE).google_maps_key
    params = urllib.urlencode({'latlng': '%s,%s' % (result.latitude, result.longitude), 'key': maps_key})
    response = urlfetch.fetch(url + params)
    result = json.loads(response.content)
    status = result['status']
    if status == 'ZERO_RESULTS':
        return None
    elif status != 'OK':
        logging.debug(response.content)
        raise Exception('Error while looking up address')
    return result.get('results', [{}])[0].get('formatted_address')


def find_step_by_type(steps, type):
    filtered = [step for step in steps
                if isinstance(step, FormFlowStepTO) and step.answer_id == FormTO.POSITIVE and step.form_type == type]
    if filtered:
        return filtered[0]


def _get_topdesk_values(settings, property_name, custom_values):
    resource = ENDPOINTS[property_name]
    query = '?'
    if property_name == PropertyName.LOCATION:
        branch_id = custom_values.get(PropertyName.BRANCH, {}).get('id') or settings.branch_id  # todo fix
        if not branch_id:
            return []
        query += '&branch=%s' % branch_id
    return topdesk_api_call(settings, '/api%s%s' % (resource, query), urlfetch.GET)


def get_reverse_value(settings, property_name, value, custom_values):
    things = _get_topdesk_values(settings, property_name, custom_values)
    if things:
        value = value.strip()
        for thing in things:
            if thing['name'] == value:
                return thing['id']


def incident_feedback(sik, incident_id, message):
    incident = get_incident(incident_id)
    if not incident:
        logging.debug('Received incident update for incident that is not in our database: %s', incident_id)
        return
    if sik != incident.sik:
        logging.error('Incident sik did not match topdesk sik %s', sik)
        return
    settings = get_integration_settings(sik)
    if not settings:
        logging.error('Could not find topdesk settings for %s', sik)
        return
    logging.debug("incident_feedback for id %s", incident_id)
    response = topdesk_api_call(settings, '/api/incidents/id/%s' % incident_id)
    logging.debug("Incident result from server: %s", response)
    status = response['processingStatus']['name']

    rt_user = get_rogerthat_user(incident.user_id)
    member = MemberTO(member=rt_user.email, app_id=rt_user.app_id, alert_flags=2)
    complete_message = u'Uw melding is geüpdatet.\nDe huidige status van uw melding is nu "%s".\n%s' % (status, message)
    try_or_defer(send_rogerthat_message, sik, member, complete_message,
                 parent_message_key=incident.parent_message_key, json_rpc_id=guid())  # todo fix
