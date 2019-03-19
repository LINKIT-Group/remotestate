"""
Copyright (c) 2019 LINKIT, The Netherlands. All Rights Reserved.
Author(s): Anthony Potappel

This software may be modified and distributed under the terms of the
MIT license. See the LICENSE file for details.
"""

import os
import re
import warnings


def terraform_provider(provider_file):
    """Parse provider_file (e.g. provider.tf) file to get provider"""
    if not os.path.isfile(provider_file):
        warnings.warn('cant access provider_file:' + provider_file)
        return None

    try:
        with open(provider_file, 'r') as infile:
            data = infile.read()
    except IOError:
        warnings.warn('cant access provider_file:' + provider_file)
        return None
    except Exception as exception:
        # unknown error
        raise exception

    # remove newlines for easy regex
    contents = ' '.join(data.strip().split('\n'))

    # remove double spaces and check if we can find 'provider "${provider_name} {'
    match = re.search(' ?provider ["\'][-a-zA-Z0-9]*["\'] ?{', re.sub(' +', ' ', contents))
    if not match:
        return None

    # strip out provider name
    match = re.sub('.*provider |[ "\'{]*', '', match.group())

    # check if its a reasonable length
    if 32 > match.__len__() > 1:
        return match
    return None
