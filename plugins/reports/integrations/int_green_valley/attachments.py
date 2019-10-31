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

from base64 import b64encode
from cStringIO import StringIO

from google.appengine.api import urlfetch

from PIL import Image


def _maybe_resize_image(image, content_type):
    img_file = StringIO(image)
    img = Image.open(img_file)
    width, height = img.size
    max_width = 2560
    if width < max_width:
        return image
    new_height = int(float(height) / float(width) * max_width)
    result_image = img.resize((max_width, new_height))  # type: Image.Image
    result = StringIO()
    image_format = 'png' if content_type == 'image/png' else 'jpeg'
    result_image.save(result, image_format)
    return result.getvalue()


def get_attachment_content(url):
    """
    Converts an url to base64 encoded content. Compresses images if they are too large.
    """
    result = urlfetch.fetch(url)  # type: urlfetch._URLFetchResult
    content_type = result.headers.get('content-type', '')
    if content_type.startswith('image'):
        content = _maybe_resize_image(result.content, content_type)
        base64_attachment = b64encode(content)
    else:
        base64_attachment = b64encode(result.content)
    return base64_attachment, content_type
