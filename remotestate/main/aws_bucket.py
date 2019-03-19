"""
Copyright (c) 2019 LINKIT, The Netherlands. All Rights Reserved.
Author(s): Anthony Potappel

This software may be modified and distributed under the terms of the
MIT license. See the LICENSE file for details.
"""

import sys
import re

# pylint: disable=E0401
import boto3

# pylint: disable=E0402
from .exceptions import ResponseError
#from .aws_base import AWSBase
from .aws_base import get_region_name
from .aws_base import validate_aws


def validate_s3bucket_name(bucket_name):
    """Validate if name matches S3 naming standards."""
    if not isinstance(bucket_name, str):
        ValueError('Input argument \"name\" must a string')

    if bucket_name.__len__() < 3 or bucket_name.__len__() > 63:
        return (False, 'BucketName should be of length: [3-63]')
    if re.search(r'[A-Z]', bucket_name):
        return (False, 'BucketName can\'t contain upper-case characters')
    if not re.match(r'^[a-z0-9]', bucket_name):
        return (False, 'BucketName should start with a lowercase letter or number')
    if re.search(r'[-\.]{2}', bucket_name):
        return (False, 'BucketName can\'t contain two special characters [-, .] in a row')
    if not re.match(r'^[-a-z0-9\.]*$', bucket_name):
        return (False, re.sub(' +', ' ', 'BucketName contains invalid character. \
                Allowed characters: [a-z, 0-9, \'.\', \'-\']'))

    return (True, 'Success')


class S3Bucket():
    """Create an S3Bucket that is viable for use by terraform states"""
    def __init__(self, bucket_name=None, auto_create=False):
        #super().__init__()

        (is_valid, error_message) = validate_s3bucket_name(bucket_name)
        if is_valid is False:
            raise ValueError(error_message)

        self.region_name = get_region_name()
        self.bucket_name = bucket_name
        self.client = boto3.client('s3')

        if auto_create is True:
            self.create_bucket() \
            .tighten_policy()


    def __info(self, message):
        """Internal info handler. Just a simple print for now."""
        print('I: bucket \"' + self.bucket_name + '\"->' + message)

    def __exit(self, message):
        """Internal error handler. Just a simple print and exit for now."""
        sys.exit('E: bucket \"' + self.bucket_name + '\"->' + message)

    def bucket_exist(self):
        """Check if bucket already exists in our account."""
        try:
            response = self.client.head_bucket(
                Bucket=self.bucket_name
            )
            validate_aws(response)
        except self.client.exceptions.ClientError:
            # Unfortunately boto3 also returns ClientError because AWS returns 404
            return False
        except ResponseError as exception_error:
            # If something else went wrong, assume bucket does not exist in our account
            return False
        except Exception as exception_error:
            # unknown error
            raise exception_error

        return True

    def bucket_owned(self):
        """Check if bucket already exists in our account, and is owned by us."""
        tag_set = {}

        try:
            # retrieve tags from our bucket
            bucket_tagging = self.client.get_bucket_tagging(Bucket=self.bucket_name)
            tag_set = bucket_tagging.get('TagSet')
        except self.client.exceptions.NoSuchBucket:
            # bucket does not exist in this account
            return False
        except self.client.exceptions.ClientError:
            # presumably bucket has no tagset and/ or something else is wrong.
            # either way, we must assume we do not own this bucket.
            return False
        except Exception as exception_error:
            # unknown error
            raise exception_error

        if not tag_set:
            # assume we do not own this bucket
            return False

        # Print out each tag
        found = [tag for tag in tag_set
                 if isinstance(tag.get('Key'), str) and tag['Key'] == 'managed_by' \
                 and isinstance(tag.get('Value'), str) and tag['Value'] == 'terraform-init']

        if found.__len__() == 1:
            # found the key/value we were looking for
            return True

        # not found the key/value we were looking for, assume bucket is not managed by us
        return False


    def create_bucket(self):
        """Create a new S3 bucket. Return True if succesful, or bucket already exists"""

        # if bucket does not exist in our account, we can't own it either
        if self.bucket_exist() is True:
            if self.bucket_owned() is False:
                # print error message and exit
                self.__exit('bucket exist in our account, but is not managed by terraform-init')

            # safely return self
            self.__info('bucket exist in our account and is also managed by terraform-init')
            return self

        # bucket does not yet exist in our account, try to create it
        try:
            response = self.client.create_bucket(
                ACL='private',
                Bucket=self.bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': self.region_name}
            )

            # check if response is correct
            validate_aws(response)

        except self.client.exceptions.BucketAlreadyOwnedByYou:
            # this would be very rare to happen as we do a pre-check
            # nonetheless, we still catch for it and return it as valid
            return self
        except self.client.exceptions.BucketAlreadyExists:
            # this will typicall happen when a bucket is owned by someone else.
            self.__exit('BucketAlreadyExists, not owned by us.')
        except self.client.exceptions.ClientError as exception_error:
            # other invalid input error (this will handle some other cases, e.g. InvalidBucketName)
            self.__exit('S3ResponseError when creating bucket: ' + exception_error.__str__())
        except ResponseError as exception_error:
            # can't read response, or we do not have the error code covered yet
            self.__exit('ResponseError when creating bucket: ' + exception_error.__str__())
        except Exception as exception_error:
            # oops, this exception is not yet covered
            raise exception_error

        try:
            response = self.client.put_bucket_tagging(
                Bucket=self.bucket_name,
                Tagging={
                    'TagSet': [
                        {
                            'Key': 'managed_by',
                            'Value': 'terraform-init'
                        },
                    ]
                }
            )
            validate_aws(response, expect_status_code=204)

        except ResponseError as exception_error:
            # can't read response, or we do not have the error code covered yet
            self.__exit('ResponseError when creating bucket: ' + exception_error.__str__())
        except Exception as exception_error:
            # oops, this exception is not yet covered
            raise exception_error

        # if we made it up till here, bucket has been created
        self.__info('new bucket created')
        return self


    def tighten_policy(self):
        """Put a strict policy on the bucket to prevent public usage"""
        if self.bucket_owned() is not True:
            self.__exit('cant update policy, bucket is not managed by us.')

        try:
            response = self.client.put_public_access_block(
                Bucket=self.bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                },
            )
            validate_aws(response)
        except ResponseError as exception_error:
            # can't read response, or we do not have the error code covered yet
            self.__exit('ResponseError when tightening policy: ' + exception_error.__str__())
        except Exception as exception_error:
            # oops, this exception is not yet covered
            raise exception_error

        # add version control
        try:
            response = self.client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={
                    'Status': 'Enabled',
                }
            )
            validate_aws(response)
        except ResponseError as exception_error:
            # can't read response, or we do not have the error code covered yet
            self.__exit('ResponseError when enabling versioning: ' + exception_error.__str__())
        except Exception as exception_error:
            # oops, this exception is not yet covered
            raise exception_error

        # policy succesfully updated
        self.__info('strict policy enabled')
        return self
