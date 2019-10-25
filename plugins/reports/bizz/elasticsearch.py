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
import itertools
import json
import logging
import time

from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from mcfw.consts import DEBUG
from plugins.reports.bizz import convert_to_item_to
from plugins.reports.models import ElasticsearchSettings, Incident
from typing import Generator, Dict, Iterable, List, Tuple


def get_elasticsearch_config():
    # type: () -> ElasticsearchSettings
    settings = ElasticsearchSettings.create_key().get()
    if not settings:
        raise Exception('elasticsearch settings not found')
    return settings


def _request(path, method=urlfetch.GET, payload=None, allowed_status_codes=(200, 204)):
    # type: (str, int, Dict, Tuple[int]) -> Dict
    config = get_elasticsearch_config()
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic %s' % base64.b64encode('%s:%s' % (config.auth_username, config.auth_password))
    }
    if payload:
        if isinstance(payload, basestring):
            headers['Content-Type'] = 'application/x-ndjson'
        else:
            headers['Content-Type'] = 'application/json'
    data = json.dumps(payload) if isinstance(payload, dict) else payload
    url = config.base_url + path
    if DEBUG:
        logging.debug(url)
    result = urlfetch.fetch(url, data, method, headers, deadline=30)  # type: urlfetch._URLFetchResult
    if result.status_code not in allowed_status_codes:
        logging.debug(result.content)
        raise Exception('Invalid response from elasticsearch: %s' % result.status_code)
    if result.headers.get('Content-Type').startswith('application/json'):
        return json.loads(result.content)
    return result.content


def execute_bulk_request(operations):
    # type: (Iterable[Dict]) -> List[Dict]
    path = '/%s/_bulk' % get_reports_index()
    # NDJSON
    payload = '\n'.join([json.dumps(op) for op in operations])
    payload += '\n'
    result = _request(path, urlfetch.POST, payload)
    if result['errors'] is True:
        logging.debug(result)
        # throw the first error found
        for item in result['items']:
            k = item.keys()[0]
            if 'error' in item[k]:
                reason = item[k]['error']['reason']
                raise Exception(reason)
    return result['items']


def get_reports_index():
    if DEBUG:
        return 'debug-reports'
    return 'reports'


def delete_index():
    path = '/%s' % get_reports_index()
    return _request(path, urlfetch.DELETE)


def create_index():
    request = {
        'mappings': {
            'properties': {
                'location': {
                    'type': 'geo_point'
                },
                'status': {
                    'type': 'keyword'
                }
            }
        }
    }
    path = '/%s' % get_reports_index()
    return _request(path, urlfetch.PUT, request)


def index_incident(incident):
    # type: (Incident) -> Generator[Dict]
    if incident.visible:
        doc = {
            'location': {
                'lat': incident.details.geo_location.lat,
                'lon': incident.details.geo_location.lon
            },
            'status': incident.details.status
        }
        return index_doc_operations(incident.incident_id, doc)
    else:
        return delete_doc_operations(incident.incident_id)


def delete_doc_operations(uid):
    yield {'delete': {'_id': uid}}


def index_doc_operations(uid, doc):
    yield {'index': {'_id': uid}}
    yield doc


def re_index_incident(incident):
    # type: (Incident) -> List[Dict]
    return execute_bulk_request(index_incident(incident))


def re_index_incidents(incidents):
    # type: (List[Incident]) -> List[Dict]
    operations = itertools.chain.from_iterable([index_incident(incident) for incident in incidents])
    return execute_bulk_request(operations)


def search_current(lat, lon, distance, status, cursor=None, limit=10):
    start_time = time.time()
    new_cursor, result_data = _search(lat, lon, distance, status, cursor, limit)
    took_time = time.time() - start_time
    logging.info('debugging.search_current _search {0:.3f}s'.format(took_time))
    keys = {Incident.create_key(hit['_id']) for hit in result_data['hits']['hits']}

    if keys:
        start_time = time.time()
        models = ndb.get_multi(keys)
        took_time = time.time() - start_time
        logging.info('debugging.search_current ndb.get_multi {0:.3f}s'.format(took_time))

        start_time = time.time()
        items = [convert_to_item_to(model) for model in models]
        took_time = time.time() - start_time
        logging.info('debugging.search_current convert_to_item_tos {0:.3f}s'.format(took_time))
    else:
        items = []

    return items, new_cursor


def _search(lat, lon, distance, status, cursor, limit):
    # we can only fetch up to 10000 items with from param
    start_offset = long(cursor) if cursor else 0

    if (start_offset + limit) > 10000:
        limit = 10000 - start_offset
    if limit <= 0:
        return {'cursor': None, 'ids': []}

    d = {
        'size': limit,
        'from': start_offset,
        'query': {
            'bool': {
                'must': {
                    'match_all': {}
                },
                'filter': [{
                    'geo_distance': {
                        'distance': '%sm' % distance,
                        'location': {
                            'lat': lat,
                            'lon': lon
                        }
                    }
                }, {
                    'term': {
                        'status': status
                    }
                }]
            }
        },
        'sort': [{
            '_geo_distance': {
                'location': {
                    'lat': lat,
                    'lon': lon
                },
                'order': 'asc',
                'unit': 'm'
            }
        }]
    }
    path = '/%s/_search' % get_reports_index()
    result_data = _request(path, urlfetch.POST, d)

    new_cursor = None
    next_offset = start_offset + len(result_data['hits']['hits'])
    if result_data['hits']['total']['relation'] in ('eq', 'gte'):
        if result_data['hits']['total']['value'] > next_offset and next_offset < 10000:
            new_cursor = u'%s' % next_offset

    return new_cursor, result_data
