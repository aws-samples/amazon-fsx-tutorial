#! /usr/bin/env python3

import argparse
import os
import json
import boto3
from botocore.exceptions import ClientError
import subprocess
import re
import time

invalid_hsm_states=["dirty","released","lost","non-release","non-archive"]


def parseArguments():

        parser = argparse.ArgumentParser(description='Cache Eviction script to release least recently accessed files when FSx for Lustre file system free capacity Alarm is triggered')
        parser.add_argument_group('Required arguments')
        parser.add_argument(
                                '-mountpath', required=True, help='Please specify the FSx for Lustre file system mount path')
        parser.add_argument(
                                '-lwmfreecapacity', required=True, help='Low water Mark for free capacity on your file system.When utilization drops to this value hsm release will be triggered')
        parser.add_argument(
                                '-hwmfreecapacity', required=True, help='High water Mark for free capacity on your file system. hsm release will release space up to this value,'
                                'when the script can find sufficient number of least recently accessed files')
        parser.add_argument(
                                '-minage', required=True,
                                help='Please specify number of days since last access. Files not accessed for more than this number of days will be considered for hsm release')
        parser.add_argument(
                                '-loggroup', required=True,
                                help='Please specify Cloudwatch log group to write script output')
        parser.add_argument(
                                '-sns', required=True,
                                help='Please specify SNS topic to send notification')
        parser.add_argument(
                                '-region', required=True,
                                help='Please specify AWS region of where this solution is used')
        args = parser.parse_args()
        return(args)

##############################################################################
# Function to write output to cloudwatch log stream
##############################################################################
def logEvents(message):
        try:
            response = logs.describe_log_streams(
                        logGroupName=logGroup,
                        orderBy='LastEventTime',
                        descending=True
                        )
        except ClientError as e:
            raise e

        #print("Log group response is:", response)

        logStream=response['logStreams'][0]['logStreamName']
        #print("Latest log stream is:", logStream)

        sequenceToken=response['logStreams'][0]['uploadSequenceToken']

        timestamp = int(round(time.time() * 1000))

        response = logs.put_log_events(
                            logGroupName=logGroup,
                            logStreamName=logStream,
                            sequenceToken=sequenceToken,
                            logEvents=[
                                {
                                    'timestamp': timestamp,
                                    'message': time.strftime('%Y-%m-%d %H:%M:%S')+'\t'+message
                                }
                            ]
                    )
        return

##############################################################################
# Function to send SNS notification
##############################################################################
def snsNotify(message):
        try:
            sns = boto3.resource('sns',region_name=region)
            topic = sns.Topic(snsTopicArn)
            response = topic.publish(
                    Subject='FSxL Cache Eviction Status',
                    Message=message
            )
            return
        except Exception as e:
            raise e


##############################################################################
# Function to release space using hsm_release. The function will release list of least recently accessed files.
##############################################################################
def releaseInfrequentlyAccessedFiles(filesToRelease,freeCapacityHighWaterMark,freeCapacityLowWaterMark):
        targetedSpaceRelease=int(freeCapacityHighWaterMark)-int(freeCapacityLowWaterMark)
        totalSpaceReleased=0
        hsmreleaseList=[]
        for filename,attrbs in sorted (filesToRelease.items(), key=lambda x: x[1]['atime'], reverse=True):

                cmd = "sudo lfs hsm_release "+key
                try:
                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, universal_newlines=True)
                    hsmreleaseList.append(filename)
                    print("Initiated hsm_release for file:",filename, " with access time:", attrbs['atime']," and size:",attrbs['size']," and hsm_state:",attrbs['state'])
                except Exception as e:
                    print("ERROR:", e)
                    logEvents(e)

                totalSpaceReleased=totalSpaceReleased+attrbs['size']
                print("Target Space Release is:", targetedSpaceRelease, " current total space released:", totalSpaceReleased," after archiving:", filename)
                if(totalSpaceReleased > targetedSpaceRelease):
                    message="Triggered hsm_release on files identified as suitable for release. Sufficient files were identified to release space up to the High Water Mark. Aborting space release for additional files. hsm release is a non blocking call and will continue to release space in the background, so please wait for few minutes to check your file system capacity\n"+json.dumps(hsmreleaseList)
                    print(message)
                    logEvents(message)
                    snsNotify(message)
                    message="Total Space release triggered by hsm_release:"+str(totalSpaceReleased)
                    logEvents(message)
                    break
        
        if(totalSpaceReleased < targetedSpaceRelease):
            message="Triggered hsm_release on files identified as suitable for release. However, file system free capacity  will be still below the target  High Water Mark as no additional files suitable for hsm_release. hsm release is a non blocking call that runs in the background, so please wait for few minutes to check your file system capacity\n"+json.dumps(hsmreleaseList)
            print(message)
            logEvents(message)
            snsNotify(message)

            message="Total Space release triggered by hsm_release:"+str(totalSpaceReleased)
            logEvents(message)
        return


##############################################################################
# Function to check if file exists in FSx by verifying hsm_state
##############################################################################
def gethsmState(fileList):
        ignoreFileList={}
        for key in list(fileList.keys()):
            cmd = "sudo lfs hsm_state "+key
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, universal_newlines=True)
                output = p.communicate()[0]
            except Exception as e:
                print("ERROR:", e)
                logEvents(e)
            #fileList[key]['state']=output.split(":")[1]

            if "exists archived"  in output.split(":")[1]:
                for hsmState in invalid_hsm_states:
                    if re.search(hsmState,output.split(":")[1]):
                        ignoreFileList[key]=output.split(":")[1]
                        print("Ignoring file as hsm state not valid for release:", key,"is:", output.split(":")[1])
                        fileList.pop(key)
                        break
                    else:
                        fileList[key]['state']=output.split(":")[1]
            else:
                print("Ignoring file as hsm state not valid for release:", key,"is:", output.split(":")[1])
                ignoreFileList[key]=output.split(":")[1]
                fileList.pop(key)

            message="List of files ignored as the  hsm state of file was  not suitable for space release:\n"+json.dumps(ignoreFileList)
        logEvents(message)
        return(fileList)


##############################################################################
# Function to query access time and size of files returned by getInfrequentlyAccessedFiles function.
##############################################################################
def getFileAttr(outputFileList):
        fileList={}
        for file in outputFileList.split("\n"):
            if len(file) == 0:
                continue
            fileList[file]={}
            #print("File is:", file)
            st = os.stat(file)
            print("Filename:", file,"-","Size:", st.st_size, "file access time:", st.st_atime)
            fileList[file]['size']=st.st_size
            fileList[file]['atime']=st.st_atime

        #print("Dictionary is:", json.dumps(fileList))
        message="Successfully generated last Access time and size for files\n"+json.dumps(fileList)
        logEvents(message)

        gethsmState(fileList)
        #print("Final file List is:", json.dumps(fileList))
        return(fileList)



##############################################################################
# Function to get a list of Files that have not been accessed for N days. 
# Script currently excludes files that are smaller than 4KB in size
##############################################################################
def getInfrequentlyAccessedFiles(atime,mountPath):
        cmd = "lfs find "+mountPath+"  --atime +"+str(atime)+" --size +4k -print -type f"
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, universal_newlines=True)
            output = p.communicate()[0]
            print("lfs find output for files not accessed for more than:", atime," is:", output)
        except Exception as e:
            print("ERROR:", e)
            logEvents(e)

        return(output)

##############################################################################
# Main function
##############################################################################
def main():
        global logGroup
        global logs
        global snsTopicArn
        global region

        args = parseArguments()

        ### Confirm all required parameters have been passed.
       # if args.mountpath == "" or args.lwmfreecapacity == "" or args.hwmfreecapacity == "" or args.minage == "" or  args.loggroup == "" or args.region =="" or args.sns == "":
       #     message="ERROR: Insufficient number of arguments"
       #     print(message)
       #     logEvents(message)
       #     snsNotify(args.sns,message)
       # else:
        logGroup=args.loggroup
        freeCapacityLowWaterMark=args.lwmfreecapacity
        freeCapacityHighWaterMark=args.hwmfreecapacity
        filesMinAge=args.minage
        mountPath=args.mountpath
        snsTopicArn=args.sns
        region=args.region

        logs = boto3.client('logs',region_name=region)

        try:
            response = logs.describe_log_streams(
                        logGroupName=logGroup,
                        orderBy='LastEventTime',
                        descending=True
                        )
        except ClientError as e:
            snsNotify(message)

        logStream=response['logStreams'][0]['logStreamName']
        sequenceToken=response['logStreams'][0]['uploadSequenceToken']

        ### Trigger function to run lfs find to list all files that have not been accessed for more than N(filesMinAge) Days 
        fileList=getInfrequentlyAccessedFiles(filesMinAge,mountPath)
        if fileList == "":
            message="Unable to find files that have not been accessed for more than: "+filesMinAge+" days"
            print(message)
            logEvents(message)
            exit()
        else:
            ### Add logic to validate FSx is mounted on the input mount path###
            message="Identified files not accessed for more than:"+filesMinAge+" days"+"\n"+fileList+" . See file list below:"
            logEvents(message)

            ###  Trigger function to get size and access time for files generated in getInfrequentlyAccessedFiles function
            filesToRelease=getFileAttr(fileList)
            ###  Trigger function to release space
            releaseInfrequentlyAccessedFiles(filesToRelease,freeCapacityHighWaterMark,freeCapacityLowWaterMark)


##############################################################################
# Run from command line
##############################################################################
if __name__ == '__main__':
        main()

