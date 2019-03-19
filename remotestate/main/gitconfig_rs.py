"""
Copyright (c) 2019 LINKIT, The Netherlands. All Rights Reserved.
Author(s): Anthony Potappel

This software may be modified and distributed under the terms of the
MIT license. See the LICENSE file for details.
"""

import re
import warnings
import configparser

# pylint: disable=E0402
from .system_execute import system_call
from .validators import validate_url


def configparser_config(filename):
    """Return configparser config object from a filename"""
    config = configparser.ConfigParser()
    config.read(filename)
    return config


def retrieve_key(filename, classifier, key='url', name=None):
    """Retrieve a key from a specified classifier"""
    config = configparser_config(filename)
    if not isinstance(config, configparser.ConfigParser):
        return None

    if name is None:
        # find all submodule sections
        sections = [section for section in config.sections()
                    if re.match(r'^' + classifier + ' "[-a-zA-Z0-9_=/]*"$', section)]
        modules = {re.sub(r'^' + classifier + ' "|"$', '', section): config.get(section, key)
                   for section in sections}
    else:
        # search a particular section
        try:
            modules = {name: config.get(classifier + ' "' + name + '"', key)}
        except configparser.NoSectionError:
            return None

    # validate urls before returning
    if key == 'url':
        for module_name, module_url in modules.items():
            (is_valid, error_message) = validate_url(module_url)
            if is_valid is False:
                warnings.warn('\nsection ' + module_name + ' contains invalid url')
                raise ValueError(error_message)
    else:
        # not implemented tests for other types yet
        pass
    return modules


def remote_read(git_directory='.', key='url', name=None):
    """Retrieve url value from .git/config in dictionary format,
    if name is undefined, return (a dictionary of) all remotes"""
    return retrieve_key(git_directory + '/.git/config', 'remote', key=key, name=name)


def current_branch(git_directory='.'):
    """Retrieve current branch for a given git_repository"""
    return_code, stdout, stderr = system_call(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                              pathname=git_directory)

    if stderr:
        warnings.warn('\n'.join(stderr))

    if return_code != 0 or not stdout:
        return None

    return stdout[0]
