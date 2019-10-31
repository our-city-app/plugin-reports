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

from mcfw.rpc import parse_complex_value, serialize_complex_value
from plugins.reports.bizz.incidents import process_incident
from plugins.reports.dal import get_consumer
from plugins.reports.utils import parse_to_human_readable_tag
from plugins.rogerthat_api.to import UserDetailsTO
from plugins.rogerthat_api.to.messaging.service_callback_results import FlowMemberResultCallbackResultTO

FMR_TAG_MAPPING = {
    'meldings-kaart': process_incident,
    'meldingskaart': process_incident
}


def log_and_parse_user_details(user_details):
    # type: (dict) -> UserDetailsTO
    is_list = isinstance(user_details, list)
    user_detail = user_details[0] if is_list else user_details
    logging.debug('Current user: %(email)s:%(app_id)s', user_detail)
    return parse_complex_value(UserDetailsTO, user_details, is_list)


def flow_member_result(rt_settings, request_id, tag, parent_message_key, steps, flush_id, user_details, timestamp, **kwargs):
    user_details = log_and_parse_user_details(user_details)
    f = FMR_TAG_MAPPING.get(parse_to_human_readable_tag(tag))
    if f:
        logging.info('Processing flow_member_result with tag %s and flush_id %s', tag, flush_id)
        consumer = get_consumer(rt_settings.sik)
        result = f(consumer.integration_id, user_details, parent_message_key, steps, timestamp)
        return result and serialize_complex_value(result, FlowMemberResultCallbackResultTO, False,
                                                  skip_missing=True)
    return None
