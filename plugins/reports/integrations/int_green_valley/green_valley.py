# -*- coding: utf-8 -*-
# Copyright 2019 Green Valley NV
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
import re
from base64 import b64encode
from collections import OrderedDict
from mimetypes import guess_extension
from uuid import uuid4
from xml.etree.ElementTree import Element

from google.appengine.api import urlfetch, users
from google.appengine.ext.ndb import GeoPt

from dateutil.parser import parse as parse_date
from framework.plugin_loader import get_config
from framework.utils import azzert
from lxml import etree
from mcfw.consts import DEBUG
from plugins.reports.consts import NAMESPACE
from plugins.reports.dal import get_integration_settings, get_rogerthat_user
from plugins.reports.integrations.int_green_valley.attachments import get_attachment_content
from plugins.reports.integrations.int_green_valley.notifications import GVExternalNotification, send_notification
from plugins.reports.models import GreenValleySettings, Incident, IncidentDetails, IntegrationParamsGreenValley, \
    IncidentStatus, IntegrationSettings, RogerthatUser
from plugins.reports.models.green_valley import GvMappingFlex, GreenValleyFormConfiguration, GvMappingAttachment, \
    GvMappingLocation, GvMappingPerson, GvMappingField, GvMappingConst, GvMappingConsent
from plugins.reports.to import FormSubmissionTO, FieldComponentTO, DynamicFormTO, TextInputComponentValueTO, \
    MultiSelectComponentValueTO, SingleSelectComponentValueTO, LocationComponentValueTO, \
    FileComponentValueTO, MultiSelectComponentTO, ValueTO, ReportsPluginConfiguration
from plugins.rogerthat_api.plugin_consts import NAMESPACE as ROGERTHAT_NAMESPACE
from typing import Optional

ATTR_PREFIX = '__'


def _add_flex(flexes, field_def_id, value, display_value=None):
    flex = {'field_def_id': field_def_id}
    if value:
        flex['string_value'] = value
    if display_value:
        flex['display_value'] = display_value
    flexes.append({'flex': flex})


def _get_extension(content_type):
    ext = guess_extension(content_type)
    if ext == '.jpe':
        ext = '.jpg'
    return ext


def dict2xml(d, name='data'):
    # type: (dict, str) -> str
    r = etree.Element(name)
    return etree.tostring(buildxml(r, d), pretty_print=DEBUG)


def buildxml(r, d):
    # Properties starting with ATTR_PREFIX will be converted to attributes of the parent
    if isinstance(d, dict):
        for k, v in d.iteritems():
            if k.startswith(ATTR_PREFIX):
                r.set(k.lstrip(ATTR_PREFIX), v)
            else:
                s = etree.SubElement(r, k)
                buildxml(s, v)
    elif isinstance(d, tuple) or isinstance(d, list):
        for v in d:
            for key, val in v.iteritems():
                s = etree.SubElement(r, key)
                buildxml(s, val)
    elif isinstance(d, basestring):
        r.text = d
    else:
        r.text = str(d)
    return r


def _order_dict(dictionary, order):
    # type: (dict, list) -> OrderedDict
    """ For some strange reason the values must be present in a specific order or an error like this will be thrown:
AXBException occurred : cvc-complex-type.2.4.a: Invalid content was found starting with element 'address'.
One of '{gender, date_of_birth, place_of_birth, nationality}' is expected.."""
    result = OrderedDict({k: dictionary[k] for k in dictionary
                          if isinstance(k, basestring) and k.startswith(ATTR_PREFIX)})
    for key in order:
        if isinstance(key, tuple):
            parent, children = key
            if parent not in dictionary:
                continue
            if parent not in result:
                result[parent] = OrderedDict()
            if isinstance(dictionary[parent], list):
                result[parent] = [_order_dict(item, children) for item in dictionary[parent]]
            else:
                result[parent] = _order_dict(dictionary[parent], children)
        elif key in dictionary:
            result[key] = dictionary[key]
    return result


def _get_auth_header(configuration):
    # type: (GreenValleySettings) -> str
    return 'Basic %s' % b64encode('%s:%s' % (configuration.username, configuration.password))


def _execute_gv_request(configuration, path, method=urlfetch.GET, body=None):
    url = u'%s/suite-webservice/ws/rest%s' % (configuration.base_url, path)
    headers = {
        'Authorization': _get_auth_header(configuration),
        'Content-Type': 'application/xml',
    }
    if DEBUG:
        logging.debug('Request to %s\n%s', url, body)
    result = urlfetch.fetch(url, body, method, headers=headers, deadline=55)  # type: urlfetch._URLFetchResult
    if DEBUG:
        logging.debug(result.content)
    if result.status_code not in (200, 201):
        if not DEBUG:
            logging.debug(result.content)
        additional = ''
        if result.status_code == 500:
            additional = 'Did you configure the correct type_id?'
        raise Exception(u'Error while executing request to %s: %s %s' % (url, result.status_code, additional))
    return result.content


class IncidentDescription(object):
    title = ''
    description = ''
    lines = []

    def add(self, component, value, field=None):
        # type: (FieldComponentTO, object, object) -> object
        if not value or field in ('type_id', 'type', 'locatiebepaling_blocks'):
            return
        if field == 'subject':
            self.title = value
            return
        if field == 'description':
            self.description = value
            return
        else:
            if component and component.title and value:
                self.lines.append('**%s**\n%s' % (component.title, value))
            elif value:
                self.lines.append(value)

    def to_string(self):
        return '\n'.join(self.lines)


def choices_to_markdown(comp_val, component):
    # type: (MultiSelectComponentValueTO, MultiSelectComponentTO) -> str
    markdown_list = ''
    for choice in component.choices:
        if choice.value in comp_val.values:
            markdown_list += '- %s\n' % choice.label
    return markdown_list


def create_incident(gv_settings, form_configuration, submission, form, incident):
    # type: (GreenValleySettings, GreenValleyFormConfiguration, FormSubmissionTO, DynamicFormTO, Incident) -> bool
    original_form_mapping = {section.id: {component.id: component for component in section.components if
                                          isinstance(component, FieldComponentTO)}
                             for section in form.sections}
    gv_mapping = {section.id: section.components for section in form_configuration.mapping}
    flexes = []
    person = {}
    request = {
        'type_id': form_configuration.type_id,
        'reference': incident.id,
    }
    details = IncidentDetails()
    desc = IncidentDescription()
    user_consent = False

    # TODO: add markdown 'question value' or something
    # That way we can add `*kleur fiets*: groen` instead of `*wat is het kleur van de fiets?*: groen`
    for section_value in submission.sections:
        gv_components = gv_mapping.get(section_value.id, [])
        if not gv_components:
            continue
        component_mapping = {component.id: component for component in section_value.components}
        for gv_comp in gv_components:
            if isinstance(gv_comp, GvMappingConst):
                _add_flex(flexes, gv_comp.field, gv_comp.value, gv_comp.display_value)
                desc.add(None, gv_comp.display_value or gv_comp.value, gv_comp.field)
                continue
            elif isinstance(gv_comp, GvMappingField):
                if gv_comp.value:
                    request[gv_comp.field] = gv_comp.value
                    desc.add(None, gv_comp.value, gv_comp.field)
                    continue
            comp_val = component_mapping.get(gv_comp.id)
            if not comp_val:
                logging.debug('Skipping component %s: not found in form result', gv_comp)
                continue
            component = original_form_mapping.get(section_value.id, {}).get(gv_comp.id)
            if not component:
                logging.debug('Skipping component %s: not found in form definition', gv_comp)
                continue
            if isinstance(gv_comp, GvMappingField):
                value = None
                if isinstance(comp_val, TextInputComponentValueTO):
                    value = comp_val.value
                    if value:
                        desc.add(component, value, gv_comp.field)
                if isinstance(comp_val, MultiSelectComponentValueTO):
                    value = '\n'.join([choice.label for choice in component.choices if choice.value in comp_val.values])
                    desc.add(component, choices_to_markdown(comp_val, component), gv_comp.field)
                if value:
                    request[gv_comp.field] = value
            elif isinstance(gv_comp, GvMappingPerson):
                if isinstance(comp_val, (TextInputComponentValueTO, SingleSelectComponentValueTO)):
                    if gv_comp.sub_field:
                        if gv_comp.field not in person:
                            person[gv_comp.field] = {}
                        person[gv_comp.field][gv_comp.sub_field] = comp_val.value
                    else:
                        person[gv_comp.field] = comp_val.value
            elif isinstance(gv_comp, GvMappingLocation):
                if isinstance(comp_val, LocationComponentValueTO):
                    details.geo_location = GeoPt(comp_val.latitude, comp_val.longitude)
                    _add_flex(flexes, gv_comp.location_type, gv_comp.location_type_value)
                    _add_flex(flexes, gv_comp.address, ', '.join(comp_val.address.address_lines))
                    _add_flex(flexes, gv_comp.coordinates, '%s,%s' % (comp_val.latitude, comp_val.longitude))
            elif isinstance(gv_comp, GvMappingAttachment):
                if isinstance(comp_val, FileComponentValueTO):
                    content, content_type = get_attachment_content(comp_val.value)
                    name = '%s%s' % (gv_comp.name, _get_extension(content_type))
                    flex = {
                        'flex': {
                            'field_def_id': gv_comp.field_def_id,
                            'attachment_value': {'name': name, 'content': content}
                        }
                    }
                    flexes.append(flex)
            elif isinstance(gv_comp, GvMappingFlex):
                if isinstance(comp_val, (TextInputComponentValueTO, SingleSelectComponentValueTO)):
                    _add_flex(flexes, gv_comp.field_def_id, comp_val.value)
                    desc.add(component, comp_val.value)
                elif isinstance(comp_val, MultiSelectComponentValueTO):
                    if component and isinstance(component, MultiSelectComponentTO):
                        if isinstance(gv_comp, GvMappingFlex):
                            choice_mapping = {c.value: c for c in component.choices}  # type: dict[str, ValueTO]
                            for value in comp_val.values:
                                chosen_value = choice_mapping.get(value)
                                if chosen_value:
                                    _add_flex(flexes, gv_comp.field_def_id, value, chosen_value.label)
                            desc.add(component, choices_to_markdown(comp_val, component))
            elif isinstance(gv_comp, GvMappingConsent):
                if isinstance(comp_val, SingleSelectComponentValueTO):
                    user_consent = gv_comp.value_id == comp_val.value
                elif isinstance(comp_val, MultiSelectComponentValueTO):
                    user_consent = gv_comp.value_id in comp_val.values
            else:
                raise Exception('Unknown component type: %s' % gv_comp)
    if flexes:
        request['flexes'] = flexes
    if person:
        person[ATTR_PREFIX + 'sequence'] = '1'
        person[ATTR_PREFIX + 'group_type'] = 'REQUESTER'
        request['agents'] = {'person': person}

    if not request.get('description') and not person:
        logging.info('Not creating case: not enough information')
        return False

    property_order = [
        'type_id',
        'subject',
        'description',
        ('flexes', [
            ('flex', [
                'field_def_id',
                'string_value',
                'display_value',
                ('attachment_value', ['name', 'content']),
            ])
        ]),
        'documents',
        ('agents', [
            ('person', [
                ('contact', ['title', 'nickname', 'phone_number', 'mobile_number', 'email', 'website', 'fax']),
                ('address', ['street_name', 'house_number', 'zip_code', 'city', 'country']),
                'flexes',
                'identity_number',
                'function',
                'first_name',
                'family_name',
                'gender',
                'date_of_birth',
                'place_of_birth',
                'nationality'
            ])
        ])
    ]

    details.title = desc.title
    if desc.description:
        description = desc.description + '\n'
    else:
        description = ''
    details.description = description + desc.to_string()
    incident.details = details
    if DEBUG:
        logging.debug('Incident details: %s', details)

    ordered_request = _order_dict(request, property_order)
    body = dict2xml(ordered_request, name='create_case_request')
    logging.debug('Submitting case request:\n%s',
                  re.sub(r'<content>.*?</content>', r'<content>(content omitted)</content>', body))
    result = _execute_gv_request(gv_settings, '/cases', urlfetch.POST, body)
    incident.external_id = etree.XML(result).get('id')
    incident.user_consent = user_consent
    incident.integration_params = IntegrationParamsGreenValley(notification_ids=[])
    return True


def _request(integration_id, proxy_id, topic, command):
    config = get_config(NAMESPACE)  # type: ReportsPluginConfiguration
    for proxy in config.gv_proxies:
        if proxy.id == proxy_id:
            break
    else:
        logging.error('No proxy found for id \'%s\'', proxy_id)
        return
    url = '%s/topics' % proxy.url
    payload = {
        'topic': topic,
        'integration_id': integration_id,
        'command': command
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': proxy.secret
    }
    result = urlfetch.fetch(url, json.dumps(payload), method=urlfetch.POST,
                            headers=headers)  # type: urlfetch._URLFetchResult
    if result.status_code not in (200, 204):
        logging.debug('Status: %s\nContent: %s', result.status_code, result.content)
        raise Exception('Could not send command %s for topic %s' % (command, topic))


def register_new_gv_integration(integration_id, topic, proxy_id):
    _request(integration_id, proxy_id, topic, 'subscribe')


def remove_gv_integration(integration_id, topic, proxy_id):
    _request(integration_id, proxy_id, topic, 'unsubscribe')


def handle_message_received(integration_id, notification):
    # type: (int, GVExternalNotification) -> None
    logging.debug('Received notification from Green Valley: %s', notification)
    if not notification.caseReference:
        logging.debug(notification)
        raise Exception('No caseReference set for notification!')
    incident = Incident.get_by_external_id(integration_id, notification.caseReference)  # type: Incident
    integration_settings = get_integration_settings(integration_id)
    if not incident:
        # Incident was not created via this backend. Create it now!
        incident = create_incident_from_gv_notification(integration_settings, notification)
        logging.debug('Created incident: %s', incident)
        incident.put()
    if incident.user_id and notification.id not in incident.integration_params.notification_ids:
        incident.integration_params.notification_ids.append(notification.id)
        if len(incident.integration_params.notification_ids) > 1:
            # Don't send initial message (this will contain the stuff the user has sent in, so there's no point in sending that to the user)
            send_notification(notification, integration_settings, incident)
        incident.put()
    else:
        logging.debug('Not sending notification')


def create_incident_from_gv_notification(integration_settings, notification):
    # type: (IntegrationSettings, GVExternalNotification) -> Incident
    user_id = None
    if notification.ocaContext:
        # Resolve user id from ocaContext
        app_user = get_app_user_from_oca_context(notification.ocaContext)
        if app_user:
            user_id = app_user.email()
            rt_user = get_rogerthat_user(user_id)
            if not rt_user:
                user_email, app_id = get_app_user_tuple_by_email(user_id)
                rt_user = RogerthatUser(key=RogerthatUser.create_key(user_id))
                rt_user.email = user_email.email()
                rt_user.name = '%s %s' % (notification.firstName, notification.lastName)
                rt_user.app_id = app_id
                rt_user.put()

    result_xml = _execute_gv_request(integration_settings.data, '/cases/' + notification.caseReference, urlfetch.GET)
    elements = etree.XML(result_xml)  # type: Element
    creation_date = parse_date(elements.findtext('date_created')).replace(tzinfo=None)
    incident = Incident(key=Incident.create_key(str(uuid4())))
    incident.set_status(IncidentStatus.NEW, creation_date)
    incident.integration_id = integration_settings.id
    incident.user_id = user_id
    incident.cleanup_date = None
    incident.source = 'web'
    incident.visible = False
    incident.user_consent = False
    incident.external_id = notification.caseReference
    incident.details = _get_incident_details_from_xml(elements)
    integration_params = IntegrationParamsGreenValley()
    integration_params.notification_ids = []
    incident.integration_params = integration_params
    sent_date = parse_date(notification.sentDate).replace(tzinfo=None)
    incident.set_status(IncidentStatus.IN_PROGRESS, sent_date)
    return incident


def _get_incident_details_from_xml(elements):
    # type: (Element) -> IncidentDetails
    details = IncidentDetails()
    # TODO: actually implement this method when needed & migrate existing incidents
    return details


def get_app_user_from_oca_context(context):
    # type: (str) -> Optional[users.User]
    base_url = get_config(ROGERTHAT_NAMESPACE).rogerthat_server_url
    url = base_url + '/mobi/rest/user/context/' + context
    result = urlfetch.fetch(url)  # type: urlfetch._URLFetchResult
    if result.status_code == 200:
        data = json.loads(result.content)
        return users.User(data['id'])
    if result.status_code != 404:
        logging.debug('%s: %s', result.status_code, result.content)
        raise Exception('Unexpected status code %s for context request' % result.status_code)
    return None


def create_app_user_by_email(human_user_email, app_id=None):
    azzert('/' not in human_user_email, 'human_user_email should not contain /')
    azzert(':' not in human_user_email, 'human_user_email should not contain :')
    if app_id is None:
        app_id = 'rogerthat'
    else:
        azzert(app_id, 'app_id should not be empty')
    if app_id != 'rogerthat':
        return users.User('%s:%s' % (human_user_email, app_id))
    return users.User(human_user_email)


def get_app_user_tuple_by_email(app_user_email):
    azzert('/' not in app_user_email, "app_user_email should not contain /")
    if ':' in app_user_email:
        human_user_email, app_id = app_user_email.split(':')
    else:
        human_user_email, app_id = app_user_email, 'rogerthat'
    return users.User(human_user_email), app_id
