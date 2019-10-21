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

from framework.bizz.job import run_job, MODE_BATCH
from framework.utils import try_or_defer
from mcfw.rpc import parse_complex_value
from plugins.reports.bizz.elasticsearch import re_index_incidents
from plugins.reports.dal import save_rogerthat_user, get_rogerthat_user, get_integration_settings
from plugins.reports.integrations.int_3p import create_incident as create_3p_incident
from plugins.reports.integrations.int_topdesk import create_incident as create_topdesk_incident
from plugins.reports.models import Incident, IntegrationProvider, IncidentSource, IncidentParamsFlow
from plugins.rogerthat_api.to.messaging.flow import FLOW_STEP_TO


def cleanup_timed_out():
    run_job(cleanup_timed_out_query, [], cleanup_timed_out_worker, [], mode=MODE_BATCH, batch_size=25)


def cleanup_timed_out_query():
    return Incident.list_by_cleanup_date(datetime.utcnow())


# TODO what is the use of this? cleanup_date is always None
@ndb.transactional(xg=True)
def cleanup_timed_out_worker(incident_keys):
    incidents = ndb.get_multi(incident_keys)  # type: list[Incident]
    for incident in incidents:
        incident.cleanup_date = None
    re_index_incidents(incidents)
    ndb.put_multi(incidents)


def process_incident(sik, user_details, parent_message_key, steps, timestamp):
    rt_user = save_rogerthat_user(user_details[0])
    incident_id = str(uuid4())
    try_or_defer(_create_incident, incident_id, sik, rt_user.user_id, parent_message_key, timestamp, steps)


def _create_incident(incident_id, sik, user_id, parent_message_key, timestamp, steps):
    logging.debug("_create_incident for user %s", user_id)
    rt_user = get_rogerthat_user(user_id)
    if not rt_user:
        logging.error('Could not find user with id %s' % (user_id))
        return

    settings = get_integration_settings(sik)
    if not settings:
        logging.error('Could not find integration settings for %s', sik)
        return
    parsed_steps = parse_complex_value(FLOW_STEP_TO, steps, True)

    incident = Incident(key=Incident.create_key(incident_id))
    incident.sik = sik
    incident.user_id = user_id
    incident.report_date = datetime.utcfromtimestamp(timestamp)
    incident.cleanup_date = None
    incident.integration = settings.integration
    incident.source = IncidentSource.APP
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
    incident.put()
    try_or_defer(re_index_incidents, [incident])
