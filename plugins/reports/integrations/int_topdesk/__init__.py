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
from __future__ import unicode_literals

import json
import logging
import urllib
from collections import defaultdict

from google.appengine.api import urlfetch
from google.appengine.ext import deferred, ndb
from markdown import markdown
from typing import List, Dict, Tuple

from framework.plugin_loader import get_config
from framework.utils import try_or_defer, guid
from plugins.reports.bizz.elasticsearch import re_index_incident
from plugins.reports.bizz.rogerthat import send_rogerthat_message
from plugins.reports.consts import NAMESPACE
from plugins.reports.dal import get_integration_settings, get_rogerthat_user, get_incident_by_external_id
from plugins.reports.integrations.int_topdesk.consts import ENDPOINTS, TopdeskPropertyName, TopdeskFieldMappingType
from plugins.reports.integrations.int_topdesk.topdesk import upload_attachment, topdesk_api_call, \
    create_topdesk_person, update_topdesk_person
from plugins.reports.models import IncidentDetails, Incident, RogerthatUser, TopdeskSettings, IntegrationSettings, \
    IncidentStatus, IncidentParamsFlow, IntegrationParamsTopdesk, IdName
from plugins.reports.utils import get_step
from plugins.rogerthat_api.to import MemberTO
from plugins.rogerthat_api.to.messaging.flow import FormFlowStepTO, MessageFlowStepTO, BaseFlowStepTO, FlowStepTO
from plugins.rogerthat_api.to.messaging.forms import Widget, FormTO, OpenIdWidgetResultTO, LocationWidgetResultTO

SINGLE_LINE_FORM_TYPES = (Widget.TYPE_SINGLE_SELECT, Widget.TYPE_MULTI_SELECT, Widget.TYPE_DATE_SELECT,
                          Widget.TYPE_RANGE_SLIDER)


def create_incident(config, rt_user, incident, steps):
    # type: (IntegrationSettings, RogerthatUser, Incident, List[FlowStepTO]) -> [bool, Dict, IncidentDetails]
    settings = config.data  # type: TopdeskSettings
    openid_step = find_step_by_type(steps, Widget.TYPE_OPENID)
    openid_result = openid_step and openid_step.form_result.result  # type: OpenIdWidgetResultTO

    if not settings.unregistered_users:
        if not rt_user.external_id:
            rt_user.external_id = create_topdesk_person(settings, rt_user, openid_result)
            rt_user.put()
        elif openid_result:
            update_topdesk_person(settings, rt_user, openid_result)

    attachments = []

    brief_description = 'Nieuwe melding'

    incident_details = IncidentDetails()

    data = {
        TopdeskPropertyName.CALL_TYPE: {
            'id': settings.call_type_id
        },
        TopdeskPropertyName.ENTRY_TYPE: {
            'id': settings.entry_type_id
        },
        TopdeskPropertyName.CATEGORY: {
            'id': settings.category_id
        },
        TopdeskPropertyName.SUB_CATEGORY: {
            'id': settings.sub_category_id
        },
        TopdeskPropertyName.LOCATION: {
            'id': None
        },
        TopdeskPropertyName.OPERATOR: {
            'id': settings.operator_id
        },
        TopdeskPropertyName.OPERATOR_GROUP: {
            'id': settings.operator_group_id
        },
        TopdeskPropertyName.BRANCH: {
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
            'id': rt_user.external_id
        }
    custom_values, included_step_ids, user_consent = get_field_mapping_values(settings, steps)
    logging.info('Updating request data with %s', custom_values)
    data.update(custom_values)
    result_text = []  # list of lines of markdown
    request_step_ids = {mapping.step_id for mapping in settings.field_mapping
                        if mapping.property == TopdeskPropertyName.REQUEST and mapping.step_id not in included_step_ids}
    # Populate the 'request' field and upload attachments
    for step in steps:
        if isinstance(step, FormFlowStepTO) and step.answer_id == FormTO.POSITIVE:
            val = step.get_value()
            if step.form_type == Widget.TYPE_PHOTO_UPLOAD:
                attachments.append(val)
                continue
            elif isinstance(step.form_result.result, OpenIdWidgetResultTO):
                continue
            elif isinstance(val, LocationWidgetResultTO):
                incident_details.geo_location = ndb.GeoPt(val.latitude, val.longitude)
        if step.step_id not in request_step_ids:
            continue
        if isinstance(step, FormFlowStepTO):
            step_value = step.display_value
            if step.answer_id == FormTO.POSITIVE:
                val = step.get_value()
                if isinstance(val, LocationWidgetResultTO):
                    address = reverse_geocode_location(val)
                    if address:
                        step_value = '%s\n%s' % (step.display_value, address)
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
        if step.step_type == BaseFlowStepTO.TYPE_MESSAGE or step.form_type in SINGLE_LINE_FORM_TYPES:
            # Question and answer on the same line
            result_text.append('**%s:** %s' % (step.message, step_value))
        else:
            # Question and answer on a new line
            result_text.append('**%s**' % step.message)
            result_text.append(step_value)
        result_text.append('\n')
    result_text = '\n'.join(result_text)
    data['request'] = markdown(result_text, output_format='html') \
        .replace('\n', '<br>') \
        .replace('<p>', '') \
        .replace('</p>', '<br>')

    for key, value in data.items():
        if isinstance(value, dict):
            if 'id' in value and not value['id']:
                del data[key]

    # TODO: add one or more of category/subcategory/calltype to title or description
    incident_details.title = data['briefDescription']
    incident_details.description = result_text

    logging.debug('Creating incident: %s', data)
    response = topdesk_api_call(settings, '/api/incidents', urlfetch.POST, data)
    logging.debug('Result from server: %s', response)

    count = 0
    for url in attachments:
        count += 1
        deferred.defer(upload_attachment, config.id, response['id'], url, 'foto-%s.jpg' % count)

    incident.details = incident_details
    integration_params = IntegrationParamsTopdesk()
    integration_params.status = IdName.from_dict(response['processingStatus'])
    integration_params.id = response['id']
    incident.integration_params = integration_params
    incident.external_id = response['number']  # e.g. M 1602 341
    incident.user_consent = user_consent


def get_field_mapping_values(settings, steps):
    # type: (TopdeskSettings, List[FlowStepTO]) -> Tuple[Dict[str, str], List[str], bool]
    # Maps form step values to fields for a topdesk incident
    has_consent = False
    custom_values = defaultdict(dict)
    included_step_ids = set()
    for mapping in settings.field_mapping:
        if mapping.type == TopdeskFieldMappingType.FIXED_VALUE:
            custom_values[mapping.property][mapping.value_properties[0]] = mapping.default_value
            continue
        if mapping.property == TopdeskPropertyName.REQUEST:
            # request field is a special snowflake that gets populated later
            continue
        step = get_step(steps, mapping.step_id)
        if isinstance(step, FormFlowStepTO):
            if step.answer_id != FormTO.POSITIVE:
                continue
            result = step.get_value()
            if mapping.type == TopdeskFieldMappingType.TEXT:
                result = result and result.strip() or ''
                if mapping.property in (TopdeskPropertyName.OPTIONAL_FIELDS_1, TopdeskPropertyName.OPTIONAL_FIELDS_2):
                    custom_values[mapping.property][mapping.value_properties[0]] = result or mapping.default_value
                    included_step_ids.add(step.step_id)
                else:
                    if mapping.property == TopdeskPropertyName.BRIEF_DESCRIPTION:
                        if result:
                            custom_values[mapping.property] = result[:80] or mapping.default_value
                    else:
                        custom_values[mapping.property]['id'] = result or mapping.default_value
                        included_step_ids.add(step.step_id)
            elif mapping.type == TopdeskFieldMappingType.GPS_SINGLE_FIELD:
                assert isinstance(result, LocationWidgetResultTO)
                custom_values[mapping.property][mapping.value_properties[0]] = '%s,%s' % (result.latitude,
                                                                                          result.longitude)
                included_step_ids.add(step.step_id)
            elif mapping.type == TopdeskFieldMappingType.GPS_URL:
                assert isinstance(result, LocationWidgetResultTO)
                custom_values[mapping.property][mapping.value_properties[0]] = \
                    'https://www.google.com/maps/search/?api=1&query=%s,%s' % (result.latitude, result.longitude)
                included_step_ids.add(step.step_id)
            elif mapping.type == TopdeskFieldMappingType.REVERSE_MAPPING:
                assert isinstance(result, unicode)
                value_id = get_reverse_value(settings, mapping.property, result, custom_values)
                if value_id:
                    custom_values[mapping.property]['id'] = value_id
                    included_step_ids.add(step.step_id)
        elif isinstance(step, MessageFlowStepTO):
            if mapping.type == TopdeskFieldMappingType.PUBLIC_CONSENT:
                has_consent = step.answer_id == mapping.property
            else:
                custom_values[mapping.property]['id'] = step.answer_id.lstrip('button_')
            included_step_ids.add(step.step_id)
    return custom_values, included_step_ids, has_consent


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
    if property_name == TopdeskPropertyName.LOCATION:
        branch_id = custom_values.get(TopdeskPropertyName.BRANCH, {}).get('id') or settings.branch_id
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


def incident_feedback(integration_id, incident_id, message):
    # type: (int, str, str) -> None
    incident = get_incident_by_external_id(integration_id, incident_id)
    if not incident:
        logging.debug('Received incident update for incident that is not in our database: %s\nIntegration id: %s',
                      incident_id, integration_id)
        return
    settings = get_integration_settings(integration_id)
    if not settings:
        logging.error('Could not find topdesk settings for %s', integration_id)
        return
    logging.debug('Received incident feedback: %s', incident_id)
    response = topdesk_api_call(settings.data, '/api/incidents/id/%s' % incident.integration_params.id)
    logging.debug("Incident result from server: %s", response)
    status = response['processingStatus']
    params = incident.integration_params  # type: IntegrationParamsTopdesk
    updated = True
    if response['closed']:
        incident.set_status(IncidentStatus.RESOLVED)
    elif incident.status == IncidentStatus.NEW:
        incident.set_status(IncidentStatus.IN_PROGRESS)
    else:
        updated = False
    message_lines = ['Uw melding is geüpdatet.']
    if params.status.id != status['id']:
        params.status = IdName.from_dict(status)
        message_lines.append('De huidige status van uw melding is nu "%s"' % params.status.name)
    if message and params.last_message != message:
        params.last_message = message
        message_lines.append(message)
        updated = True
    if updated:
        incident.put()
        try_or_defer(re_index_incident, incident)
    if len(message_lines) == 1:
        logging.info('Not sending update message to user since nothing has been updated')
    else:
        rt_user = get_rogerthat_user(incident.user_id)
        member = MemberTO(member=rt_user.email, app_id=rt_user.app_id, alert_flags=2)
        complete_message = '\n'.join(message_lines)
        if isinstance(incident.params, IncidentParamsFlow):
            try_or_defer(send_rogerthat_message, settings.sik, member, complete_message,
                         parent_message_key=incident.params.parent_message_key, json_rpc_id=guid())
        else:
            raise Exception('Can\'t process incident feedback with invalid params: %s', incident.params)
