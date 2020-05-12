# -*- coding: utf-8 -*-
# Copyright 2020 Green Valley NV
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

from plugins.reports.models import Incident, IncidentStatus


def migrate(dry_run=True):
    to_put = []
    for incident in Incident.query():  # type: Incident
        incident.resolve_date = None
        if incident.status_dates:
            last = incident.status_dates[-1]
            if last.status == IncidentStatus.RESOLVED:
                incident.resolve_date = last.date
        to_put.append(incident)
    if not dry_run:
        ndb.put_multi(to_put)
    return to_put
