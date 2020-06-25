# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import os
import boto3
from botocore.exceptions import ClientError

from datetime import datetime, timedelta
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

##############################################################################
# Function to send SNS notification
##############################################################################
def snsNotify(message):
    try:
        sns = boto3.resource('sns',region_name=Region)
        topic = sns.Topic(SNSTopic)
        response = topic.publish(
                Subject='Storage Activity Status Report',
                Message=message
        )
        return
    except ClientError as e:
        logger.info(e)

##############################################################################
# Function to get list of storage devices based on Storage Type selected by User
##############################################################################
def getStorageDevices(storageType):
    deviceList=[]
    if storageType == "LUSTRE" or storageType == "WINDOWS":
        client = boto3.client('fsx')
    
        try:
            response = client.describe_file_systems()
            filesystemList=response['FileSystems']
            for filesystem in filesystemList:
                if filesystem['FileSystemType'] != storageType:
                    print("Ignoring storage type:",filesystem['FileSystemType']," file system id:",filesystem['FileSystemId'])
                    continue
                else:
                    FileSystemId = filesystem['FileSystemId']
                    print("Found storage type:",filesystem['FileSystemType']," file system id:", FileSystemId)
                    deviceList.append(FileSystemId)
        except ClientError as e:
                logger.info(e)
        return(deviceList)
    else:
        logger.info("Additional storage types not supported")
        return(deviceList)
        
def lambda_handler(event, context):
    global Region
    global SNSTopic
    
    storageType = os.environ.get("StorageType")
    Period = int(os.environ.get("Period"))
    Region = os.environ.get("Region")
    SNSTopic = os.environ.get("SNSTopic")
    
    storageList=getStorageDevices(storageType)
    
    startTime=datetime.now()-timedelta(days=Period)
    endTime=datetime.now()
    
    storageActivityList={}
    for storage in storageList:
        if storage != "":
            storageIOPS={}
            cwclient = boto3.client('cloudwatch')
            try:
                response = cwclient.get_metric_data(
                                MetricDataQueries=[
                                    {
                                        'Id': 'm1',
                                        'MetricStat': {
                                            'Metric': {
                                                'Namespace': 'AWS/FSx',
                                                'MetricName': 'DataReadOperations',
                                                'Dimensions': [
                                                    {
                                                        'Name': 'FileSystemId',
                                                        'Value': storage
                                                    },
                                                ]
                                            },
                                            'Period': 60,
                                            'Stat': 'Sum',
                                            'Unit': 'Count'
                                        },
                                        'Label': 'DataReadOperations',
                                        'ReturnData': False,
                                    },
                                    {
                                        'Id': 'm2',
                                        'MetricStat': {
                                            'Metric': {
                                                'Namespace': 'AWS/FSx',
                                                'MetricName': 'DataWriteOperations',
                                                'Dimensions': [
                                                    {
                                                        'Name': 'FileSystemId',
                                                        'Value': storage
                                                    },
                                                ]
                                            },
                                            'Period': 60,
                                            'Stat': 'Sum',
                                            'Unit': 'Count'
                                        },
                                        'Label': 'DataWriteOperations',
                                        'ReturnData': False,
                                    },
                                    {
                                        'Id': 'm3',
                                        'MetricStat': {
                                            'Metric': {
                                                'Namespace': 'AWS/FSx',
                                                'MetricName': 'MetadataOperations',
                                                'Dimensions': [
                                                    {
                                                        'Name': 'FileSystemId',
                                                        'Value': storage
                                                    },
                                                ]
                                            },
                                            'Period': 60,
                                            'Stat': 'Sum',
                                            'Unit': 'Count'
                                        },
                                        'Label': 'MetadataOperations',
                                        'ReturnData': False,
                                    },
                                    {
                                        'Id': 'e1',
                                        'Expression': "SUM(METRICS())/PERIOD(m1)",
                                        'Label': 'Total IOPS'
                                    },
                                ],
                                StartTime=startTime,
                                EndTime=endTime
                            )
                totalIopsValues=response['MetricDataResults'][0]['Values']
                averageIops=sum(totalIopsValues)/len(totalIopsValues)
                totalIopsValues.sort()
                peakIops=totalIopsValues[-1]
                
                storageIOPS['averageIops']=averageIops
                storageIOPS['peakIops']=peakIops
                storageActivityList[storage]=storageIOPS
            except ClientError as e:
                logger.info(e)
        else:
            logger.info("No storage device passed in event, aborting")
            return
    message="Storage Activity Report for selected period of "+str(Period)+" is:\n"+json.dumps(storageActivityList)
    logger.info(message)  
    snsNotify(message)
