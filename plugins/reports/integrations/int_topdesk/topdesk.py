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
from cStringIO import StringIO

from google.appengine.api import urlfetch

from PIL import Image
from mcfw.exceptions import HttpBadRequestException
from plugins.reports.dal import get_integration_settings
from plugins.reports.integrations.int_topdesk.consts import ENDPOINTS, TopdeskPropertyName
from plugins.reports.models import TopdeskSettings, RogerthatUser, IntegrationSettings
from plugins.rogerthat_api.to.messaging.forms import OpenIdWidgetResultTO
from urllib3 import encode_multipart_formdata


class TopdeskApiException(Exception):

    def __init__(self, urlfetch_result):
        # type: (urlfetch._URLFetchResult) -> TopdeskApiException
        self.status_code = urlfetch_result.status_code
        self.content = urlfetch_result.content
        try:
            self.message = json.loads(urlfetch_result.content)[0]['message']
        except:
            self.message = urlfetch_result.content

    def __str__(self):
        return self.message


def get_topdesk_settings(sik):
    # type: (str) -> TopdeskSettings
    return get_integration_settings(sik).data


def _get_person_info_from_rogerthat_user(settings, rogerthat_user):
    # type: (TopdeskSettings, RogerthatUser) -> dict
    split_name = rogerthat_user.name.split(' ')
    first_name = split_name[0]
    sur_name = ''
    if len(split_name) > 1:
        sur_name = ''.join(split_name[1:])
    if not sur_name:
        sur_name = '(onbekend)'
    person = {
        'email': rogerthat_user.email,
        'firstName': first_name,
        'surName': sur_name,
    }
    if settings.caller_branch_id:  # todo fix
        person['branch'] = {
            'id': settings.caller_branch_id  # todo fix
        }
    return person


def _update_person_with_openid_data(person, openid_result):
    # type: (dict, OpenIdWidgetResultTO) -> dict
    mapping = {
        'firstName': openid_result.given_name,
        'surName': openid_result.family_name,
        'email': openid_result.email,
        'phoneNumber': openid_result.phone_number,
    }
    for key, value in mapping.iteritems():
        if value:
            person[key] = value
    if openid_result.gender:
        # must be one of UNDEFINED, MALE, FEMALE
        person['gender'] = openid_result.gender.upper()
    return person


def create_topdesk_person(settings, rogerthat_user, openid_result):
    # type: (TopdeskSettings, RogerthatUser, OpenIdWidgetResultTO) -> str
    person = _get_person_info_from_rogerthat_user(settings, rogerthat_user)
    if openid_result:
        person = _update_person_with_openid_data(person, openid_result)
    created_person = topdesk_api_call(settings, '/api/persons', urlfetch.POST, person)
    logging.debug('Created topdesk person: %s', created_person)
    return created_person['id']


def update_topdesk_person(settings, rogerthat_user, openid_result):
    # type: (TopdeskSettings, RogerthatUser, OpenIdWidgetResultTO) -> dict
    person = _get_person_info_from_rogerthat_user(settings, rogerthat_user)
    person = _update_person_with_openid_data(person, openid_result)
    url = '/api/persons/id/%s' % rogerthat_user.external_id
    updated_person = topdesk_api_call(settings, url, urlfetch.PUT, person)
    logging.debug('Updated topdesk person: %s', updated_person)
    return updated_person


def _get_headers(username, password):
    base64string = base64.b64encode('%s:%s' % (username, password))
    return {
        'Authorization': "Basic %s" % base64string,  # TODO upgrade to api tokens instead of this
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }


def topdesk_api_call(settings, path, method=urlfetch.GET, payload=None):
    # type: (TopdeskSettings, str, int, dict) -> dict
    full_url = '%s%s' % (settings.api_url, path)
    headers = _get_headers(settings.username, settings.password)
    response = urlfetch.fetch(full_url,
                              headers=headers,
                              payload=json.dumps(payload) if payload else None,
                              method=method,
                              deadline=30)  # type: urlfetch._URLFetchResult

    should_raise = False
    if method == urlfetch.GET and response.status_code not in (200, 204, 206,):
        should_raise = True
    if method == urlfetch.POST and response.status_code not in (201,):
        should_raise = True

    if should_raise:
        logging.info('Headers: %s', headers)
        if response.content:
            logging.info('Content: %s', response.content)
        if payload:
            logging.info('Payload: %s', payload)
        raise TopdeskApiException(response)

    return json.loads(response.content) if response.content else None


def get_topdesk_data(url, username, password):
    # type: (str,str,str) -> dict
    paths = [ENDPOINTS[prop] for prop in
             (TopdeskPropertyName.ENTRY_TYPE, TopdeskPropertyName.CALL_TYPE, TopdeskPropertyName.CATEGORY,
              TopdeskPropertyName.SUB_CATEGORY,
              TopdeskPropertyName.BRANCH, TopdeskPropertyName.OPERATOR_GROUP, TopdeskPropertyName.OPERATOR)]
    rpcs = []
    for path in paths:
        full_url = '%s/api%s' % (url, path)
        headers = _get_headers(username, password)
        rpc = urlfetch.create_rpc(20)
        urlfetch.make_fetch_call(rpc, full_url, headers=headers)
        rpcs.append(rpc)
    try:
        entry_types, call_types, categories, sub_categories, branches, operator_groups, operators = [
            json.loads(rpc.get_result().content) if rpc.get_result().content else [] for rpc in rpcs]
    except:
        logging.debug('Failed to exec rpc to topdesk', exc_info=True)
        raise HttpBadRequestException('%s: %s' % (rpcs[0].get_result().status_code, rpcs[0].get_result().content))
    return {
        'entryTypes': entry_types,
        'callTypes': call_types,
        'categories': categories,
        'subCategories': sub_categories,
        'branches': branches,
        'operatorGroups': operator_groups,
        'operators': operators,
    }


def _download(url):
    response = urlfetch.fetch(url, deadline=30)
    if response.status_code != 200:
        raise Exception('Failed to download url: %s' % url)
    return str(response.content)


def _maybe_resize_image(image):
    img_file = StringIO(image)
    img = Image.open(img_file)
    width, height = img.size
    max_width = 2560
    if width < max_width:
        return image
    new_height = int(float(height) / float(width) * max_width)
    result_image = img.resize((max_width, new_height))  # type: Image.Image
    result = StringIO()
    result_image.save(result, 'jpeg')
    return result.getvalue()


def upload_attachment(sik, topdesk_incident_id, url, file_name):
    file_content = _download(url)

    content_type = 'image/jpg'
    file_content = _maybe_resize_image(file_content)
    payload, payload_content_type = encode_multipart_formdata([
        ('file', (file_name, file_content, content_type)),
    ])
    settings = get_topdesk_settings(sik)
    headers = _get_headers(settings.username, settings.password)  # todo fix
    headers['Content-Type'] = payload_content_type

    response = urlfetch.fetch('%s/api/incidents/id/%s/attachments' % (settings.api_url, topdesk_incident_id),
                              # todo fix
                              payload=payload,
                              method=urlfetch.POST,
                              headers=headers,
                              deadline=30)

    if response.status_code != 200:
        logging.debug(response.content)
        raise Exception("Failed to upload file %s with status code %s" % (file_name, response.status_code))
