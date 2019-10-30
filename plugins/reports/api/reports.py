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

from mcfw.exceptions import HttpForbiddenException
from mcfw.restapi import rest, GenericRESTRequestHandler
from mcfw.rpc import returns, arguments
from plugins.reports.bizz.incidents import list_incidents
from plugins.reports.dal import get_consumer, get_incident, update_incident
from plugins.reports.to import IncidentListTO, IncidentTO


def get_sik():
    return GenericRESTRequestHandler.get_current_request().headers.get('Authorization')


def validate_request(f, handler):
    consumer_key = handler.request.headers.get('Authorization', None)
    return get_consumer(consumer_key) is not None


@rest('/incidents', 'get', silent_result=True)
@returns(IncidentListTO)
@arguments()
def api_get_incidents():
    sik = get_sik()
    if not sik:
        raise HttpForbiddenException()
    results, cursor, more = list_incidents(sik, 50)
    return IncidentListTO(cursor and cursor.to_websafe_string(), more, [IncidentTO.from_model(i) for i in results])


@rest('/incidents/<incident_id:[^/]+>', 'get', silent_result=True)
@returns(IncidentTO)
@arguments(incident_id=unicode)
def api_get_incident(incident_id):
    incident = get_incident(incident_id)
    sik = get_sik()
    if not sik or (incident and incident.sik != sik):
        raise HttpForbiddenException()
    return IncidentTO.from_model(incident)


@rest('/incidents/<incident_id:[^/]+>', 'put', silent_result=True)
@returns(IncidentTO)
@arguments(incident_id=unicode, data=IncidentTO)
def api_save_incident(incident_id, data):
    incident = get_incident(incident_id)
    sik = get_sik()
    if not sik or (incident and incident.sik != sik):
        raise HttpForbiddenException()
    return IncidentTO.from_model(update_incident(incident, data))
