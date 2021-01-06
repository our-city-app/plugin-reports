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
from __future__ import unicode_literals
import logging
import urllib
from urlparse import urlparse, parse_qs
from uuid import uuid4

from google.appengine.ext import ndb

import dateutil
from framework.utils import try_or_defer, guid
from mcfw.consts import MISSING
from plugins.reports.bizz.elasticsearch import re_index_incident
from plugins.reports.bizz.rogerthat import send_rogerthat_message
from plugins.reports.consts import IncidentTagType
from plugins.reports.dal import get_integration_settings, get_rogerthat_user, get_incident_by_external_id
from plugins.reports.integrations.int_green_valley.notifications import html_to_markdown
from plugins.reports.integrations.int_topdesk.consts import TopdeskFieldMappingType
from plugins.reports.integrations.int_topdesk.topdesk import topdesk_api_call
from plugins.reports.models import IdName, IncidentParamsFlow, IntegrationParamsTopdesk, TopdeskSettings, \
    IncidentDetails, Incident, IncidentStatus, IncidentTag, IncidentParamsForm
from plugins.rogerthat_api.to import MemberTO


def incident_feedback(integration_id, incident_id, message):
    # type: (int, str, str) -> None
    logging.debug('Received incident feedback: %s', incident_id)
    settings = get_integration_settings(integration_id)
    if not settings:
        logging.error('Could not find topdesk settings for %s', integration_id)
        return

    topdesk_settings = settings.data  # type: TopdeskSettings
    if len(incident_id) == 36:
        # uuid -> get by id
        response = topdesk_api_call(topdesk_settings, '/api/incidents/id/%s' % incident_id)
    else:
        # case number -> get by number
        urlencoded = urllib.quote(incident_id)
        response = topdesk_api_call(topdesk_settings, '/api/incidents/number/%s' % urlencoded)
    logging.debug("Incident result from server: %s", response)

    incident = create_or_update_incident_from_topdesk(integration_id, topdesk_settings, response)

    message_lines = ['Uw melding is geüpdatet.']
    if incident.source == 'app':
        params = incident.integration_params  # type: IntegrationParamsTopdesk
        status = response['processingStatus']
        if params.status.id != status['id']:
            params.status = IdName.from_dict(status)
            message_lines.append('De huidige status van uw melding is nu "%s"' % params.status.name)
        if message and params.last_message != message:
            params.last_message = message
            message_lines.append(message)
    incident.put()
    try_or_defer(re_index_incident, incident)

    if incident.source == 'app':
        if len(message_lines) == 1:
            logging.info('Not sending update message to user since nothing has been updated')
        else:
            rt_user = get_rogerthat_user(incident.user_id)
            member = MemberTO(member=rt_user.email, app_id=rt_user.app_id, alert_flags=2)
            complete_message = '\n'.join(message_lines)
            if isinstance(incident.params, (IncidentParamsFlow, IncidentParamsForm)):
                try_or_defer(send_rogerthat_message, settings.sik, member, complete_message,
                             parent_message_key=incident.params.parent_message_key, json_rpc_id=guid())
            else:
                raise Exception('Can\'t process incident feedback with invalid params: %s', incident.params)


def create_or_update_incident_from_topdesk(integration_id, topdesk_settings, topdesk_incident):
    # type: (int, TopdeskSettings, dict) -> Incident
    external_id = topdesk_incident['number']
    incident = get_incident_by_external_id(integration_id, external_id)

    if not incident:
        logging.debug('Creating new incident %s', external_id)
        incident = create_incident_from_topdesk(integration_id, topdesk_incident)
    set_incident_info(topdesk_incident, incident, topdesk_settings)
    return incident


def create_incident_from_topdesk(integration_id, topdesk_incident):
    # type: (int, str) -> Incident
    details = IncidentDetails()
    details.title = topdesk_incident['briefDescription']
    # Remove date and name from request
    request = topdesk_incident['request']
    if request:
        request = request.split(': \n', 1)[1]
        details.description = html_to_markdown(request)
    incident = Incident(key=Incident.create_key(str(uuid4())))
    incident.details = details
    incident.integration_id = integration_id
    incident.source = 'web'
    incident.user_consent = False
    incident.external_id = topdesk_incident['number']
    incident.integration_params = IntegrationParamsTopdesk()
    incident.integration_params.id = topdesk_incident['id']
    incident.integration_params.status = IdName.from_dict(topdesk_incident['processingStatus'])
    incident.visible = incident.can_show_on_map  # always false since no consent could be given
    report_date = _parse_date(topdesk_incident['creationDate'])
    incident.set_status(IncidentStatus.NEW, report_date)
    return incident


def set_incident_info(topdesk_incident, incident, topdesk_settings):
    # type: (dict, Incident, TopdeskSettings) -> Incident
    statuses = {s.status for s in incident.status_dates}
    if IncidentStatus.IN_PROGRESS not in statuses:
        incident.set_status(IncidentStatus.IN_PROGRESS, incident.report_date)
    closed_date = _parse_date(topdesk_incident['closedDate'])
    if topdesk_incident['closed']:
        incident.set_status(IncidentStatus.RESOLVED, closed_date)
    tags = []
    category_id = topdesk_incident[IncidentTagType.CATEGORY].get('id')
    if category_id:
        incident.tags.append(IncidentTag(type=IncidentTagType.CATEGORY, id=category_id))
    subcategory_id = topdesk_incident[IncidentTagType.SUB_CATEGORY].get('id')
    if subcategory_id:
        incident.tags.append(IncidentTag(type=IncidentTagType.SUB_CATEGORY, id=subcategory_id))
    if topdesk_settings.report_settings and topdesk_settings.report_settings is not MISSING:
        # TODO: I'm not actually sure what the point of this is
        for field in topdesk_settings.report_settings.type_fields:
            value = topdesk_incident[field.property]
            if value:
                tags.append(IncidentTag(type=field.property, id=value['id']))
    incident.tags = tags
    location_from_topdesk = _get_geo_location_from_topdesk_incident(topdesk_settings, topdesk_incident)
    if location_from_topdesk:
        incident.details.geo_location = location_from_topdesk
    return incident


def _parse_date(date):
    return dateutil.parser.parse(date).replace(tzinfo=None) if date else None


def _get_geo_location_from_topdesk_incident(topdesk_settings, topdesk_incident):
    # type: (TopdeskSettings, dict) -> Optional[ndb.GeoPt]
    for mapping in topdesk_settings.field_mapping:
        try:
            if mapping.type == TopdeskFieldMappingType.GPS_DUAL_FIELD:
                lat_prop, lon_prop = mapping.value_properties[0], mapping.value_properties[1]
                lat = topdesk_incident[mapping.property][lat_prop].strip()
                lon = topdesk_incident[mapping.property][lon_prop].strip()
                if lat and lon:
                    return ndb.GeoPt(lat, lon)
            elif mapping.type == TopdeskFieldMappingType.GPS_SINGLE_FIELD:
                value = topdesk_incident[mapping.property][mapping.value_properties[0]].strip()
                if value:
                    return ndb.GeoPt(value)
            elif mapping.type == TopdeskFieldMappingType.GPS_URL:
                value = topdesk_incident[mapping.property][mapping.value_properties[0]]
                parsed_url = urlparse(value)
                query_params = parse_qs(parsed_url)
                query = query_params.get('query').strip()
                if query:
                    return ndb.GeoPt(query)
        except Exception as e:
            logging.info('Could not convert value of field %s.%s to gps location: %s', mapping.property,
                         mapping.value_properties[0], e.message)
            raise e
    return None
