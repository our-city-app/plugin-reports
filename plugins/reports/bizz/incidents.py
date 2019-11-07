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
from datetime import datetime
from uuid import uuid4

from google.appengine.ext import ndb

from dateutil.parser import parse as parse_date
from framework.bizz.job import run_job, MODE_BATCH
from framework.utils import try_or_defer
from mcfw.exceptions import HttpBadRequestException
from mcfw.rpc import parse_complex_value
from plugins.reports.bizz.elasticsearch import re_index_incidents, re_index_incident
from plugins.reports.dal import save_rogerthat_user, get_rogerthat_user, get_integration_settings
from plugins.reports.integrations.int_3p import create_incident as create_3p_incident
from plugins.reports.integrations.int_green_valley.green_valley import create_incident as create_gv_incident
from plugins.reports.integrations.int_topdesk import create_incident as create_topdesk_incident
from plugins.reports.models import Incident, IntegrationProvider, IncidentParamsFlow, IncidentParamsForm, \
    FormIntegration, GreenValleyFormConfiguration, IncidentStatus
from plugins.reports.to import FormSubmittedCallback
from plugins.rogerthat_api.to.messaging.flow import FLOW_STEP_TO
from typing import List, Tuple


def cleanup_timed_out():
    run_job(cleanup_timed_out_query, [], cleanup_timed_out_worker, [], mode=MODE_BATCH, batch_size=25)


def cleanup_timed_out_query():
    return Incident.list_by_cleanup_date(datetime.utcnow())


@ndb.transactional(xg=True)
def cleanup_timed_out_worker(incident_keys):
    incidents = ndb.get_multi(incident_keys)  # type: List[Incident]
    for incident in incidents:
        incident.visible = False
        incident.cleanup_date = None
    re_index_incidents(incidents)
    ndb.put_multi(incidents)


def process_incident(integration_id, user_details, parent_message_key, steps, timestamp):
    rt_user = save_rogerthat_user(user_details[0])
    incident_id = str(uuid4())
    try_or_defer(_create_incident, incident_id, integration_id, rt_user.user_id, parent_message_key, timestamp, steps)


def _create_incident(incident_id, integration_id, user_id, parent_message_key, timestamp, steps):
    logging.debug("_create_incident for user %s", user_id)
    rt_user = get_rogerthat_user(user_id)
    if not rt_user:
        logging.error('Could not find user with id %s', user_id)
        return

    settings = get_integration_settings(integration_id)
    parsed_steps = parse_complex_value(FLOW_STEP_TO, steps, True)

    incident = Incident(key=Incident.create_key(incident_id))
    incident.status = IncidentStatus.NEW
    incident.integration_id = settings.id
    incident.user_id = user_id
    incident.report_date = datetime.utcfromtimestamp(timestamp)
    incident.cleanup_date = None
    incident.integration = settings.integration
    incident.source = 'app'
    params = IncidentParamsFlow()
    params.parent_message_key = parent_message_key
    params.steps = parsed_steps
    incident.params = params

    if settings.integration == IntegrationProvider.TOPDESK:
        create_topdesk_incident(settings, rt_user, incident, parsed_steps)
    elif settings.integration == IntegrationProvider.THREE_P:
        create_3p_incident(settings, rt_user, incident, parsed_steps)
    else:
        raise Exception('Unknown integration: %s' % settings.integration)
    incident.visible = incident.can_show_on_map
    incident.put()
    try_or_defer(re_index_incident, incident)


def list_incidents(integration_id, page_size, status, cursor=None):
    # type: (int, int, str, str) -> Tuple[List[Incident], ndb.Cursor, bool]
    return Incident.list_by_integration_id_and_status(integration_id, status).fetch_page(page_size, start_cursor=cursor)


def create_incident_from_form(integration_id, data):
    # type: (int, FormSubmittedCallback) -> str
    rt_user = save_rogerthat_user(data.user_details)
    settings = get_integration_settings(integration_id)
    form_configuration = FormIntegration.create_key(data.form.id).get()  # type: FormIntegration
    if not settings:
        raise HttpBadRequestException('Could not find integration settings for %s' % integration_id)
    date = parse_date(data.submission.submitted_date).replace(tzinfo=None)
    incident = Incident(key=Incident.create_key(str(uuid4())))
    incident.status = IncidentStatus.NEW
    incident.integration_id = integration_id
    incident.user_id = rt_user.user_id
    incident.report_date = date
    incident.cleanup_date = None
    incident.integration = integration_id
    incident.source = 'app'
    params = IncidentParamsForm()
    params.submission_id = data.submission.id
    incident.params = params

    integration = get_integration_settings(integration_id)
    if isinstance(form_configuration.config, GreenValleyFormConfiguration):
        created = create_gv_incident(integration.data, form_configuration.config, data.submission, data.form, incident)
    else:
        raise HttpBadRequestException()
    if created:
        incident.visible = incident.can_show_on_map
        incident.put()
        try_or_defer(re_index_incident, incident)
        return incident.id
    return None
