# -*- coding: utf-8 -*-
# Copyright 2020 Green Valley NV
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
import json
import logging
import urllib
from collections import defaultdict

from google.appengine.api import urlfetch
from google.appengine.ext import ndb, deferred

from framework.plugin_loader import get_config
from markdown import markdown
from plugins.reports.consts import NAMESPACE
from plugins.reports.integrations.int_topdesk.consts import TopdeskPropertyName, TopdeskFieldMappingType
from plugins.reports.integrations.int_topdesk.topdesk import create_topdesk_person, update_topdesk_person, \
    get_new_incident_data, upload_attachment, topdesk_api_call, get_reverse_value
from plugins.reports.models import IncidentDetails, IntegrationParamsTopdesk, IdName, Incident, \
    TopdeskSettings, IntegrationSettings
from plugins.reports.utils import get_step
from plugins.rogerthat_api.to.messaging.flow import FormFlowStepTO, MessageFlowStepTO, BaseFlowStepTO
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

    incident_details = IncidentDetails()

    data = get_new_incident_data(settings, rt_user)
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
            if step.answer_id == FormTO.POSITIVE:
                val = step.get_value()
                if not val:
                    continue
                if isinstance(val, LocationWidgetResultTO):
                    address = reverse_geocode_location(val)
                    if address:
                        step_value = '%s\n%s' % (step.display_value, address)
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

    incident_details.title = data['briefDescription']
    incident_details.description = result_text

    logging.debug('Creating incident: %s', data)
    response = topdesk_api_call(settings, '/api/incidents', urlfetch.POST, data)
    logging.debug('Result from server: %s', response)

    count = 0
    for url in attachments:
        count += 1
        deferred.defer(upload_attachment, config.id, response['id'], url, 'foto-%s.jpg' % count, 'image/jpeg')

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
                result = result and result.strip() or mapping.default_value or ''
                if mapping.property in (TopdeskPropertyName.OPTIONAL_FIELDS_1, TopdeskPropertyName.OPTIONAL_FIELDS_2):
                    custom_values[mapping.property][mapping.value_properties[0]] = result
                    included_step_ids.add(step.step_id)
                else:
                    if mapping.property == TopdeskPropertyName.BRIEF_DESCRIPTION:
                        if result:
                            custom_values[mapping.property] = result[:80]
                    else:
                        custom_values[mapping.property]['id'] = result
                        included_step_ids.add(step.step_id)
            elif mapping.type == TopdeskFieldMappingType.GPS_SINGLE_FIELD:
                assert isinstance(result, LocationWidgetResultTO)
                custom_values[mapping.property][mapping.value_properties[0]] = '%s,%s' % (result.latitude,
                                                                                          result.longitude)
            elif mapping.type == TopdeskFieldMappingType.GPS_DUAL_FIELD:
                assert isinstance(result, LocationWidgetResultTO)
                custom_values[mapping.property][mapping.value_properties[0]] = result.latitude
                custom_values[mapping.property][mapping.value_properties[1]] = result.longitude
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


