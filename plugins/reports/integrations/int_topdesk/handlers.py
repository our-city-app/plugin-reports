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

import webapp2

from framework.utils import try_or_defer
from plugins.reports.dal import get_consumer
from plugins.reports.integrations.int_topdesk import incident_feedback


class TopdeskCallbackHandler(webapp2.RequestHandler):

    def post(self):
        auth_header = self.request.headers.get('Authorization', '')
        consumer = get_consumer(auth_header)
        if not consumer:
            logging.error('Received callback from topdesk with incorrect authorization')
            logging.debug('Headers: %s', self.request.headers)
            self.response.set_status(401)
            return

        logging.debug('Body: %s', self.request.body)
        data = json.loads(self.request.body) if self.request.body else {}
        incident_id = data.get('id')
        if not incident_id:
            logging.error('Received callback from topdesk without an id')
            self.response.set_status(400)
            return
        message = data.get('message')
        try_or_defer(incident_feedback, consumer.sik, incident_id, message)
