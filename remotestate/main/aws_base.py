"""
Copyright (c) 2019 LINKIT, The Netherlands. All Rights Reserved.
Author(s): Anthony Potappel

This software may be modified and distributed under the terms of the
MIT license. See the LICENSE file for details.
"""
# pylint: disable=E0401
import boto3

# pylint: disable=E0402
from .exceptions import ResponseError

#class AWSBase():
#    """AWS Baseclass for functions that apply to all AWS related classes"""
#    def __init__(self):
#        self.region_name = None

def get_region_name():
    """Return name of the current region"""
    #if not isinstance(self.region_name, str):
    session = boto3.session.Session()
    return session.region_name
    #self.region_name = session.region_name
    #return self.region_name


def validate_aws(response, expect_status_code=200):
    """Validate AWS API resonse with a HTTPStatusCode filter.
    Raise a the custom ResponseError Exception if a problem has occured.
    Function should only be used within a Try/ Exception block."""

    # check if response meets our standards
    if not isinstance(response.get('ResponseMetadata'), dict):
        raise ResponseError('No response received by API')
    if not isinstance(response['ResponseMetadata'].get('HTTPStatusCode'), int):
        raise ResponseError('No HTTPStatusCode received by API')

    # check if call is succesful
    status_code = response['ResponseMetadata']['HTTPStatusCode']
    if status_code != expect_status_code:
        raise ResponseError('HTTPStatusCode=' + str(status_code))

    return True
