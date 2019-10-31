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

from google.appengine.ext import ndb

from framework.i18n_utils import translate
from plugins.reports.models import IncidentVote, UserIncidentVote, Incident
from plugins.reports.to import MapItemDetailsTO, TextSectionTO, VoteSectionTO, \
    MapItemTO, GeoPointTO, MapIconTO, MapVoteOptionTO


@ndb.transactional()
def update_incident_vote(incident_id, from_option_id, to_option_id):
    vote_key = IncidentVote.create_key(incident_id)
    vote = vote_key.get()
    if not vote:
        vote = IncidentVote(key=vote_key)
        vote.negative_count = 0
        vote.positive_count = 0

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

    return vote


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


def convert_to_item_to(m):
    # type: (Incident) -> MapItemTO
    # TODO: proper icon
    icon_id = 'other'
    icon_color = '#263583'

    return MapItemTO(id=m.id,
                     coords=GeoPointTO(lat=m.details.geo_location.lat,
                                       lon=m.details.geo_location.lon),
                     icon=MapIconTO(id=icon_id,
                                    color=icon_color),
                     title=m.details.title,
                     description=m.details.description)


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
