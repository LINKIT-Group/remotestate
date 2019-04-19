"""
Copyright (c) 2019 LINKIT, The Netherlands. All Rights Reserved.
Author(s): Anthony Potappel

This software may be modified and distributed under the terms of the
MIT license. See the LICENSE file for details.
"""

import re
from urllib.parse import urlparse


def validate_url(url_name):
    """Validate if url matches standard"""
    if not isinstance(url_name, str):
        ValueError('Input argument \"url_name\" must a string')

    if url_name.__len__() < 1 or url_name.__len__() > 2000:
        #https://stackoverflow.com/questions/417142/
        return (False, 'url_name should be of reasonable length: [1-2000]')

    # only accept filter reasonably safe characters.
    # this might be to strict, but better safe than sorry.
    if not re.match(r'^[-a-zA-Z0-9\.:_\/@+\?&=%]*$', url_name):
        return (False, re.sub(' +', ' ', 'url_name contains (reasonably) unsafe \
                characters, we must be strict to guantuee broad compatibility'))

    return (True, 'Success')
