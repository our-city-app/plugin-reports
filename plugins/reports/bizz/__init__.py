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

from google.appengine.ext import ndb

from plugins.reports.models import IncidentVote, UserIncidentVote
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
    if from_option_id and from_option_id == IncidentVote.NEGATIVE:
        vote.negative_count -= 1
        changed = True
    if from_option_id and from_option_id == IncidentVote.POSITIVE:
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


def get_vote_options(vote, user_vote):
    positive_count = vote.positive_count if vote else 0
    positive_seleted = user_vote.option_id == IncidentVote.POSITIVE if user_vote else False
    negative_count = vote.negative_count if vote else 0
    negative_seleted = user_vote.option_id == IncidentVote.NEGATIVE if user_vote else False
    return [
        MapVoteOptionTO(id=IncidentVote.POSITIVE,
                        icon=u'fa-thumbs-o-up',
                        title=u'Het is opgelost',
                        count=positive_count,
                        color=u'#87CD03',
                        selected=positive_seleted),
        MapVoteOptionTO(id=IncidentVote.NEGATIVE,
                        icon=u'fa-eye',
                        title=u'Deze melding ook rapporteren',
                        count=negative_count,
                        color=u'#FE6B00',
                        selected=negative_seleted)
    ]


def convert_to_item_to(m):
    icon_id = 'other'
    icon_color = '#263583'

    return MapItemTO(id=m.uid,
                     coords=GeoPointTO(lat=m.geo_location.lat,
                                       lon=m.geo_location.lon),
                     icon=MapIconTO(id=icon_id,
                                    color=icon_color),
                     title=u'Report title %s' % m.status,
                     description=u'\n'.join([u'Report description line 1',
                                             m.description]))


def convert_to_item_tos(models):
    items = []
    for m in models:
        try:
            items.append(convert_to_item_to(m))
        except:
            logging.debug('uid: %s', m.uid)
            raise

    return items


def convert_to_item_details_to(user_id, m):
    to = MapItemDetailsTO(id=m.uid,
                          geometry=[],
                          sections=[])

    to.sections.append(TextSectionTO(title=u'Report detail title %s' % m.status,
                                     description=u'\n'.join([u'Report detail description line 1',
                                                             m.description])))

    vote = IncidentVote.create_key(m.uid).get()
    user_vote = UserIncidentVote.create_key(user_id, m.uid).get()
    to.sections.append(VoteSectionTO(id=u'vote1',
                                     options=get_vote_options(vote, user_vote)))

    return to


def convert_to_item_details_tos(user_id, models):
    items = []
    for m in models:
        try:
            items.append(convert_to_item_details_to(user_id, m))
        except:
            logging.debug('uid: %s', m.uid)
            raise

    return items
