import json
import os
import time
import boto3
import sys, getopt
from urllib.parse import urlparse

if os.environ['AWS_PROFILE'] == 'localstack':
    sqs = boto3.client('sqs', region_name=os.environ['AWS_REGION'],
                        endpoint_url=os.environ['LOCALSTACK_ENDPOINT_URL'])
else:
    boto3.setup_default_session(profile_name=os.environ['AWS_PROFILE'])
    sqs= boto3.client('sqs')

def generate_payload(s3_uri, collection, size):
    filename = os.path.basename(s3_uri)
    parsed_uri = urlparse(s3_uri)
    bucket = parsed_uri.netloc
    path = parsed_uri.path[1:len(parsed_uri.path)-len(filename)-1]
    payload = { "cumulu_meta": 
        {
            "cumulus_version": "11.1.1",
            "execution_name": f"{collection}-{filename}-{int(time.time())}",
            "message_source": "sfn",
            "queueExecutionLimits": {
                "https://sqs.us-west-2.amazonaws.com/349778025075/ghrcw-backgroundJobQueue": 900,
                "https://sqs.us-west-2.amazonaws.com/349778025075/ghrcw-backgroundProcessing": 5,
                "https://sqs.us-west-2.amazonaws.com/349778025075/ghrcw-near-real-time": 900,
                "https://sqs.us-west-2.amazonaws.com/349778025075/ghrcw-ongoing": 900
            },
            "state_machine": "arn:aws:states:us-west-2:349778025075:stateMachine:ghrcw-IngestGranule",
            "system_bucket": "ghrcw-internal",
            "workflow_start_time": None,
            "parentExecutionArn": "arn:aws:states:us-west-2:349778025075:execution:ghrcw-DiscoverGranules:isslis_v2_nrt-947ed5cb-0d37-4846-83e9-97d5f85c6e3a"
        },
        "exception": None,
        "meta": {
            "buckets": {
                "dashboard": {
                    "name": "ghrcw-dashboard",
                    "type": "public"
                },
                "internal": {
                    "name": "ghrcw-internal",
                    "type": "internal"
                },
                "orca_default": {
                    "name": "prod-orca-glacier-archive",
                    "type": "orca"
                },
                "private": {
                    "name": "ghrcw-private",
                    "type": "private"
                },
                "protected": {
                    "name": "ghrcw-protected",
                    "type": "protected"
                },
                "public": {
                    "name": "ghrcw-public",
                    "type": "public"
                },
                "sharedprivate": {
                    "name": "ghrcw-private",
                    "type": "sharedprivate"
                }
            },
            "cmr": {
                "clientId": "ghrc_daac",
                "cmrEnvironment": "OPS",
                "cmrLimit": 100,
                "cmrPageSize": 50,
                "oauthProvider": "launchpad",
                "passwordSecretName": "ghrcw-message-template-cmr-password20200309200329692700000005",
                "provider": "GHRC_DAAC",
                "username": "ghrc_daac"
            },
            "collection": {
            "name":"gpmkdmx2ifld",
            "version":"1",
            "dataType":"gpmkdmx2ifld",
            "process":"metadataextractor",
            "url_path":"gpmkdmx2ifld__1",
            "duplicateHandling":"replace",
            "granuleId":"^Level2_KDMX_.*\\.(ar2v)$",
            "granuleIdExtraction":"^((Level2_KDMX_).*)",
            "reportToEms":True,
            "sampleFileName":"Level2_KDMX_20130618_0148.ar2v",
            "meta":{
                "provider_path":"gpmkdmx2ifld/fieldCampaigns/gpmValidation/ifloods/NEXRAD2/KDMX/data/",
                "hyrax_processing":"false",
                "large_dataset": "true",
                "metadata_extractor":[
                {
                    "regex":"^Level2_KDMX_(.*).*\\.(ar2v)$",
                    "module":"netcdf"
                }
                ]
            },
            "files":[
                {
                "bucket":"public",
                "regex":"^Level2_KDMX_(.*).*\\.cmr.(xml|json)$",
                "sampleFileName":"Level2_KDMX_20130618_0148.ar2v.cmr.xml"
                },
                {
                "bucket":"protected",
                "regex":"^Level2_KDMX_(.*).*(ar2v)$",
                "sampleFileName":"Level2_KDMX_20130618_0148.ar2v"
                }
            ]
        },
            "distribution_endpoint": "https://data.ghrc.earthdata.nasa.gov/",
            "launchpad": {
                "api": "https://api.launchpad.nasa.gov/icam/api/sm/v1",
                "certificate": "launchpad.pfx",
                "passphraseSecretName": "ghrcw-message-template-launchpad-passphrase20200309200328262000000001"
            },
            "provider": {
                "id": "private_bucket",
                "globalConnectionLimit": 900,
                "host": "ghrcw-private",
                "protocol": "s3",
                "createdAt": 1592857271267,
                "updatedAt": 1592857271267
            },
            "stack": "ghrcw",
            "template": "s3://ghrcw-internal/ghrcw/workflow_template.json",
            "workflow_name": "IngestGranule",
            "workflow_tasks": {}
        },
        "payload": {
            "granules": [
                {
                    "granuleId": filename,
                    "dataType": collection,
                    "version": "1",
                    "files": [
                        {
                            "bucket": "ghrcw-protected",
                            "checksum": "",
                            "checksumType": "",
                            "filename": s3_uri,
                            "name": filename,
                            "path": path,
                            "size": int(size),
                            "time": "1655328855.0",
                            "type": ""
                        }
                    ],
                    "createdAt": 1655328929725
                }
            ]
        }
    }
    
    return payload


def send_to_sqs(payload, sqs_name):
        
    resp = sqs.create_queue(QueueName=sqs_name)
    que_url = resp["QueueUrl"]
    sqs.send_message(QueueUrl=que_url, MessageBody=json.dumps(payload))
    
    resp = sqs.receive_message(QueueUrl=que_url, MaxNumberOfMessages=1)
    
    for message in resp.get("Messages", []):
        message_body = message["Body"]
        print(f"{message_body}\n\n")
        
        
def start_execution(payload):
    
    sfn_client = boto3.client('stepfunctions')
    resoponse = sfn_client.start_execution(
        stateMachineArn="arn:aws:states:us-west-2:349778025075:stateMachine:ghrcw-IngestGranule",
        input= f"""{payload}""")
    print(resoponse)


def reingest(csv_path, collection, sqs_name):
    
    with open(csv_path, 'r', encoding='utf-8') as in_file:
        while True:
            line = in_file.readline()
            if not line:
                break
            p_line = line.split(',')
            s3_uri, size = p_line[0], p_line[1]
            payload = generate_payload(s3_uri, collection, size)
            #send_to_sqs(payload, sqs_name)
            start_execution(payload)
            


def main(argv):
    
    csv_path = ''
    collection = ''
    sqs_name = ''
    
    try:
      opts, args = getopt.getopt(argv, "p:c:q:")
    except getopt.GetoptError as err:
      print(f'Error: {err}')
      sys.exit(2)
      
    for opt, arg in opts:
        if opt  == '-p':
            csv_path = arg
        elif opt == '-c':
            collection = arg
        elif opt == '-q':
            sqs_name = arg
    
    reingest(csv_path, collection, sqs_name)
            

if __name__ == '__main__':
    main(sys.argv[1:])