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

import json
import logging
import time

from google.appengine.ext import ndb
import webapp2

from framework.utils import try_or_defer
from mcfw.rpc import serialize_complex_value
from plugins.reports.bizz import convert_to_item_details_tos, \
    update_incident_vote, get_vote_options
from plugins.reports.bizz.elasticsearch import search_current
from plugins.reports.integrations.int_topdesk.importer import FakeTopdeskIncident
from plugins.reports.models import Consumer, Incident, IncidentVote, \
    UserIncidentVote
from plugins.reports.to import GetMapItemDetailsResponseTO, \
    GetMapItemsResponseTO, SaveMapItemVoteResponseTO


def return_items_result(self, items, new_cursor, distance):
    headers = {}
    headers['Content-Type'] = 'application/json'
    headers['Accept'] = 'application/json'
    self.response.headers = headers

    logging.debug('got %s search results', len(items))
    result_to = GetMapItemsResponseTO(cursor=new_cursor, items=items, distance=distance)
    start_time = time.time()
    result = serialize_complex_value(result_to, GetMapItemsResponseTO, False)
    took_time = time.time() - start_time
    logging.info('debugging.return_items_result serialize_complex_value {0:.3f}s'.format(took_time))

    start_time = time.time()
    self.response.out.write(json.dumps(result))
    took_time = time.time() - start_time
    logging.info('debugging.return_items_result self.response.out.write {0:.3f}s'.format(took_time))


def _get_items(self):
    params = json.loads(self.request.body) if self.request.body else {}
    lat = params.get('lat')
    lng = params.get('lon')
    distance = params.get('distance')
#     status = params.get('status')
    status = Incident.STATUS_TODO  # todo fix status
    limit = params.get('limit')
    cursor = params.get('cursor', None)

    if lat and lng and distance and status and limit:
        try:
            lat = float(lat)
            lng = float(lng)
            distance = long(distance)
            limit = long(limit)
            if limit > 1000:
                limit = 1000
        except:
            logging.debug('not all parameters where provided correctly', exc_info=True)
            return_items_result(self, [], None, distance)
            return
    else:
        logging.debug('not all parameters where provided')
        return_items_result(self, [], None, distance)
        return

    items, new_cursor = search_current(lat, lng, distance, status, cursor=cursor, limit=limit)
    return_items_result(self, items, new_cursor, distance)


def return_detail_result(self, items):
    headers = {}
    headers['Content-Type'] = 'application/json'
    headers['Accept'] = 'application/json'
    self.response.headers = headers

    logging.debug('got %s results', len(items))
    result_to = GetMapItemDetailsResponseTO(items=items)
    result = serialize_complex_value(result_to, GetMapItemDetailsResponseTO, False)
    self.response.out.write(json.dumps(result))


def _get_details(self):
    params = json.loads(self.request.body) if self.request.body else {}
    user_id = params.get('user_id')
    ids = params.get('ids')
    if not ids or not user_id:
        return_detail_result(self, [])
        return
    if type(ids) is not list:
        return_detail_result(self, [])
        return

    keys = set()
    for uid in ids:
        keys.add(FakeTopdeskIncident.create_key(uid))

    items = []
    if keys:
        models = ndb.get_multi(keys)
        items.extend(convert_to_item_details_tos(user_id, models))
    else:
        items = []

    return_detail_result(self, items)
    

class AuthValidationHandler(webapp2.RequestHandler):

    def dispatch(self):
        consumer_key = self.request.headers.get('consumer_key', None)
        if not consumer_key:
            self.abort(401)
            return
        c = Consumer.create_key(consumer_key).get()
        if not c:
            self.abort(401)
            return

        return super(AuthValidationHandler, self).dispatch()


class ReportItemsHandler(AuthValidationHandler):

    def post(self):
        logging.debug(self.request.body)
        _get_items(self)


class ReportItemDetailsHandler(AuthValidationHandler):

    def post(self):
        logging.debug(self.request.body)
        _get_details(self)


class ReportItemsVoteHandler(AuthValidationHandler):

    def post(self):
        logging.debug(self.request.body)
        params = json.loads(self.request.body) if self.request.body else {}
        user_id = params.get('user_id')
        item_id = params.get('item_id')
        vote_id = params.get('vote_id')
        option_id = params.get('option_id')

        if not user_id or not item_id or not option_id:
            self.abort(400)
            return

        incident = FakeTopdeskIncident.create_key(item_id).get()
        if not incident:
            self.abort(400)
            return

        from_option = None
        user_vote_key = UserIncidentVote.create_key(user_id, item_id)
        user_vote = user_vote_key.get()
        save_vote = True
        if user_vote:
            from_option = user_vote.option_id
            if from_option == option_id:
                user_vote_key.delete()
                user_vote = None
                save_vote = False
        else:
            user_vote = UserIncidentVote(key=user_vote_key)
        if save_vote:
            user_vote.incident_id = item_id
            user_vote.option_id = option_id
            user_vote.put()

        # todo trans collision
        vote = update_incident_vote(item_id, from_option, option_id)
        options = get_vote_options(vote, user_vote)

        headers = {}
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'
        self.response.headers = headers

        result_to = SaveMapItemVoteResponseTO(item_id=item_id,
                                              vote_id=vote_id,
                                              options=options)
        result = serialize_complex_value(result_to, SaveMapItemVoteResponseTO, False)
        self.response.out.write(json.dumps(result))
