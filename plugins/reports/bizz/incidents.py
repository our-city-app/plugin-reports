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

from datetime import datetime
import logging

from google.appengine.ext import ndb, deferred

from framework.bizz.job import run_job
from framework.utils import guid
from mcfw.properties import object_factory
from mcfw.rpc import returns, arguments, parse_complex_value
from plugins.reports.bizz.elasticsearch import delete_docs, index_docs
from plugins.reports.bizz.rogerthat import send_rogerthat_message
from plugins.reports.dal import save_rogerthat_user, get_rogerthat_user, \
    get_integration_settings, get_incident
from plugins.reports.integrations.int_3p import create_incident as create_3p_incident
from plugins.reports.integrations.int_topdesk import create_incident as create_topdesk_incident
from plugins.reports.models import Incident, IntegrationSettings
from plugins.rogerthat_api.to import MemberTO
from plugins.rogerthat_api.to.messaging.flow import FLOW_STEP_MAPPING


def cleanup_timed_out():
    run_job(cleanup_timed_out_query, [], cleanup_timed_out_worker, [])


def cleanup_timed_out_query():
    qry = Incident.query()
    qry = qry.filter(Incident.cleanup_time != None)
    qry = qry.filter(Incident.cleanup_time < datetime.utcnow())
    qry = qry.order(Incident.cleanup_time, Incident.key)
    return qry


def cleanup_timed_out_worker(m_key):
    re_index(m_key)


@returns()
@arguments(m_key=ndb.Key)
def re_index(m_key):
    m = m_key.get()
    re_index_incident(m)


@returns()
@arguments(incident=Incident)
def re_index_incident(incident):
    delete_docs(incident.search_keys)
    incident.search_keys = []
    if not incident.visible:
        incident.cleanup_date = None
        incident.put()
        return

    docs = []
    doc = {
        "location": {
            "lat": incident.details.geo_location.lat,
            "lon": incident.details.geo_location.lon
        },
        "status": incident.details.status
    }
    docs.append({'uid': incident.incident_id, 'data': doc})
    incident.search_keys.append(incident.incident_id)

    incident.put()
    index_docs(docs)


def process_incident(sik, user_details, parent_message_key, steps, timestamp):
    rt_user = save_rogerthat_user(user_details[0])
    incident_id = Incident.create_key().id()
    deferred.defer(_create_incident,
                   incident_id,
                   sik,
                   rt_user.user_id,
                   parent_message_key,
                   timestamp,
                   steps)


def _create_incident(incident_id, sik, user_id, parent_message_key, timestamp, steps):
    logging.debug("_create_incident for user %s", user_id)
    rt_user = get_rogerthat_user(user_id)
    if not rt_user:
        logging.error('Could not find user with id %s' % (user_id))
        return

    settings = get_integration_settings(sik)
    if not settings:
        logging.error('Could not find integration settings for %s' % (sik))
        return

    incident = Incident(key=Incident.create_key(incident_id))
    incident.sik = sik
    incident.user_id = user_id
    incident.report_time = datetime.utcfromtimestamp(timestamp)
    incident.resolve_time = None
    incident.cleanup_time = None
    incident.search_keys = []
    incident.integration = settings.integration
    incident.params = {'source': 'app',
                       'parent_message_key': parent_message_key,
                       'steps': steps}

    parsed_steps = parse_complex_value(object_factory("step_type", FLOW_STEP_MAPPING), steps, True)
    if settings.integration == IntegrationSettings.INT_TOPDESK:
        visible, params, details = create_topdesk_incident(settings, rt_user, incident, parsed_steps)
    elif settings.integration == IntegrationSettings.INT_3P:
        visible, params, details = create_3p_incident(settings, rt_user, incident, parsed_steps)
    else:
        visible = False
        params = None
        details = None
    if params:
        incident.params.update(params)
    incident.visible = visible
    incident.details = details

    re_index_incident(incident)


def incident_follow_up(from_, regex, subject, body):
    # todo-later security validate from
    incident_id = long(regex.groupdict()['incident_id'])
    incident = get_incident(incident_id)
    if not incident:
        logging.debug("Recieved incident update that is not in our database: '%s'" % (incident_id))
        return
    rt_user = get_rogerthat_user(incident.user_id)
    member = MemberTO(member=rt_user.email, app_id=rt_user.app_id, alert_flags=2)
    parent_message_key = incident.params.get('parent_message_key')
    deferred.defer(send_rogerthat_message, incident.sik, member, body,
                   parent_message_key=parent_message_key,
                   json_rpc_id=guid())
