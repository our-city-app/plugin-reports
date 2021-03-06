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

from framework.bizz.authentication import get_browser_language
from framework.plugin_loader import get_config
from mcfw.exceptions import HttpBadRequestException
from mcfw.restapi import rest
from mcfw.rpc import returns, arguments, serialize_complex_value
from plugins.reports.bizz.map import get_report_map_items, get_reports_map_item_details, vote_report_item, \
    get_report_map_announcement
from plugins.reports.consts import NAMESPACE
from plugins.reports.to import GetMapItemsResponseTO, GetMapItemDetailsResponseTO, ItemVoteTO, SaveMapItemVoteResponseTO, \
    MapAnnouncementTO


def validate_request(f, handler):
    auth = handler.request.headers.get('Authorization', None)
    return auth == get_config(NAMESPACE).oca_server_secret


@rest('/map', 'get', silent_result=True, custom_auth_method=validate_request)
@returns(dict)
@arguments(user_id=unicode)
def api_get_map(user_id):
    announcement = get_report_map_announcement(user_id)
    return {u'announcement': serialize_complex_value(announcement, MapAnnouncementTO(), False) if announcement else None}


@rest('/items', 'get', silent_result=True, custom_auth_method=validate_request)
@returns(GetMapItemsResponseTO)
@arguments(user_id=unicode, lat=float, lon=float, distance=(int, long), status=unicode, limit=(int, long), cursor=unicode)
def api_get_items(user_id, lat, lon, distance, status=None, limit=None, cursor=None):
    return get_report_map_items(user_id, lat, lon, distance, status, limit, cursor)


@rest('/items/detail', 'get', silent_result=True, custom_auth_method=validate_request)
@returns(GetMapItemDetailsResponseTO)
@arguments(ids=unicode, user_id=unicode)
def api_get_item_details(ids, user_id):
    try:
        ids = {unicode(i) for i in ids.split(',')}
    except TypeError as e:
        logging.debug(e.message, exc_info=True)
        ids = []
    return get_reports_map_item_details(user_id, ids, get_browser_language())


@rest('/items/<item_id:[^/]+>/vote', 'post', silent_result=True, custom_auth_method=validate_request)
@returns(SaveMapItemVoteResponseTO)
@arguments(item_id=unicode, data=ItemVoteTO)
def api_vote_item(item_id, data):
    # type: (unicode, ItemVoteTO) -> SaveMapItemVoteResponseTO
    if not data.option_id or not data.user_id or not data.vote_id:
        raise HttpBadRequestException()
    return vote_report_item(item_id, data.user_id, data.vote_id, data.option_id, get_browser_language())
