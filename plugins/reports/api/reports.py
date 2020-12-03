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
import logging
from collections import defaultdict

from dateutil import parser
from mcfw.exceptions import HttpForbiddenException, HttpNotFoundException, HttpBadRequestException
from mcfw.restapi import rest, GenericRESTRequestHandler
from mcfw.rpc import returns, arguments
from plugins.reports.bizz.incident_statistics import get_all_incident_statistics, get_incident_statistics
from plugins.reports.bizz.incidents import list_incidents, create_incident_from_form
from plugins.reports.dal import get_consumer, get_incident, update_incident
from plugins.reports.integrations.int_topdesk.topdesk import topdesk_integration_call
from plugins.reports.models import FormIntegration, SaveFormIntegrationTO, IncidentStatus
from plugins.reports.to import IncidentListTO, IncidentTO, FormSubmittedCallback


def get_auth_header():
    return GenericRESTRequestHandler.get_current_request().headers.get('Authorization')


def validate_request(f, handler):
    consumer_key = handler.request.headers.get('Authorization', None)
    return get_consumer(consumer_key) is not None


def _get_consumer():
    consumer_id = get_auth_header()
    if not consumer_id:
        raise HttpForbiddenException()
    consumer = get_consumer(consumer_id)
    if not consumer:
        raise HttpForbiddenException()
    return consumer


@rest('/incidents/integrations/form', 'put', silent_result=True)
@returns(dict)
@arguments(data=SaveFormIntegrationTO)
def api_save_form_settings(data):
    # type: (SaveFormIntegrationTO) -> dict
    consumer = _get_consumer()
    key = FormIntegration.create_key(data.form_id)
    form_integration = key.get() or FormIntegration(key=key)
    form_integration.config = data.config
    form_integration.integration_id = consumer.integration_id
    form_integration.put()
    return form_integration.to_dict()


@rest('/incidents', 'get', silent_result=True)
@returns(IncidentListTO)
@arguments(status=unicode, cursor=unicode)
def api_get_incidents(status=None, cursor=None):
    consumer = _get_consumer()
    if status not in IncidentStatus.all():
        raise HttpBadRequestException('Invalid status', {'allowed_statuses': IncidentStatus.all()})
    results, cursor, more = list_incidents(consumer.integration_id, 50, status=status, cursor=cursor)
    return IncidentListTO(cursor and cursor.to_websafe_string(), more, [IncidentTO.from_model(i) for i in results])


@rest('/incident-statistics/details', 'get', silent_result=True)
@returns([dict])
@arguments(date=[unicode])
def api_get_incident_statistics(date=None):
    if date is None:
        date = []
    consumer = _get_consumer()
    dates = []
    for d in date:
        try:
            dates.append(parser.parse(d))
        except (ValueError, OverflowError):
            logging.debug('Ignoring invalid date: %s', d)
    return get_incident_statistics(consumer.integration_id, dates)


@rest('/incident-statistics', 'get', silent_result=True)
@returns(dict)
@arguments()
def api_list_incident_statistics():
    consumer = _get_consumer()
    return get_all_incident_statistics(consumer.integration_id)


@rest('/incidents/<incident_id:[^/]+>', 'get', silent_result=True)
@returns(IncidentTO)
@arguments(incident_id=unicode)
def api_get_incident(incident_id):
    incident = get_incident(incident_id)
    if not incident:
        raise HttpNotFoundException('incident_not_found')
    consumer = _get_consumer()
    if incident.integration_id != consumer.integration_id:
        raise HttpForbiddenException()
    return IncidentTO.from_model(incident)


@rest('/incidents/<incident_id:[^/]+>', 'put', silent_result=True)
@returns(IncidentTO)
@arguments(incident_id=unicode, data=IncidentTO)
def api_save_incident(incident_id, data):
    incident = get_incident(incident_id)
    if not incident:
        raise HttpNotFoundException()
    consumer = _get_consumer()
    if incident.integration_id != consumer.integration_id:
        raise HttpForbiddenException()
    return IncidentTO.from_model(update_incident(incident, data))


@rest('/callbacks/form/<form_id:[^/]+>', 'post', silent_result=True)
@returns(dict)
@arguments(form_id=(int, long), data=FormSubmittedCallback)
def api_form_callback(form_id, data):
    # type: (int, FormSubmittedCallback) -> str
    consumer = _get_consumer()
    return {'external_reference': create_incident_from_form(consumer.integration_id, data)}


@rest('/integrations/topdesk/categories', 'get', silent_result=True)
@returns([dict])
@arguments()
def api_get_topdesk_categories():
    return topdesk_integration_call(_get_consumer().integration_id, '/incidents/categories')


@rest('/integrations/topdesk/subcategories', 'get', silent_result=True)
@returns([dict])
@arguments()
def api_get_topdesk_subcategories():
    data = topdesk_integration_call(_get_consumer().integration_id, '/incidents/subcategories')
    # Convert from flat list with duplicated category info to list of categories with subcategories
    per_category = defaultdict(list)
    categories = {entry['category']['id']: entry['category']['name'] for entry in data}
    for entry in data:
        per_category[entry['category']['id']].append({'id': entry['id'], 'name': entry['name']})
    return [{'id': category_id, 'name': categories[category_id], 'subcategories': subcategories}
            for category_id, subcategories in per_category.iteritems()]
