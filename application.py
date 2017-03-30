import os
import json
import logging
import argparse
import boto3
import botocore
import sys
import time
import signal
import urllib2


# AWS_ACCESS_KEY_ID=[access_key]
# AWS_SECRET_ACCESS_KEY=[secret]
# AWS_REGION_NAME="us-west-2"
# LOG_LEVEL="INFO"
# AWS_SNS_TOPIC_NAME="dronze-qlearn-cf"
# AWS_SQS_QUEUE_NAME="dronze-qlearn-cf-q"
# MESSAGE_LOOP_WAIT_SECS=3
# POST_MESSAGE_ENDPOINT


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')

LOGGER = logging.getLogger(__name__)

# The SQS queue needs a policy to allow the SNS topic to post to it.
queue_policy_statement = {
    "Version": "2008-10-17",
    "Id": "sns-publish-to-sqs",
    "Statement": [{
        "Sid": "auto-subscribe",
        "Effect": "Allow",
        "Principal": {
            "AWS": "*"
        },
        "Action": "SQS:SendMessage",
        "Resource": "{queue_arn}",
        "Condition": {
            "StringLike": {
                "aws:SourceArn": "{topic_arn}"
            }
        }
    }]
}

def get_log_level(level_string):
    levels = {
        "DEBUG":logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "CRITICAL":logging.CRITICAL
    }
    return levels[level_string]

def load_config(config_file):
    config = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.rstrip() #removes trailing whitespace and '\n' chars

            if "=" not in line: continue #skips blanks and comments w/o =
            if line.startswith("#"): continue #skips comments which contain =

            k, v = line.split("=", 1)
            config[k] = v.replace("\"","")
    return config

def get_sns_topic(sns, topic_name):
    """
    Get or create the SNS topic.
    """
    # Creating a topic is idempotent, so if it already exists
    # then we will just get the topic returned.
    print "topic_name:{0}".format(topic_name)
    return sns.create_topic(Name=topic_name)

def get_queue_arn(sqs,queue):
        q_attributes = sqs.get_queue_attributes(QueueUrl=queue['QueueUrl'], AttributeNames=['QueueArn'])

        #print q_attributes
        return q_attributes['Attributes']['QueueArn']

def get_sqs_queue(sqs, sns, queue_name, topic, queue_policy_statement):
    """
    Get or create the SQS queue. If it is created, then it is
    also subscribed to the SNS topic, and a policy is set to allow
    the SNS topic to send messages to the queue.
    """
    # Creating a queue is idempotent, so if it already exists
    # then we will just get the queue returned.
    topic_arn = topic['TopicArn']
    queue = sqs.create_queue(QueueName=queue_name)
    # q_attributes = sqs.get_queue_attributes(QueueUrl=queue['QueueUrl'], AttributeNames=['QueueArn'])

    #print q_attributes
    queue_arn = get_queue_arn(sqs, queue)

    # setup the statement
    queue_policy_statement['Id'] = "sqs-policy-{0}".format(queue_name)
    queue_policy_statement['Statement'][0]['Sid'] = "sqs-statement-{0}".format(queue_name)
    queue_policy_statement['Statement'][0]['Resource'] = queue_arn
    queue_policy_statement['Statement'][0]['Condition']['StringLike']['aws:SourceArn'] = topic_arn
    queue_policy_statement_merged = json.dumps(queue_policy_statement, indent=4)
    #print queue_policy_statement_merged
    set_policy_response = sqs.set_queue_attributes(
        QueueUrl=queue['QueueUrl'],
        Attributes={
            'Policy': queue_policy_statement_merged
        }
    )

    # Ensure that we are subscribed to the SNS topic
    # subscribed = False
    topic = sns.subscribe(TopicArn=topic_arn, Protocol='sqs', Endpoint=queue_arn)

    return queue

def handle_ctrl_c(signal, frame):
    print "Got ctrl+c, exiting!"
    sys.exit(0)



def check_queue(sqs, queue, poll_interval):
        """
        Check the queue for completed files and set them to be
        downloaded.
        """
        messages_model = []
        messages_response = sqs.receive_message(
            QueueUrl=queue['QueueUrl'],
            WaitTimeSeconds=poll_interval
        )

        if "Messages" in messages_response:
            for message in messages_response['Messages']:
                try:
                    messages_model.append({
                        "body":message['Body'],
                        "queue_url":queue['QueueUrl']
                        })
                except:
                    logging.critical("Unexpected error when parsing json:: {0} for json: {1}".format(sys.exc_info()[0], message['Body']))

                sqs.delete_message(
                    QueueUrl=queue['QueueUrl'],
                    ReceiptHandle=message['ReceiptHandle']
                )

        return messages_model

def post_message(message, config):

    message_json = json.dumps(message)
    logging.info("sending message: {0}".format(message_json))
    req = urllib2.Request(config['POST_MESSAGE_ENDPOINT'])
    req.add_header('Content-Type', 'application/json')

    try:
        response = urllib2.urlopen(req, message_json)
        logging.info("response: {0}".format(response.read()))
    except urllib2.HTTPError as e:
        logging.error("HTTPError code:{0} body:{1}".format(e.code, e.read()))

    return response

def main():
    print "starting."

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default=None,
                       help='the config file used for the application.')

    args = parser.parse_args()

    #load the app config
    config = load_config(args.config)

    # init LOGGER
    logging.basicConfig(level=get_log_level(config['LOG_LEVEL']), format=LOG_FORMAT)

    # make the boto3 clients
    sns = boto3.client(
        'sns',
        config["AWS_REGION_NAME"],
        aws_access_key_id=config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY"])

    sqs = boto3.client(
        'sqs',
        config["AWS_REGION_NAME"],
        aws_access_key_id=config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY"])

    # make the topic and the queue
    topic = get_sns_topic(sns, config["AWS_SNS_TOPIC_NAME"])
    topic_arn = topic['TopicArn']

    queue_name = "{0}-q".format(config["AWS_SNS_TOPIC_NAME"])
    queue = get_sqs_queue(sqs, sns, queue_name, topic, queue_policy_statement)
    queue_arn = get_queue_arn(sqs,queue)

    listening = True
    while listening:
        try:
            messages_model = check_queue(sqs, queue, int(config['MESSAGE_LOOP_WAIT_SECS']))

            if len(messages_model) > 0:
                logging.info("messages received: {0}".format(len(messages_model)))
                for message in messages_model:
                    message['topic_arn'] = topic_arn
                    message['queue_arn'] = queue_arn

                    post_message(message, config)
                    logging.info("message sent.")


        except (KeyError, AttributeError, ValueError, NameError) as ke:
            print("error: {0}".format(ke))
        except KeyboardInterrupt:
            listening = False
            signal.signal(signal.SIGINT, handle_ctrl_c)
        except:
            logging.critical("Unexpected error: {0}".format(sys.exc_info()[0]))
            time.sleep(1)


if __name__ == '__main__':
    main()
