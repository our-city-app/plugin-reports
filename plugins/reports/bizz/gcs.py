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

import cloudstorage
from google.appengine.api.blobstore import blobstore

CHUNK_SIZE = 1024 * 1024


def read_file_in_chunks(file_obj, chunk_size=CHUNK_SIZE):
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        yield chunk


def is_file_available(filepath):
    try:
        cloudstorage.stat(filepath)
        return True
    except cloudstorage.errors.NotFoundError:
        return False


def upload_to_gcs(file_data, content_type, file_name):
    """
    Args:
        file_data (str or file-like object)
        content_type (unicode)
        file_name (unicode)
    Returns:
        blob_key (unicode): An encrypted `BlobKey` string.
    """
    # this can fail on the devserver for some reason
    with cloudstorage.open(file_name, 'w', content_type=content_type) as f:
        if isinstance(file_data, basestring):
            f.write(file_data)
        else:
            try:
                for chunk in read_file_in_chunks(file_data):
                    f.write(chunk)
            except AttributeError:
                raise ValueError('file_data must be a file-like object')

    return blobstore.create_gs_key('/gs' + file_name).decode('utf-8')
