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
import logging
from collections import defaultdict
from datetime import datetime

from google.appengine.ext import ndb

from dateutil.relativedelta import relativedelta
from framework.bizz.job import run_job
from framework.utils.cloud_tasks import schedule_tasks, create_task
from plugins.reports.integrations.int_topdesk import refresh_topdesk_tags
from plugins.reports.models import Incident, IncidentStatus, IntegrationSettings, IntegrationProvider
from plugins.reports.models.incident_statistics import IncidentStatistics, IncidentTagMapping
from typing import List, Dict


def build_monthly_incident_statistics(date):
    run_job(_list_all_integrations, [], build_statistics, [date.year, date.month])


def _list_all_integrations():
    return IntegrationSettings.query()


def rebuild_all_statistics():
    ndb.delete_multi(IncidentStatistics.query().fetch(keys_only=True))
    oldest = Incident.get_oldest()  # type: Incident
    date = oldest.report_date  # type: datetime
    date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_date = datetime.now()
    while date < current_date:
        run_job(_list_all_integrations, [], build_statistics, [date.year, date.month])
        date += relativedelta(months=1)
    refresh_all_tags()


def build_statistics(integration_key, year, month):
    integration_id = integration_key.id()
    logging.info('Building incident statistics for integration %s -> %s-%s', integration_id, year, month)
    min_date = datetime(year, month, 1)
    max_date = min_date + relativedelta(months=1)
    keys = set()
    # List incidents reported this month
    keys.update(Incident.list_by_integration_and_report_date(integration_id, min_date, max_date).fetch(keys_only=True))
    # List incidents resolved this month
    keys.update(Incident.list_between_resolve_date(integration_id, min_date, max_date).fetch(keys_only=True))
    # List all incidents that haven't been resolved yet (the "in progress" ones)
    keys.update(Incident.list_without_resolve_date(integration_id).fetch(keys_only=True))
    incidents = ndb.get_multi(keys)  # type: List[Incident]
    data = []

    for incident in incidents:
        if incident.details.geo_location:
            location = [incident.details.geo_location.lat, incident.details.geo_location.lon]
        else:
            location = []
        tags = [tag.to_string() for tag in incident.tags]
        statuses = []
        for status_date in incident.status_dates:
            if status_date.date.year == year and status_date.date.month == month:
                status = status_date.status
                # Ensures every status can only appear once in the list, with the last element in the list
                # being the current status of the incident.
                # For example, incident status goes from created -> in_progress -> resolved -> in_progress
                if status in statuses:
                    statuses.remove(status)
                statuses.append(status)
        if len(statuses) == 0:
            if min_date > incident.report_date:
                statuses = [IncidentStatus.IN_PROGRESS]
            else:
                # No status updates this month - skip this incident
                continue
        data.append([incident.id, statuses, tags, location])
    if data:
        stats = IncidentStatistics(key=IncidentStatistics.create_key(integration_id, year, month))
        stats.integration_id = integration_id
        stats.data = data
        stats.put()
        return stats


def get_all_incident_statistics(integration_id):
    qry = IncidentStatistics.list_by_integration(integration_id).fetch(None, keys_only=True)
    tag_mapping = IncidentTagMapping.create_key(integration_id).get()  # type: IncidentTagMapping
    year_mapping = defaultdict(list)
    for result in qry:
        _, year, month = map(int, result.id().split('-'))
        year_mapping[year].append(month)
    results = sorted([{'year': year, 'months': sorted(months, reverse=True)}
                      for year, months in year_mapping.iteritems()],
                     cmp=lambda year1, year2: year2['year'] - year1['year'])
    return {
        'results': results,
        'categories': [c.to_dict() for c in tag_mapping.categories],
        'subcategories': [c.to_dict() for c in tag_mapping.subcategories],
    }


def get_incident_statistics(integration_id, dates):
    # type: (int, List[datetime]) -> List[Dict]
    keys = [IncidentStatistics.create_key(integration_id, date.year, date.month) for date in dates]
    models = ndb.get_multi(keys)  # type: List[IncidentStatistics]
    return [{'year': date.year, 'month': date.month, 'data': model.data if model else []}
            for date, model in zip(dates, models)]


def refresh_all_tags():
    tasks = [create_task(refresh_topdesk_tags, p) for p in
             IntegrationSettings.list_by_integration(IntegrationProvider.TOPDESK).iter(keys_only=True)]
    return schedule_tasks(tasks)
