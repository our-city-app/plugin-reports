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

from mcfw.cache import cached
from mcfw.rpc import returns, arguments
from plugins.rogerthat_api.api import messaging, system
from plugins.rogerthat_api.models.settings import RogerthatSettings
from plugins.rogerthat_api.to import MemberTO
from plugins.rogerthat_api.to.messaging import AnswerTO, Message


@returns(unicode)
@arguments(sik=unicode, member=MemberTO, message=unicode, answers=(None, [AnswerTO]), flags=(int, long), json_rpc_id=unicode)
def send_rogerthat_message(sik, member, message, answers=None, flags=None, json_rpc_id=None):
    rt_settings = RogerthatSettings.create_key(sik).get()
    flags = flags if flags is not None else Message.FLAG_AUTO_LOCK
    if not answers:
        flags = flags | Message.FLAG_ALLOW_DISMISS
        answers = []
    return messaging.send(api_key=rt_settings.api_key,
                          parent_message_key=None,
                          members=[member],
                          message=message,
                          answers=answers or [],
                          flags=flags,
                          alert_flags=Message.ALERT_FLAG_VIBRATE,
                          branding=get_main_branding_hash(rt_settings.api_key),
                          tag=None,
                          json_rpc_id=json_rpc_id)


@cached(version=1, lifetime=86400, request=True, memcache=True)
@returns(unicode)
@arguments(api_key=unicode)
def get_main_branding_hash(api_key):
    si = system.get_identity(api_key)
    return si.description_branding
