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
import json
import logging
import urllib
from HTMLParser import HTMLParser
from base64 import b64encode, b64decode

import webapp2
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext.deferred import PermanentTaskFailure
from html2text import HTML2Text
from mcfw.cache import cached
from mcfw.properties import unicode_property, long_property, typed_property
from mcfw.rpc import arguments, returns
from typing import List

from framework.bizz.job import run_job
from framework.to import TO
from framework.utils import get_server_url
from framework.utils import try_or_defer, guid, convert_to_str
from plugins.reports.bizz.rogerthat import send_rogerthat_message
from plugins.reports.dal import get_rogerthat_user
from plugins.reports.models import GreenValleySettings, Incident, IntegrationSettings, IntegrationProvider, \
    IntegrationParamsGreenValley
from plugins.rogerthat_api.to import MemberTO
from plugins.rogerthat_api.to.messaging import AttachmentTO


class GVExternalNotificationAttachment(TO):
    extension = unicode_property('extension')
    fileData = unicode_property('fileData')
    fileSize = long_property('fileSize')
    id = unicode_property('id')
    mimeType = unicode_property('mimeType')
    name = unicode_property('name')


class GVExternalNotification(TO):
    attachments = typed_property('attachments', GVExternalNotificationAttachment,
                                 True)  # type: List[GVExternalNotificationAttachment]
    caseReference = unicode_property('caseReference')
    emailAddress = unicode_property('emailAddress')
    firstName = unicode_property('firstName')
    id = unicode_property('id')
    identityNumber = unicode_property('identityNumber')
    lastName = unicode_property('lastName')
    message = unicode_property('message')
    sentDate = unicode_property('sentDate')
    source = unicode_property('source')  # one of WORKFLOW, CASE_MESSAGE, EXTERNAL_TASK


@cached(0, lifetime=14 * 60)
@returns(dict)
@arguments(realm=unicode, client_id=unicode, client_secret=unicode)
def _get_token(realm, client_id, client_secret):
    # type: (str, str, str) -> str
    url = 'https://gateway-release.onlinesmartcities.be/external/authorization/intercept/auth/token'
    headers = {
        'Authorization': 'Basic %s' % b64encode('%s--%s:%s' % (client_id, realm, client_secret)),
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    payload = 'grant_type=client_credentials'
    response = urlfetch.fetch(url, payload, method=urlfetch.POST, headers=headers)  # type: urlfetch._URLFetchResult
    if response.status_code == 200:
        return json.loads(response.content)
    else:
        logging.debug('Request: %s\nHeaders:%s', url, headers)
        logging.debug('Response: %s: %s', response.status_code, response.content)
        raise Exception('Invalid response from %s' % url)


def _request(settings, path, method=urlfetch.GET, params=None):
    # type: (GreenValleySettings, str, int, dict) -> dict
    token = _get_token(settings.realm, settings.gateway_client_id, settings.gateway_client_secret)
    headers = {
        'Authorization': 'Bearer %s' % token['access_token'],
    }
    url_params = ('?' + urllib.urlencode(params)) if params and method == urlfetch.GET else ''
    url = 'https://gateway-release.onlinesmartcities.be/external/api/v1%s%s' % (path, url_params)
    payload = json.dumps(params) if method != urlfetch.GET and params else None
    response = urlfetch.fetch(url, payload, method, headers, deadline=30)  # type: urlfetch._URLFetchResult
    if response.status_code == 200:
        return json.loads(response.content)
    else:
        logging.debug('Request: %s\nHeaders:%s\nPayload:%s', url, headers, payload)
        logging.debug('Response: %s: %s', response.status_code, response.content)
        raise Exception('Invalid response from %s' % url)


def get_notifications(settings, case_reference):
    # type: (GreenValleySettings, str) -> List[GVExternalNotification]
    params = {
        'caseReference': case_reference,
    }
    result = _request(settings, '/notifications', params=params)
    return GVExternalNotification.from_list(result)


def _get_all_incidents(integration_id):
    return Incident.list_by_integration_id(integration_id)


def check_for_new_notifications(incident_key, integration_id):
    keys = incident_key, IntegrationSettings.create_key(integration_id)
    incident, settings = ndb.get_multi(keys)  # type: Incident, IntegrationSettings
    if not incident.external_id:
        logging.info('Skipping incident %s, external id not set', incident.id)
        return
    try:
        notifications = get_notifications(settings.data, incident.external_id)
    except Exception as e:
        logging.exception('Could not fetch notifications')
        raise PermanentTaskFailure(e.message)
    if isinstance(incident.integration_params, IntegrationParamsGreenValley):
        new_notifications = [n for n in notifications if n.id not in incident.integration_params.notification_ids]
        try_or_defer(_send_notification, new_notifications, incident_key, integration_id)
    else:
        raise Exception('Invalid integration params for incident %s' % incident.id)


@ndb.transactional(xg=True)
def _send_notification(notifications, incident_key, integration_id):
    # type: (List[GVExternalNotification], ndb.Key, int) -> None
    keys = incident_key, IntegrationSettings.create_key(integration_id)
    incident, settings = ndb.get_multi(keys)  # type: Incident, IntegrationSettings
    rt_user = get_rogerthat_user(incident.user_id)
    member = MemberTO(member=rt_user.email, app_id=rt_user.app_id, alert_flags=2)
    assert isinstance(incident.integration_params, IntegrationParamsGreenValley)
    server_url = get_server_url()
    for notification in notifications:
        incident.integration_params.notification_ids.append(notification.id)
        unescaped = HTMLParser().unescape(notification.message)
        message = html_to_markdown(unescaped)
        if not message:
            continue
        attachments = []
        if notification.attachments:
            for attachment in notification.attachments:
                if attachment.mimeType in AttachmentTO.CONTENT_TYPES:
                    a = AttachmentTO()
                    a.name = attachment.name
                    a.size = attachment.fileSize
                    a.content_type = attachment.mimeType
                    a.download_url = NotificationAttachmentHandler.get_route(server_url, settings.id, notification.id,
                                                                             attachment.id)
                    attachments.append(a)
        # TODO: maybe don't send initial confirmation message containing the entire form the user has sent
        message_id = send_rogerthat_message(settings.sik, member, message,
                                            attachments=attachments,
                                            parent_message_key=incident.integration_params.parent_message_id,
                                            json_rpc_id=guid())
        if not incident.integration_params.parent_message_id:
            incident.integration_params.parent_message_id = message_id
    logging.debug(incident)
    incident.put()


def html_to_markdown(html_content):
    if not html_content:
        return html_content
    converter = HTML2Text(bodywidth=0)
    converter.ignore_images = True
    return converter.handle(html_content).strip()


class NotificationsCronHandler(webapp2.RequestHandler):
    def get(self):
        qry = IntegrationSettings.list_by_integration(
            IntegrationProvider.GREEN_VALLEY)  # type: List[IntegrationSettings]
        for integration in qry:
            if isinstance(integration.data, GreenValleySettings) and integration.data.gateway_client_secret:
                run_job(_get_all_incidents, [integration.id], check_for_new_notifications, [integration.id])


class NotificationAttachmentHandler(webapp2.RequestHandler):

    @staticmethod
    def get_route(base_url, integration_id, notification_id, attachment_id):
        return '%s/plugins/reports/green_valley/%s/notifications/%s/attachments/%s' % (
            base_url, integration_id, notification_id, attachment_id)

    def get(self, integration_id, notification_id, attachment_id):
        integration_id = long(integration_id)
        settings = IntegrationSettings.create_key(integration_id).get()
        try:
            result = _request(settings.data, '/notifications/%s/attachments/%s' % (notification_id, attachment_id))
            attachment = GVExternalNotificationAttachment.from_dict(result)
            self.response.headers['Content-Type'] = convert_to_str(attachment.mimeType)
            self.response.out.write(b64decode(attachment.fileData))
        except Exception as e:
            logging.exception(e)
            self.abort(404)
