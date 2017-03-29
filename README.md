# sns-webhook

The simple sns to webhook service. listens to a specific sns topic and posts to a webhook. The application will expect that a topic exists and will create a SQS queue and subscribe the SNS topic to it automatically. It will also add the policy to the SQS queue automatically *if the config user is allowed to add permissions to a SQS policies"

# Configuration

## IAM Policy Requirements
The following policy Requirements were used for this application credentials:

* AmazonSQSFullAccess
* AmazonSNSFullAccess

## The  Config File
It is expected that the name of the file is snswebhook.properties

```
AWS_ACCESS_KEY_ID=[access_key]
AWS_SECRET_ACCESS_KEY=[secret]
AWS_REGION_NAME="us-west-2"
LOG_LEVEL="INFO"
AWS_SNS_TOPIC_ARN="arn:aws:sns:us-west-2:604212546939:dronze-qlearn-cf"
AWS_SNS_TOPIC_NAME="dronze-qlearn-cf"
AWS_SQS_QUEUE_NAME="dronze-qlearn-cf-q"
MESSAGE_LOOP_WAIT_SECS=3
POST_MESSAGE_ENDPOINT="http://ec2-35-167-29-231.us-west-2.compute.amazonaws.com:5020/webhook/notification/T1BGUBKQR/aws-sns/dronze-qlearn-cf"
```

## Installing the Virtual Environment
A virtual environment installer is provided called `install.sh`.

```
$ bash ./install.sh
$ source ../ve-sns-webhook/bin/activate
```


# Running The Application Locally
```
$ python application.py --config ~/config/local/snswebhook.properties
starting.
topic_name:dronze-qlearn-cf
INFO       2017-03-29 15:29:50,529 _new_conn                            735 : Starting new HTTPS connection (1): sns.us-west-2.amazonaws.com
INFO       2017-03-29 15:29:50,724 _new_conn                            735 : Starting new HTTPS connection (1): us-west-2.queue.amazonaws.com
```

# Using the Docker Container

## Building the Container

if you have problems use the `--no-cache` option

```
docker build -t dronzebot/snswebhook:latest .
```

## Running The Docker image
The container will use the configuration and brain graph you provide.

```
$ docker run -t -d -p 5020:5020 --name snswebhook -v ${CONFIG_DIR}:/mnt/config dronzebot/snswebhook:latest
```

## Pushing the Container to AWS ECR

1) Retrieve the docker login command that you can use to authenticate your Docker client to your registry:

`aws ecr get-login --region us-west-2`

2) Run the docker login command that was returned in the previous step.
3) Build your Docker image using the following command. For information on building a Docker file from scratch see the instructions here. You can skip this step if your image is already built:

`docker build -t dronzebot/snswebhook:latest .`

4) After the build completes, tag your image so you can push the image to this repository:

`docker tag dronzebot/snswebhook:latest 604212546939.dkr.ecr.us-west-2.amazonaws.com/dronzebot/snswebhook:latest`

5) Run the following command to push this image to your newly created AWS repository:

`docker push 604212546939.dkr.ecr.us-west-2.amazonaws.com/dronzebot/snswebhook:latest`

# Pulling the Container from the Private Repo and Running

1) login

`aws ecr get-login --region us-west-2`

2) pull the container from the ecs repo

`docker pull 604212546939.dkr.ecr.us-west-2.amazonaws.com/dronzebot/snswebhook:latest`

3) make sure that the snswebhook.properties is in the config dir to be mounted.

4) make sure any existing instances are stoped and removed
```
$ sudo docker stop snswebhook
snswebhook
$ sudo docker rm snswebhook
snswebhook
```

5) run it

```
$ export CONFIG_DIR=/home/ubuntu/config
$ docker run -t -d --name snswebhook -v ${CONFIG_DIR}:/mnt/config 604212546939.dkr.ecr.us-west-2.amazonaws.com/dronzebot/snswebhook:latest
```
