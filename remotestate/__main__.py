#!/usr/bin/env python3
"""
Copyright (c) 2019 LINKIT, The Netherlands. All Rights Reserved.
Author(s): Anthony Potappel

This software may be modified and distributed under the terms of the
MIT license. See the LICENSE file for details.
"""

import os
import sys
import argparse

from .main.make_backend import BackendAWS
from .main.tfconfig import terraform_provider

def main():
    """This function is called when run as python3 -m ${MODULE}
    Parse any additional arguments and call required module functions."""

    module_name = '.'.join(__loader__.name.split('.')[0:-1])

    argument_parser = argparse.ArgumentParser(
        prog=module_name,
        description='Create a remotestate backend to hold infra state configration'
    )

    argument_parser.add_argument('--git', action='store', nargs=1, required=True,
                                 help='GIT is the name of a local repository directory')
    argument_parser.add_argument('--provider', action='store', nargs=1, required=False,
                                 default=['auto'],
                                 help='PROVIDER used to create the remotestate. \
                                       Defaults to "auto"')

    args = argument_parser.parse_args(sys.argv[1:])

    git_directory = args.git[0]
    backend_provider = args.provider[0]

    if backend_provider == "auto":
        # discover based on project configuration
        # reset to None
        backend_provider = None

        # check terraform first
        terraform_provider_file = git_directory + '/terraform/provider.tf'
        if os.path.isfile(terraform_provider_file) is True:
            backend_provider = terraform_provider(terraform_provider_file)
        else:
            # no other auto configurations to check yet
            pass
        if backend_provider is None:
            print('Cant retrieve backend provider automatically')
            sys.exit(1)

    if backend_provider == "aws":
        backend = BackendAWS(git_directory=git_directory)
        backend.create()
    else:
        print('Unknown backend provider: ' + str(backend_provider))
        sys.exit(1)

    return 0


if __name__ == '__main__':
    sys.exit(main())
