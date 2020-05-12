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
from datetime import datetime, date

from google.appengine.ext import ndb, deferred

from dateutil.relativedelta import relativedelta
from framework.bizz.job import run_job
from framework.i18n_utils import translate
from plugins.reports.models import IncidentVote, UserIncidentVote, Incident, IncidentStatus, \
    IncidentStatisticsYear, IncidentStatisticsMonth, IntegrationSettings
from plugins.reports.to import MapItemDetailsTO, TextSectionTO, VoteSectionTO, \
    MapItemTO, GeoPointTO, MapIconTO, MapVoteOptionTO

ICON_MAPPING = {
    IncidentStatus.NEW: ('new', '#f10812'),
    IncidentStatus.IN_PROGRESS: ('inprogress', '#eeb309'),
    IncidentStatus.RESOLVED: ('resolved', '#a4c14d'),
}


@ndb.transactional(xg=True)
def update_incident_vote(incident_id, user_id, vote_id, to_option_id):
    vote_key = IncidentVote.create_key(incident_id)
    user_vote_key = UserIncidentVote.create_key(user_id, incident_id)
    vote, user_vote = ndb.get_multi((vote_key, user_vote_key))

    from_option_id = None
    save_vote = True
    if user_vote:
        from_option_id = user_vote.option_id
        # Pressed same option -> remove vote
        if from_option_id == to_option_id:
            user_vote_key.delete()
            user_vote = None
            save_vote = False
    else:
        user_vote = UserIncidentVote(key=user_vote_key)
    if save_vote:
        user_vote.incident_id = incident_id
        user_vote.option_id = to_option_id
        user_vote.put()

    if not vote:
        vote = IncidentVote(key=vote_key)

    changed = False
    if from_option_id == IncidentVote.NEGATIVE:
        vote.negative_count -= 1
        changed = True
    if from_option_id == IncidentVote.POSITIVE:
        vote.positive_count -= 1
        changed = True

    if from_option_id == to_option_id:
        pass
    elif IncidentVote.NEGATIVE == to_option_id:
        vote.negative_count += 1
        changed = True
    elif IncidentVote.POSITIVE == to_option_id:
        vote.positive_count += 1
        changed = True

    if changed:
        vote.put()

    return vote, user_vote


def get_vote_options(vote, user_vote, language):
    if not vote:
        vote = IncidentVote()
    if not user_vote:
        user_vote = UserIncidentVote()
    return [
        MapVoteOptionTO(id=IncidentVote.POSITIVE,
                        icon=u'fa-thumbs-o-up',
                        title=translate(language, 'r', 'resolved'),
                        count=vote.positive_count,
                        color=u'#87CD03',
                        selected=user_vote.option_id == IncidentVote.POSITIVE),
        MapVoteOptionTO(id=IncidentVote.NEGATIVE,
                        icon=u'fa-eye',
                        title=translate(language, 'r', 'also_report_this'),
                        count=vote.negative_count,
                        color=u'#FE6B00',
                        selected=user_vote.option_id == IncidentVote.NEGATIVE)
    ]


def convert_to_item_to(incident):
    # type: (Incident) -> MapItemTO
    icon_id, icon_color = ICON_MAPPING.get(incident.status, IncidentStatus.NEW)

    return MapItemTO(id=incident.id,
                     coords=GeoPointTO(lat=incident.details.geo_location.lat,
                                       lon=incident.details.geo_location.lon),
                     icon=MapIconTO(id=icon_id,
                                    color=icon_color),
                     title=incident.details.title,
                     description=incident.details.description)


def convert_to_item_details_to(incident, vote, user_vote, language):
    # type: (Incident, IncidentVote, UserIncidentVote, unicode) -> MapItemDetailsTO
    item = MapItemDetailsTO(id=incident.id,
                            geometry=[],
                            sections=[
                                TextSectionTO(title=incident.details.title,
                                              description=incident.details.description),
                            ])
    if vote:
        item.sections.append(VoteSectionTO(id=u'vote1', options=get_vote_options(vote, user_vote, language)))
    return item


def re_count_incidents():
    run_job(_re_count_incidents_query, [], _re_count_incidents_worker, [])


def _re_count_incidents_query():
    return IntegrationSettings.query()


def _re_count_incidents_worker(key):
    settings = key.get()  # type: IntegrationSettings
    if not settings.app_id:
        logging.error('Cannot build statistics, app id not set on integration settings "%s"(%s)', settings.name,
                      settings.id)
    else:
        re_count_incidents_app(settings)


def re_count_incidents_app(integration_settings):
    # type: (IntegrationSettings) -> None
    today = date.today()
    yesterday = today - relativedelta(days=1)

    if today.year != yesterday.year:
        re_count_incidents_month(integration_settings.id, integration_settings.app_id, yesterday.year, yesterday.month)
        deferred.defer(re_count_incidents_year, integration_settings.app_id, yesterday.year,
                       _countdown=5)
    elif today.month != yesterday.month:
        re_count_incidents_month(integration_settings.id, integration_settings.app_id, yesterday.year, yesterday.month)

    re_count_incidents_month(integration_settings.id, integration_settings.app_id, today.year, today.month)
    deferred.defer(re_count_incidents_year, integration_settings.app_id, today.year,
                   _countdown=5)


def re_count_incidents_month(integration_id, app_id, year, month):
    first_day_of_month = datetime(year, month, 1)
    next_month = datetime(year, month, 1) + relativedelta(months=1)
    resolved_count = Incident.list_by_integration_status_and_date(integration_id,
                                                                  IncidentStatus.RESOLVED,
                                                                  first_day_of_month,
                                                                  next_month).count()

    IncidentStatisticsMonth(key=IncidentStatisticsMonth.create_key(app_id, year, month),
                            app_id=app_id,
                            year=year,
                            month=month,
                            resolved_count=resolved_count).put()


def re_count_incidents_year(app_id, year):
    resolved_count = 0
    for s in IncidentStatisticsMonth.list_by_app_and_year(app_id, year):
        resolved_count += s.resolved_count

    IncidentStatisticsYear(key=IncidentStatisticsYear.create_key(app_id, year),
                           app_id=app_id,
                           year=year,
                           resolved_count=resolved_count).put()
