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

from google.appengine.api.taskqueue import MAX_TASKS_PER_ADD

from framework.bizz.job import run_job
from framework.consts import HIGH_LOAD_WORKER_QUEUE
from framework.utils.cloud_tasks import create_task, schedule_tasks
from plugins.reports.integrations.int_topdesk import topdesk_api_call
from plugins.reports.integrations.int_topdesk.feedback import create_or_update_incident_from_topdesk
from plugins.reports.models import IntegrationSettings, IntegrationProvider


def migrate():
    run_job(_get_integrations, [], import_incidents, [])


def _get_integrations():
    return IntegrationSettings.list_by_integration(IntegrationProvider.TOPDESK)


def import_incidents(integration_key):
    settings = integration_key.get()  # type: IntegrationSettings
    offset = 0
    page_size = MAX_TASKS_PER_ADD
    has_more = True
    while has_more:
        incidents = topdesk_api_call(settings.data, '/api/incidents?page_size=%s&start=%s' % (page_size, offset))
        if not incidents:
            break
        has_more = len(incidents) == page_size
        offset += page_size
        tasks = [create_task(_create_incident, settings.id, incident) for incident in incidents]
        schedule_tasks(tasks, HIGH_LOAD_WORKER_QUEUE)


def _create_incident(integration_id, topdesk_incident):
    settings = IntegrationSettings.create_key(integration_id).get()  # type: IntegrationSettings
    incident = create_or_update_incident_from_topdesk(settings.id, settings.data, topdesk_incident)
    incident.put()
    # Indexing the incident is not needed as user_consent will always be false
