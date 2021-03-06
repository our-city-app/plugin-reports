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
from datetime import date

from google.appengine.ext import ndb
from typing import List

from plugins.reports.bizz import update_incident_vote, get_vote_options, convert_to_item_details_to
from plugins.reports.bizz.elasticsearch import search_current
from plugins.reports.models import Incident, UserIncidentVote, IncidentStatus, ReportsFilter, IncidentVote, \
    IncidentStatisticsYear, UserIncidentAnnouncement
from plugins.reports.to import GetMapItemsResponseTO, GetMapItemDetailsResponseTO, SaveMapItemVoteResponseTO, \
    TextSectionTO, TextAnnouncementTO
from plugins.reports.utils import get_app_id_from_user_id


def convert_filter_to_status(filter_value):
    mapping = {
        # ReportsFilter is defined in rogerthat.bizz.maps.reports.ReportsFilter
        ReportsFilter.ALL: None,
        ReportsFilter.NEW: IncidentStatus.NEW,
        ReportsFilter.IN_PROGRESS: IncidentStatus.IN_PROGRESS,
        ReportsFilter.RESOLVED: IncidentStatus.RESOLVED,
    }
    return mapping.get(filter_value, IncidentStatus.NEW)


def get_report_map_announcement(user_id):
    today = date.today()
    user_incident_announcement_key = UserIncidentAnnouncement.create_key(user_id, today.year, today.month)
    if user_incident_announcement_key.get():
        return None

    UserIncidentAnnouncement(key=user_incident_announcement_key).put()

    app_id = get_app_id_from_user_id(user_id)
    s = IncidentStatisticsYear.create_key(app_id, today.year).get()
    if not s:
        return None
    if s.resolved_count < 2:
        return None
    # todo translate
    return TextAnnouncementTO(title=u'Opgeloste meldingen',
                              description=u'Dit jaar zijn er al %s meldingen opgelost.' % s.resolved_count)


def get_report_map_items(user_id, lat, lon, distance, status, limit, cursor):
    # type: (str, float, float, int, str, int, str) -> GetMapItemsResponseTO
    if lat and lon and distance and status and limit:
        if limit > 1000:
            limit = 1000
    else:
        logging.debug('not all parameters where provided')
        return GetMapItemsResponseTO()
    status = convert_filter_to_status(status)
    items, new_cursor = search_current(lat, lon, distance, status, cursor, limit)
    top_sections = []
    if status == IncidentStatus.RESOLVED and cursor is None:
        top_sections = get_top_sections_resolved(user_id)
    return GetMapItemsResponseTO(cursor=new_cursor,
                                 items=items,
                                 distance=distance,
                                 top_sections=top_sections)


def get_reports_map_item_details(user_id, ids, language):
    # type: (list[unicode], unicode, unicode) -> GetMapItemDetailsResponseTO
    if not ids or not user_id:
        return GetMapItemDetailsResponseTO()
    incidents = ndb.get_multi([Incident.create_key(uid) for uid in ids])  # type: List[Incident]
    extra_keys = [IncidentVote.create_key(incident.id) for incident in incidents if incident.can_show_votes] + \
                 [UserIncidentVote.create_key(user_id, incident.id) for incident in incidents if
                  incident.can_show_votes]
    extra_models = ndb.get_multi(extra_keys)
    vote_mapping = {}
    user_vote_mapping = {}
    for model in extra_models:
        if isinstance(model, IncidentVote):
            vote_mapping[model.incident_id] = model
        elif isinstance(model, UserIncidentVote):
            user_vote_mapping[model.incident_id] = model
    items = []
    for incident in incidents:
        vote = vote_mapping.get(incident.id)
        if not vote and incident.can_show_votes:
            vote = IncidentVote(key=IncidentVote.create_key(incident.id))
        items.append(convert_to_item_details_to(incident, vote, user_vote_mapping.get(incident.id), language))
    return GetMapItemDetailsResponseTO(items=items)


def vote_report_item(item_id, user_id, vote_id, option_id, language):
    # type: (unicode, unicode, unicode, unicode, unicode) -> SaveMapItemVoteResponseTO
    vote, user_vote = update_incident_vote(item_id, user_id, vote_id, option_id)
    options = get_vote_options(vote, user_vote, language)
    return SaveMapItemVoteResponseTO(item_id=item_id, vote_id=vote_id, options=options)


def get_top_sections_resolved(user_id):
    app_id = get_app_id_from_user_id(user_id)
    s = IncidentStatisticsYear.create_key(app_id, date.today().year).get()
    if not s:
        return []
    if s.resolved_count == 0:
        return []
    # todo translate
    return [TextSectionTO(title=u'Opgeloste meldingen',
                          description=u'Dit jaar zijn er al %s meldingen opgelost.' % s.resolved_count)]
