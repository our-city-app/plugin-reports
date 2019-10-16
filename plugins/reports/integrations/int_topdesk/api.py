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

from mcfw.restapi import rest
from mcfw.rpc import returns, arguments

# todo fix


@rest('/settings', 'get', silent_result=True)
@returns([dict])
@arguments()
def api_list_settings():
    return []
#     return [settings.to_dict(include=['api_url'],
#                              extra_properties=['sik']) for settings in TopdeskSettings.query()]


@rest('/settings/<sik:[^/]+>', 'get', silent_result=True)
@returns(dict)
@arguments(sik=unicode)
def api_get_settings(sik):
    return {}
#     settings = TopdeskSettings.create_key(sik).get()
#     if not settings:
#         raise HttpNotFoundException('settings_not_found', {'sik': sik})
#     return settings.to_dict(extra_properties=['sik'])


@rest('/settings/<sik:[^/]+>', 'put', silent_result=True)
@returns(dict)
@arguments(sik=unicode, data=dict)
def api_save_settings(sik, data):
    return {}
#     allowed_keys = ['secret', 'api_url', 'username', 'password', 'caller_branch_id', 'call_type_id', 'category_id',
#                     'sub_category_id', 'branch_id', 'entry_type_id', 'operator_group_id', 'operator_id',
#                     'unregistered_users', 'field_mapping']
#     kwargs = {key: data[key] for key in data if key in allowed_keys}
#     if 'field_mapping' in kwargs:
#         kwargs['field_mapping'] = [FieldMapping(**mapping) for mapping in kwargs['field_mapping']]
#     settings = create_topdesk_settings(sik, **kwargs)
#     return settings.to_dict(extra_properties=['sik'])


@rest('/topdesk-data/<sik:[^/]+>', 'post', silent_result=True)
@returns(dict)
@arguments(sik=unicode, data=dict)
def api_get_topdesk_data(sik, data):
    return {}
#     return get_topdesk_data(sik, data['api_url'], data['username'], data['password'])
