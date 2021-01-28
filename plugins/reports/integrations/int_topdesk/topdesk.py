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
import json
import logging
from cStringIO import StringIO
from mimetypes import guess_extension

from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext.deferred import deferred

from PIL import Image
from framework.utils import guid
from markdown import markdown
from mcfw.cache import cached
from mcfw.exceptions import HttpBadRequestException
from mcfw.rpc import arguments, returns
from plugins.reports.bizz.rogerthat import send_rogerthat_message
from plugins.reports.dal import get_integration_settings
from plugins.reports.integrations.int_topdesk.consts import ENDPOINTS, TopdeskPropertyName
from plugins.reports.integrations.int_topdesk.models import TOPDeskFormConfiguration, TOPDeskCategoryMapping, \
    BaseComponent, TOPDeskSubCategoryMapping, TOPDeskBriefDescriptionMapping, TOPDeskOptionalFields1Mapping, \
    TOPDeskOptionalFields2Mapping, OptionalFieldLocationOptions, OptionalFieldLocationFormat
from plugins.reports.models import TopdeskSettings, RogerthatUser, Incident, IncidentDetails, IdName, \
    IntegrationParamsTopdesk, IntegrationSettings, IntegrationProvider, IncidentParamsForm
from plugins.reports.to import FormSubmissionTO, DynamicFormTO, FieldComponentTO, SingleSelectComponentValueTO, \
    BaseComponentValue, LocationComponentValueTO, FileComponentValueTO
from plugins.rogerthat_api.to import MemberTO
from plugins.rogerthat_api.to.messaging.forms import OpenIdWidgetResultTO
from typing import Dict, List
from urllib3 import encode_multipart_formdata


class TopdeskApiException(Exception):

    def __init__(self, urlfetch_result):
        # type: (urlfetch._URLFetchResult) -> TopdeskApiException
        self.status_code = urlfetch_result.status_code
        self.content = urlfetch_result.content
        try:
            self.message = json.loads(urlfetch_result.content)[0]['message']
        except:
            self.message = urlfetch_result.content
        self.urlfetch_result = urlfetch_result

    def __str__(self):
        return self.message


def _get_person_info_from_rogerthat_user(settings, rogerthat_user):
    # type: (TopdeskSettings, RogerthatUser) -> dict
    split_name = rogerthat_user.name.split(' ')
    first_name = split_name[0]
    sur_name = ''
    if len(split_name) > 1:
        sur_name = ''.join(split_name[1:])
    if not sur_name:
        sur_name = '(onbekend)'
    person = {
        'email': rogerthat_user.email,
        'firstName': first_name,
        'surName': sur_name,
    }
    if settings.caller_branch_id:  # todo fix
        person['branch'] = {
            'id': settings.caller_branch_id  # todo fix
        }
    return person


def _update_person_with_openid_data(person, openid_result):
    # type: (dict, OpenIdWidgetResultTO) -> dict
    mapping = {
        'firstName': openid_result.given_name,
        'surName': openid_result.family_name,
        'email': openid_result.email,
        'phoneNumber': openid_result.phone_number,
    }
    for key, value in mapping.iteritems():
        if value:
            person[key] = value
    if openid_result.gender:
        # must be one of UNDEFINED, MALE, FEMALE
        person['gender'] = openid_result.gender.upper()
    return person


def create_topdesk_person(settings, rogerthat_user, openid_result):
    # type: (TopdeskSettings, RogerthatUser, OpenIdWidgetResultTO) -> str
    person = _get_person_info_from_rogerthat_user(settings, rogerthat_user)
    if openid_result:
        person = _update_person_with_openid_data(person, openid_result)
    created_person = topdesk_api_call(settings, '/api/persons', urlfetch.POST, person)
    logging.debug('Created topdesk person: %s', created_person)
    return created_person['id']


def update_topdesk_person(settings, rogerthat_user, openid_result):
    # type: (TopdeskSettings, RogerthatUser, OpenIdWidgetResultTO) -> dict
    person = _get_person_info_from_rogerthat_user(settings, rogerthat_user)
    person = _update_person_with_openid_data(person, openid_result)
    url = '/api/persons/id/%s' % rogerthat_user.external_id
    updated_person = topdesk_api_call(settings, url, urlfetch.PUT, person)
    logging.debug('Updated topdesk person: %s', updated_person)
    return updated_person


def _get_headers(username, password):
    base64string = base64.b64encode('%s:%s' % (username, password))
    return {
        'Authorization': "Basic %s" % base64string,  # TODO upgrade to api tokens instead of this
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }


def topdesk_api_call(settings, path, method=urlfetch.GET, payload=None):
    # type: (TopdeskSettings, str, int, dict) -> dict
    full_url = '%s%s' % (settings.api_url, path)
    headers = _get_headers(settings.username, settings.password)
    response = urlfetch.fetch(full_url,
                              headers=headers,
                              payload=json.dumps(payload) if payload else None,
                              method=method,
                              deadline=30)  # type: urlfetch._URLFetchResult

    should_raise = False
    if method == urlfetch.GET and response.status_code not in (200, 204, 206,):
        should_raise = True
    if method == urlfetch.POST and response.status_code not in (201,):
        should_raise = True

    if should_raise:
        logging.info('%s\nHeaders: %s', full_url, headers)
        if response.content:
            logging.info('Content: %s', response.content)
        if payload:
            logging.info('Payload: %s', payload)
        raise TopdeskApiException(response)

    return json.loads(response.content) if response.content else None


@cached(0)
@returns([dict])
@arguments(integration_id=long, path=unicode)
def topdesk_integration_call(integration_id, path):
    settings = IntegrationSettings.create_key(integration_id).get()  # type: IntegrationSettings
    if settings.integration != IntegrationProvider.TOPDESK:
        raise HttpBadRequestException('This integration is not a topdesk integration')
    return topdesk_api_call(settings.data, '/api' + path, urlfetch.GET)


def get_topdesk_data(url, username, password):
    # type: (str,str,str) -> dict
    paths = [ENDPOINTS[prop] for prop in
             (TopdeskPropertyName.ENTRY_TYPE, TopdeskPropertyName.CALL_TYPE, TopdeskPropertyName.CATEGORY,
              TopdeskPropertyName.SUB_CATEGORY,
              TopdeskPropertyName.BRANCH, TopdeskPropertyName.OPERATOR_GROUP, TopdeskPropertyName.OPERATOR)]
    rpcs = []
    for path in paths:
        full_url = '%s/api%s' % (url, path)
        headers = _get_headers(username, password)
        rpc = urlfetch.create_rpc(20)
        urlfetch.make_fetch_call(rpc, full_url, headers=headers)
        rpcs.append(rpc)
    try:
        entry_types, call_types, categories, sub_categories, branches, operator_groups, operators = [
            json.loads(rpc.get_result().content) if rpc.get_result().status_code == 200 else [] for rpc in rpcs]
    except:
        logging.debug('Failed to exec rpc to topdesk', exc_info=True)
        raise HttpBadRequestException('%s: %s' % (rpcs[0].get_result().status_code, rpcs[0].get_result().content))
    return {
        'entryTypes': entry_types,
        'callTypes': call_types,
        'categories': categories,
        'subCategories': sub_categories,
        'branches': branches,
        'operatorGroups': operator_groups,
        'operators': operators,
    }


def _download(url):
    response = urlfetch.fetch(url, deadline=30)
    if response.status_code != 200:
        raise Exception('Failed to download url: %s' % url)
    return str(response.content)


def _maybe_resize_image(image, content_type):
    img_file = StringIO(image)
    img = Image.open(img_file)
    width, height = img.size
    max_width = 2560
    if width < max_width:
        return image, content_type
    new_height = int(float(height) / float(width) * max_width)
    result_image = img.resize((max_width, new_height))  # type: Image.Image
    result = StringIO()
    result_image.save(result, 'jpeg')
    return result.getvalue(), 'image/jpeg'


def upload_attachment(integration_id, topdesk_incident_id, url, file_name, content_type):
    file_content = _download(url)

    if content_type.startswith('image'):
        file_content, content_type = _maybe_resize_image(file_content, content_type)
    payload, payload_content_type = encode_multipart_formdata([
        ('file', (file_name.replace(' ', '_').replace(':', '-'), file_content, content_type)),
    ])
    settings = get_integration_settings(integration_id).data
    headers = _get_headers(settings.username, settings.password)  # todo fix
    headers['Content-Type'] = payload_content_type

    response = urlfetch.fetch('%s/api/incidents/id/%s/attachments' % (settings.api_url, topdesk_incident_id),
                              payload=payload,
                              method=urlfetch.POST,
                              headers=headers,
                              deadline=30)

    if response.status_code != 200:
        logging.debug(response.content)
        raise Exception("Failed to upload file %s with status code %s" % (file_name, response.status_code))


def create_topdesk_incident_from_form(config, form_configuration, submission, form, incident, rt_user):
    # type: (IntegrationSettings, TOPDeskFormConfiguration, FormSubmissionTO, DynamicFormTO, Incident, RogerthatUser) -> bool
    topdesk_settings = config.data  # type; TopdeskSettings
    form_def_sections = {section.id: {component.id: component for component in section.components if
                                      isinstance(component, FieldComponentTO)}
                         for section in form.sections}
    submitted_components = {
        section.id: {comp.id: comp for comp in section.components}
        for section in submission.sections
    }  # type: Dict[str, Dict[str, BaseComponentValue]]
    topdesk_mapping = {section.id: section.components for section in form_configuration.mapping}

    if not topdesk_settings.unregistered_users and not rt_user.external_id:
        rt_user.external_id = create_topdesk_person(topdesk_settings, rt_user, None)
        rt_user.put()
    new_incident_data = get_new_incident_data(topdesk_settings, rt_user)

    # components that don't need to be added to the 'request' field
    processed_components_per_section = {}
    for section_id, component_mappings in topdesk_mapping.iteritems():
        processed_components = set()
        def_components = form_def_sections.get(section_id)
        submitted_comps = submitted_components.get(section_id)  # type: List[BaseComponent]
        if not def_components or not submitted_comps:
            continue
        for mapping in component_mappings:
            component_id = mapping.id
            component_def = def_components.get(component_id)
            component_value = submitted_comps.get(component_id)
            if not component_def or not component_value:
                continue
            if isinstance(mapping, TOPDeskCategoryMapping):
                if isinstance(component_value, SingleSelectComponentValueTO):
                    selected_category = mapping.categories.get(component_value.value)
                    if selected_category:
                        new_incident_data[TopdeskPropertyName.CATEGORY]['id'] = selected_category
                        processed_components.add(component_id)
                    else:
                        logging.debug('Could not find selected category %s for mapping %s', mapping)
            elif isinstance(mapping, TOPDeskSubCategoryMapping):
                if isinstance(component_value, SingleSelectComponentValueTO):
                    selected_sub_category = mapping.subcategories.get(component_value.value)
                    if selected_sub_category:
                        new_incident_data[TopdeskPropertyName.SUB_CATEGORY]['id'] = selected_sub_category
                        processed_components.add(component_id)
                    else:
                        logging.debug('Could not find selected subcategory %s for mapping %s', component_value.value,
                                      mapping)
            elif isinstance(mapping, TOPDeskBriefDescriptionMapping):
                brief_description = _get_brief_description(component_def, component_value)
                if brief_description:
                    new_incident_data[TopdeskPropertyName.BRIEF_DESCRIPTION] = brief_description
                    processed_components.add(component_id)
            elif isinstance(mapping, (TOPDeskOptionalFields1Mapping, TOPDeskOptionalFields2Mapping)):
                if isinstance(mapping.options, OptionalFieldLocationOptions):
                    if isinstance(component_value, LocationComponentValueTO):
                        location_format = mapping.options.format
                        if location_format == OptionalFieldLocationFormat.LATITUDE:
                            topdesk_value = component_value.latitude
                        elif location_format == OptionalFieldLocationFormat.LONGITUDE:
                            topdesk_value = component_value.longitude
                        elif location_format == OptionalFieldLocationFormat.LATITUDE_LONGITUDE:
                            topdesk_value = '%s,%s' % (component_value.latitude, component_value.longitude)
                        else:
                            raise NotImplementedError(
                                'OptionalFieldLocationFormat %s not implemented' % location_format)
                        new_incident_data[mapping.type][mapping.field] = topdesk_value
                        processed_components.add(component_id)
                    else:
                        logging.warning('Cannot process component value %s for mapping %s', component_value,
                                        mapping)
                else:
                    raise NotImplementedError('Mapping options %s not implemented' % mapping.options)
        processed_components_per_section[section_id] = processed_components

    # Add all unprocessed components to the 'request' field
    request_lines = []
    attachments = []  # type: List[FileComponentValueTO]
    incident_details = IncidentDetails()
    for section_id, components in submitted_components.iteritems():
        section_def = form_def_sections.get(section_id)
        if not section_def:
            logging.debug('Skipping section %s, definition not found', section_id)
            continue
        for component_id, component_value in components.iteritems():  # type: str, BaseComponentValue
            if component_id in processed_components_per_section.get(section_id, {}):
                continue
            component_def = section_def.get(component_id)  # type: FieldComponentTO
            if not component_def:
                logging.debug('Skipping component %s-%s, definition not found', section_id, component_id)
                continue
            else:
                if isinstance(component_value, LocationComponentValueTO):
                    incident_details.geo_location = ndb.GeoPt(lat=component_value.latitude,
                                                              lon=component_value.longitude)
                elif isinstance(component_value, FileComponentValueTO):
                    attachments.append(component_value)
                    continue
                request_lines.append('**%s**' % component_def.title)
                request_lines.append(component_value.get_string_value(component_def))
                request_lines.append('\n')
    request_text = '\n'.join(request_lines)
    new_incident_data[TopdeskPropertyName.REQUEST] = markdown(request_text, output_format='html') \
        .replace('\n', '<br>') \
        .replace('<p>', '') \
        .replace('</p>', '<br>')

    for key, value in new_incident_data.items():
        if isinstance(value, dict):
            if 'id' in value and not value['id']:
                del new_incident_data[key]
    incident_details.title = new_incident_data[TopdeskPropertyName.BRIEF_DESCRIPTION]
    incident_details.description = request_text

    logging.debug('Creating incident: %s', new_incident_data)
    response = topdesk_api_call(topdesk_settings, '/api/incidents', urlfetch.POST, new_incident_data)
    logging.debug('Result from server: %s', response)

    for i, attachment in enumerate(attachments):
        extension = guess_extension(attachment.file_type, strict=False)
        if extension == '.jpe':
            extension = '.jpeg'
        deferred.defer(upload_attachment, config.id, response['id'], attachment.value,
                       'attachment-%d%s' % (i, extension), attachment.file_type)

    integration_params = IntegrationParamsTopdesk()
    integration_params.status = IdName.from_dict(response['processingStatus'])
    integration_params.id = response['id']
    incident.integration_params = integration_params
    incident.external_id = response['number']  # e.g. M 1602 341
    incident.details = incident_details
    # TODO implement when needed
    # incident.user_consent = user_consent
    incident.params = IncidentParamsForm(
        submission_id=submission.id,
    )
    # Add countdown to ensure this runs after incident is saved to datastore
    deferred.defer(_send_confirmation_message, incident.id, incident.integration_id, submission, form, rt_user, guid(),
                   _countdown=5)
    return True


@ndb.transactional(xg=True)
def _send_confirmation_message(incident_id, integration_id, submission, form, rt_user, json_rpc_id):
    # type: (str, int, FormSubmissionTO, DynamicFormTO, RogerthatUser, str) -> None
    keys = [Incident.create_key(incident_id), IntegrationSettings.create_key(integration_id)]
    incident, integration_settings = ndb.get_multi(keys)  # type: Incident, IntegrationSettings
    if not incident:
        logging.debug('Not sending confirmation message: incident %s does not exist', incident_id)
        return
    member = MemberTO(member=rt_user.email, app_id=rt_user.app_id, alert_flags=2)
    summary_lines = []
    form_def_sections = {section.id: {component.id: component for component in section.components if
                                      isinstance(component, FieldComponentTO)}
                         for section in form.sections}
    for section in submission.sections:
        section_def = form_def_sections.get(section.id)
        if not section_def:
            continue
        for component in section.components:
            component_def = section_def.get(component.id)
            if not component_def:
                continue
            summary_lines.append('**%s**' % component_def.title.strip())
            if isinstance(component, FileComponentValueTO):
                summary_lines.append('[%s](%s)' % (component.name, component.value))
            else:
                summary_lines.append(component.get_string_value(component_def))
            summary_lines.append('')
    complete_message = 'We hebben uw melding goed ontvangen. ' \
                       'Indien er updates zijn zullen we u via dit bericht op de hoogte houden. ' \
                       'Hieronder vind u de opgestuurde gegevens van uw melding.\n%s' % '\n'.join(summary_lines)
    message_key = send_rogerthat_message(integration_settings.sik, member, complete_message, json_rpc_id=json_rpc_id)
    assert isinstance(incident.params, IncidentParamsForm)
    incident.params.parent_message_key = message_key
    incident.put()


def _get_brief_description(component_def, component_value):
    # type: (FieldComponentTO, BaseComponentValue) -> str
    text = component_value.get_string_value(component_def)
    return text and text[:80]


def get_new_incident_data(topdesk_settings, rt_user):
    # type: (TopdeskSettings, RogerthatUser) -> dict
    data = {
        TopdeskPropertyName.CALL_TYPE: {
            'id': topdesk_settings.call_type_id
        },
        TopdeskPropertyName.ENTRY_TYPE: {
            'id': topdesk_settings.entry_type_id
        },
        TopdeskPropertyName.CATEGORY: {
            'id': topdesk_settings.category_id
        },
        TopdeskPropertyName.SUB_CATEGORY: {
            'id': topdesk_settings.sub_category_id
        },
        TopdeskPropertyName.LOCATION: {
            'id': None
        },
        TopdeskPropertyName.OPERATOR: {
            'id': topdesk_settings.operator_id
        },
        TopdeskPropertyName.OPERATOR_GROUP: {
            'id': topdesk_settings.operator_group_id
        },
        TopdeskPropertyName.BRANCH: {
            'id': topdesk_settings.branch_id
        },
        TopdeskPropertyName.BRIEF_DESCRIPTION: 'Nieuwe melding',
        TopdeskPropertyName.OPTIONAL_FIELDS_1: {},
        TopdeskPropertyName.OPTIONAL_FIELDS_2: {},
    }

    if topdesk_settings.unregistered_users:
        data['caller'] = {
            'email': rt_user.email,
            'dynamicName': rt_user.name
        }
        if topdesk_settings.caller_branch_id:
            data['caller']['branch'] = {'id': topdesk_settings.caller_branch_id}
    else:
        data['callerLookup'] = {
            'id': rt_user.external_id
        }
    return data


def get_topdesk_values(settings, property_name, custom_values):
    resource = ENDPOINTS[property_name]
    query = '?'
    if property_name == TopdeskPropertyName.LOCATION:
        branch_id = custom_values.get(TopdeskPropertyName.BRANCH, {}).get('id') or settings.branch_id
        if not branch_id:
            return []
        query += '&branch=%s' % branch_id
    return topdesk_api_call(settings, '/api%s%s' % (resource, query), urlfetch.GET)


def get_reverse_value(settings, property_name, value, custom_values):
    things = get_topdesk_values(settings, property_name, custom_values)
    if things:
        value = value.strip()
        for thing in things:
            if thing['name'] == value:
                return thing['id']
