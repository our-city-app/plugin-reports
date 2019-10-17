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

import base64
import json
import logging
import time

from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from plugins.reports.models import ElasticsearchSettings, Incident


def get_elasticsearch_config():
    settings = ElasticsearchSettings.create_key().get()
    if not settings:
        raise Exception('elasticsearch settings not found')

    return settings.base_url, settings.auth_username, settings.auth_password


def delete_index():
    base_url, es_user, es_passwd = get_elasticsearch_config()
    headers = {
        'Authorization': 'Basic %s' % base64.b64encode("%s:%s" % (es_user, es_passwd))
    }
    result = urlfetch.fetch('%s/reports' % base_url, method=urlfetch.DELETE, headers=headers, deadline=30)
    logging.info('Deleting reports index: %s %s', result.status_code, result.content)

    if result.status_code not in (200, 404):
        raise Exception('Failed to delete reports index')


def create_index():
    base_url, es_user, es_passwd = get_elasticsearch_config()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic %s' % base64.b64encode("%s:%s" % (es_user, es_passwd))
    }

    request = {
        "mappings": {
            "properties": {
                "location": {
                    "type": "geo_point"
                },
                "status": {
                    "type":  "keyword"
                }
            }
        }
    }

    json_request = json.dumps(request)

    result = urlfetch.fetch('%s/reports' % base_url, json_request, method=urlfetch.PUT, headers=headers, deadline=30)
    logging.info('Creating reports index: %s %s', result.status_code, result.content)

    if result.status_code != 200:
        raise Exception('Failed to create reports index')


def delete_docs(uids):
    for uid in uids:
        delete_doc(uid)


def delete_doc(uid):
    base_url, es_user, es_passwd = get_elasticsearch_config()
    headers = {
        'Authorization': 'Basic %s' % base64.b64encode("%s:%s" % (es_user, es_passwd))
    }
    result = urlfetch.fetch('%s/reports/_doc/%s' % (base_url, uid), method=urlfetch.DELETE, headers=headers, deadline=30)

    if result.status_code not in (200, 404):
        logging.info('Deleting reports index: %s %s', result.status_code, result.content)
        raise Exception('Failed to delete index %s', uid)


def index_docs(docs):
    for d in docs:
        index_doc(d['uid'], d['data'])


def index_doc(uid, data):
    base_url, es_user, es_passwd = get_elasticsearch_config()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic %s' % base64.b64encode("%s:%s" % (es_user, es_passwd))
    }

    json_request = json.dumps(data)

    result = urlfetch.fetch('%s/reports/_doc/%s' % (base_url, uid), json_request, method=urlfetch.PUT, headers=headers, deadline=30)
    if result.status_code not in (200, 201):
        logging.info('Creating reports index: %s %s', result.status_code, result.content)
        raise Exception('Failed to create index %s', uid)


def search_current(lat, lon, distance, status, cursor=None, limit=10):
    from plugins.reports.bizz import convert_to_item_tos
    start_time = time.time()
    new_cursor, result_data = _search(lat, lon, distance, status, cursor, limit, is_new=False)
    took_time = time.time() - start_time
    logging.info('debugging.search_current _search {0:.3f}s'.format(took_time))
    keys = set()

    start_time = time.time()
    for hit in result_data['hits']['hits']:
        uid = hit['_id']
        keys.add(Incident.create_key(uid))

    took_time = time.time() - start_time
    logging.info('debugging.search_current hits {0:.3f}s'.format(took_time))

    if keys:
        start_time = time.time()
        models = ndb.get_multi(keys)
        took_time = time.time() - start_time
        logging.info('debugging.search_current ndb.get_multi {0:.3f}s'.format(took_time))

        start_time = time.time()
        items = convert_to_item_tos(models)
        took_time = time.time() - start_time
        logging.info('debugging.search_current convert_to_item_tos {0:.3f}s'.format(took_time))
    else:
        items = []

    return items, new_cursor


def _search(lat, lon, distance, status, cursor, limit, is_new=False):
    # we can only fetch up to 10000 items with from param
    start_offset = long(cursor) if cursor else 0

    if (start_offset + limit) > 10000:
        limit = 10000 - start_offset
    if limit <= 0:
        return {'cursor': None, 'ids': []}

    d = {
        "size": limit,
        "from": start_offset,
        "query": {
            "bool" : {
                "must" : {
                    "match_all" : {}
                },
                "filter" : [
                    {
                        "geo_distance" : {
                            "distance" : "%sm" % distance,
                            "location" : {
                                "lat" :lat,
                                "lon" : lon
                            }
                        }
                    },
                    {
                        "term": {
                            "status": status
                        }
                    }
                ]
            }
        },
        "sort" : [
            {"_geo_distance" : {
                "location" : {
                    "lat" : lat,
                    "lon" : lon
                },
                "order" : "asc",
                "unit" : "m"}
            }
        ]
    }

    base_url, es_user, es_passwd = get_elasticsearch_config()

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Basic %s' % base64.b64encode("%s:%s" % (es_user, es_passwd))
    }

    json_request = json.dumps(d)

    result = urlfetch.fetch('%s/reports/_search' % base_url, json_request, method=urlfetch.POST, headers=headers, deadline=30)
    if result.status_code not in (200,):
        logging.info('Search reports: %s %s', result.status_code, result.content)
        raise Exception('Failed to search reports')

    result_data = json.loads(result.content)

    new_cursor = None
    next_offset = start_offset + len(result_data['hits']['hits'])
    if result_data['hits']['total']['relation'] in ('eq', 'gte'):
        if result_data['hits']['total']['value'] > next_offset and next_offset < 10000:
            new_cursor = u'%s' % next_offset

    return new_cursor, result_data
