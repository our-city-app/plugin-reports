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

import webapp2

from plugins.reports.bizz import re_count_incidents
from plugins.reports.bizz.incident_statistics import build_monthly_incident_statistics, refresh_all_tags
from plugins.reports.bizz.incidents import cleanup_timed_out


class ReportsCleanupTimedOutHandler(webapp2.RequestHandler):

    def get(self):
        cleanup_timed_out()


class ReportsCountIncidentsHandler(webapp2.RequestHandler):

    def get(self):
        re_count_incidents()


class BuildIncidentStatisticsHandler(webapp2.RequestHandler):
    def get(self):
        build_monthly_incident_statistics(datetime.now())
        refresh_all_tags()
