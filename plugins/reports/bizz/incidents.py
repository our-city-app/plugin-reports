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
from mcfw.rpc import returns, arguments
from plugins.reports.bizz.elasticsearch import delete_docs
from plugins.reports.dal import save_rogerthat_user, get_rogerthat_user
from plugins.reports.models import Incident


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

    incident.visible = False
    incident.cleanup_date = None
    incident.search_keys = []

    # todo implement


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
    
    # todo implement
