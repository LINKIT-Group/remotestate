"""
Copyright (c) 2019 LINKIT, The Netherlands. All Rights Reserved.
Author(s): Anthony Potappel

This software may be modified and distributed under the terms of the
MIT license. See the LICENSE file for details.
"""

import sys
import re
import time
# pylint: disable=E0401
import boto3

# pylint: disable=E0402
from .exceptions import ResponseError
#from .aws_base import AWSBase
from .aws_base import get_region_name
from .aws_base import validate_aws
from .aws_bucket import validate_s3bucket_name


def time_string():
    """Return current time in micro-second (usec) as a string"""
    return str(round(time.time()*10**6))


def validate_name_dynamotable(table_name):
    """Validate if table name matches DynamoDB naming standards."""
    if not isinstance(table_name, str):
        ValueError('Input argument \"name\" must a string')

    if table_name.__len__() < 3 or table_name.__len__() > (255 - 5):
        # note: deduct 5 chars to allow postfix space (e.g. for .lock)
        return (False, 'TableName should be of length: [3-255]')
    if not re.match(r'^[a-zA-Z0-9]', table_name):
        return (False, 'BucketName should start with a lowercase letter or number')
    if re.search(r'[-\._]{2}', table_name):
        return (False, 'TableName can\'t contain two special characters [-, ., _] in a row')
    if not re.match(r'^[-a-zA-Z0-9\._]*$', table_name):
        return (False, re.sub(' +', ' ', 'TableName contains invalid character. \
                Allowed characters: [a-z, A-Z, 0-9, \'.\', \'-\', \'_\']'))

    return (True, 'Success')


class DynamoTable():
    """Create a DynamoTable that is viable for use by terraform states"""
    def __init__(self, table_name=None, auto_create=False):
        #super().__init__()

        (is_valid, error_message) = validate_name_dynamotable(table_name)
        if is_valid is False:
            raise ValueError(error_message)

        self.region_name = get_region_name()
        self.table_name = table_name
        self.client = boto3.client('dynamodb')
        self.resource = boto3.resource('dynamodb')

        if auto_create is True:
            self.create_tables(check_exist=True)

    def __info(self, message):
        """Internal info handler. Just a simple print for now."""
        print('I: table \"' + self.table_name + '\"->' + message)

    def __exit(self, message):
        """Internal error handler. Just a simple print and exit for now."""
        sys.exit('E: table \"' + self.table_name + '\"->' + message)

    def tables_exist(self):
        """Check if table already exists in our account."""
        try:
            response = self.client.describe_table(TableName=self.table_name + '.lock')
            validate_aws(response)
        except self.client.exceptions.ResourceNotFoundException:
            return False
        except ResponseError as exception_error:
            # un-expected response
            raise exception_error
        except Exception as exception_error:
            # catch other errors
            raise exception_error

        try:
            response = self.client.describe_table(TableName=self.table_name + '.s3')
            validate_aws(response)
        except self.client.exceptions.ResourceNotFoundException:
            return False
        except ResponseError as exception_error:
            # un-expected response
            raise exception_error
        except Exception as exception_error:
            # catch other errors
            raise exception_error

        return True

    def create_tables(self, check_exist=False):
        """Create new tables. Return True if succesful,
        also return True if tables already exists"""
        if check_exist is True:
            if self.tables_exist() is True:
                # safely return self
                self.__info('table exist in our account')
                return self

        # table does not yet exist in our account, try to create it
        try:
            # create lock table, used by Terraform to lock state
            table_lock = self.client.create_table(
                TableName=self.table_name + '.lock',
                AttributeDefinitions=[{'AttributeName': 'LockID', 'AttributeType': 'S'}],
                KeySchema=[{'AttributeName': 'LockID', 'KeyType': 'HASH'}],
                ProvisionedThroughput={'ReadCapacityUnits': 5,
                                       'WriteCapacityUnits': 5},
            )
            validate_aws(table_lock)
        except self.client.exceptions.ResourceInUseException:
            # this would be very rare to happen as we do a pre-check
            # nonetheless, we still catch for it and pass on as ok
            pass
        except ResponseError as exception_error:
            # can't read response, or we do not have the error code covered yet
            self.__exit('ResponseError when creating table: ' + exception_error.__str__())
        except Exception as exception_error:
            # oops, this exception is not yet covered
            raise exception_error

        # create s3 table, used to translate url to s3 bucket names
        try:
            table_s3 = self.client.create_table(
                TableName=self.table_name + '.s3',
                AttributeDefinitions=[{'AttributeName': 'GitURI', 'AttributeType': 'S'}],
                KeySchema=[{'AttributeName': 'GitURI', 'KeyType': 'HASH'}],
                ProvisionedThroughput={'ReadCapacityUnits': 5,
                                       'WriteCapacityUnits': 5},
            )
            validate_aws(table_s3)
        except self.client.exceptions.ResourceInUseException:
            # this would be very rare to happen as we do a pre-check
            # nonetheless, we still catch for it and pass on as ok
            pass
        except ResponseError as exception_error:
            # can't read response, or we do not have the error code covered yet
            self.__exit('ResponseError when creating table: ' + exception_error.__str__())
        except Exception as exception_error:
            # oops, this exception is not yet covered
            raise exception_error

        # wait till both tables exist
        try:
            self.client.get_waiter('table_exists').wait(TableName=self.table_name + '.lock')
            self.client.get_waiter('table_exists').wait(TableName=self.table_name + '.s3')
        except Exception as exception_error:
            # oops, this exception is not yet covered
            raise exception_error

        # if we made it up till here, tables have been created
        self.__info('new bucket created')
        return self

    def lookup_s3(self, bucket_uri=None, auto_create=False):
        """Lookup s3 real bucket name by querying the bucket_uri
        if auto_create is True, generate a new bucket name"""
        if not isinstance(bucket_uri, str):
            ValueError('Input argument \"bucket_uri\" must a string')

        table = self.resource.Table(self.table_name + '.s3')

        try:
            response = table.get_item(
                Key={'GitURI': bucket_uri},
            )
            validate_aws(response)

            value = response['Item']['BucketName']
            if not isinstance(value, str):
                # raise KeyError also when value is not of correct format
                raise KeyError
            return value
        except KeyError:
            # expected error when item is not in database, or if format is in-correct
            pass
        except ResponseError as exception_error:
            # can't read response, or we do not have the error code covered yet
            self.__exit('ResponseError when putting Dynamo table item: ' \
                        + exception_error.__str__())
        except Exception as exception_error:
            # oops, this exception is not yet covered
            raise exception_error

        if auto_create is False:
            return None

        # create a new value for this GitURI
        #   format: {{ GIT_HOST }}.{{ GIT_PATH }}.terraform-{{ CREATION_TIME }}
        # - remove repo name (last part)
        # - add '.terraform-${CREATION_TIME}}'
        # - replace '/' with '.' due to requirement of S3 naming standard
        bucket_name = self.table_name + '-' + time_string()

        # validate
        (is_valid, error_message) = validate_s3bucket_name(bucket_name)
        if is_valid is False:
            raise ValueError(error_message)

        # add item to DynamoDB
        try:
            response = table.put_item(
                Item={'GitURI': bucket_uri,
                      'BucketName': bucket_name}
            )
            validate_aws(response)
        except ResponseError as exception_error:
            # can't read response, or we do not have the error code covered yet
            self.__exit('ResponseError when putting Dynamo table item: ' \
                        + exception_error.__str__())
        except Exception as exception_error:
            # oops, this exception is not yet covered
            raise exception_error
        return bucket_name
