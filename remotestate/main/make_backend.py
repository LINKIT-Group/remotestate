"""
Copyright (c) 2019 LINKIT, The Netherlands. All Rights Reserved.
Author(s): Anthony Potappel

This software may be modified and distributed under the terms of the
MIT license. See the LICENSE file for details.
"""

import sys
import re

# pylint: disable=E0401
from jinja2 import Template

# pylint: disable=E0402
from . import gitconfig_rs as gitconfig
from .aws_bucket import S3Bucket
from .aws_table import DynamoTable


class Backend():
    """Parent function for Backend handlers"""
    def __init__(self,
                 git_directory='.',
                 backend_template_file='etc/backend_auto.tf.j2'):

        self.backend_template_file = backend_template_file
        self.git_directory = git_directory

        # required vars for backend file
        self.keyvalue_map = {}

        self.table_name = None
        self.table_lock = None
        self.region_name = None


    def update_backend_terraform(self):
        """Write a new terraform backend file, by reading template file and update this
        with retrieved variables from backend_provider and current git project"""
        with open(self.backend_template_file, 'r') as template_file:
            template_data = template_file.read().strip()

        template = Template(template_data)
        rendered = template.render(BUCKET_NAME=self.keyvalue_map.get('bucket_name'),
                                   TABLE_LOCK=self.table_name + '.lock',
                                   REPO_NAME=self.keyvalue_map.get('repo_name'),
                                   BRANCH_NAME=self.keyvalue_map.get('branch_name'),
                                   REGION_NAME=self.region_name)

        # create backend directory (e.g. ./build) if not yet exist
        #if not os.path.isdir(os.path.dirname(self.backend_output_file)):
        #    os.makedirs(os.path.dirname(self.backend_output_file))

        # write rendered backend file
        backend_output_file = self.git_directory + '/terraform/backend_auto.tf'
        with open(backend_output_file, 'w') as output_file:
            output_file.write(rendered)

    def source_git(self):
        """Source and update variables that can be retrieved from current GIT Repository
        Following items are set:
            - self.table_name -> required in retrieve_tables(), and update_backend_terraform()
            - self.bucket_uri -> required in retrieve_bucket_name()
            - self.repo_name -> required in update_backend_terraform()
            - self.branch_name -> required in update_backend_terraform()
        """

        # retrieve full url from the GIT repository
        git_url_project = gitconfig.remote_read(git_directory=self.git_directory,
                                                name='origin')
        if not isinstance(git_url_project, dict) \
        or not isinstance(git_url_project.get('origin'), str):
            raise ValueError(re.sub(' +', ' ', 'giturl not found, location searched: \
                             .git/config -> [remote \"origin\"] -> url'))
        git_url_project = git_url_project['origin'].lower()

        # create a clean host_path (remove uri-vars)
        host_path = re.sub(r'.*:\/\/|.*@|:', '', '/'.join(git_url_project.split('/')[0:-1]))
        git_host = host_path.split('/')[0]
        git_path = '.'.join(host_path.split('/')[1:])

        self.keyvalue_map['repo_name'] = re.sub(r'\.git$', '', git_url_project.split('/')[-1])
        self.keyvalue_map['bucket_uri'] = git_host + '/' + git_path + '/' \
                                          + self.keyvalue_map['repo_name']
        self.keyvalue_map['branch_name'] = gitconfig.current_branch(self.git_directory)
        if not isinstance(self.keyvalue_map['branch_name'], str):
            raise ValueError('gitbranch not of correct format')

        self.table_name = 'terraform.' + \
                          '.'.join(self.keyvalue_map['bucket_uri'].split('/')[0:-1])


class BackendAWS(Backend):
    """Backend handler for AWS"""
    def __init__(self, git_directory='.'):
        super().__init__(git_directory=git_directory)
        self.bucket = None
        self.table = None

    def retrieve_tables(self):
        """Retrieve DynamoDB tables"""
        try:
            self.table = DynamoTable(table_name=self.table_name,
                                     auto_create=True)
        except ValueError as error:
            print(error.__str__())
            sys.exit(1)
        except Exception as error:
            raise error
        return self

    def retrieve_bucket_name(self):
        """Retrieve s3 bucket_name"""
        # if Table object is not yet set, retrieve this first
        if self.table is None:
            self.retrieve_tables()

        try:
            self.keyvalue_map['bucket_name'] = \
                self.table.lookup_s3(bucket_uri=self.keyvalue_map['bucket_uri'],
                                     auto_create=True)
        except ValueError as error:
            print(error.__str__())
            sys.exit(1)
        except Exception as error:
            raise error
        return self

    def retrieve_bucket(self):
        """Retrieve S3 Bucket object"""
        # if bucket_name is not yet set, retrieve this first
        if not isinstance(self.keyvalue_map.get('bucket_name'), str):
            self.retrieve_bucket_name()

        try:
            self.bucket = S3Bucket(bucket_name=self.keyvalue_map['bucket_name'],
                                   auto_create=True)
        except ValueError as error:
            print(error.__str__())
            sys.exit(1)
        except Exception as error:
            raise error

    def create(self):
        """Create all Backend items, and update Terraform backend file when succesful"""
        # retrieve variables from current GIT repository
        self.source_git()

        # if Bucket object is not yet set, retrieve this first
        if self.bucket is None or not isinstance(self.keyvalue_map.get('bucket_name'), str):
            self.retrieve_bucket()

        # retrieve items required for backend file
        self.region_name = self.bucket.region_name

        # all variables should be set, updated backend file
        self.update_backend_terraform()
