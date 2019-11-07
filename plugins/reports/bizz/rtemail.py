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
import re

from google.appengine.api import app_identity
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

from plugins.reports.integrations.int_3p import incident_follow_up

EMAIL_ADDRESS_EXPRESSION = re.compile("([^<]*<(?P<mail1>[^>]+)>.*|(?P<mail2>[^<]*))")
INCIDENT_FOLLOWUP_EXPRESSION = re.compile(
    "incident\\.(?P<incident_id>.*)\\.followup@%s\\.appspotmail\\.com" % app_identity.get_application_id())

ROUTER = {
    INCIDENT_FOLLOWUP_EXPRESSION: incident_follow_up
}


class EmailHandler(InboundMailHandler):

    def post(self, email, *args, **kwargs):
        super(EmailHandler, self).post(*args, **kwargs)

    def receive(self, mail_message):
        try:
            for body in mail_message.bodies():  # Fix for 8bit encoded messages
                body = body[1]
                if hasattr(body, 'charset') and body.charset and body.charset.lower() == '8bit':
                    body.charset = '7bit'
                if hasattr(body, 'encoding') and body.encoding and body.encoding.lower() == '8bit':
                    body.encoding = '7bit'
            logging.info(str(mail_message.to_mime_message()))
        except:
            logging.exception("Could not log incoming message")

        plaintext_bodies = list(mail_message.bodies('text/plain'))
        if plaintext_bodies:
            body = plaintext_bodies[0][1]
            if body.charset and body.charset.lower() == '8bit':  # Fix for 8bit encoded messages
                body.charset = '7bit'
            body = body.decode()

            xmailer = mail_message.original.get("X-Mailer")
            if xmailer and 'outlook' in xmailer.lower():
                body = body.replace('\r\n\r\n', '\n')

        m = EMAIL_ADDRESS_EXPRESSION.search(mail_message.to)
        if m is None:
            logging.error("Unable to parse recipient email address!\n\n\n%s" % mail_message.to)
            return

        groups = m.groupdict()
        to_address = groups['mail2'] if groups['mail1'] is None else groups['mail1']

        for regex, function in ROUTER.iteritems():
            m = regex.search(to_address)
            if m:
                function(mail_message.sender, m, getattr(mail_message, 'subject', ''), body)
                break
        else:
            # If loop did not break ...
            logging.warning("Recipient email address not recognized!\n\n\n%s" % mail_message.to)
            return
