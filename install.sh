#!/bin/bash -e

BASEDIR=`dirname $0`/..
REQUIREMENTS=`dirname $0`/requirements.txt

echo "BASEDIR: ${BASEDIR}"

if [ ! -d "$BASEDIR/ve-sns-webhook" ]; then
    virtualenv -q $BASEDIR/ve-sns-webhook --system-site-packages
    echo "Virtualenv ve-sns-webhook created."
fi

if [ ! -f "$BASEDIR/ve-sns-webhook/updated" -o $REQUIREMENTS -nt $BASEDIR/ve-sns-webhook/updated ]; then
    source "$BASEDIR/ve-sns-webhook/bin/activate"
    echo "virtualenv ve-sns-webhook activated."

    pip install --upgrade pip

    pip install -r $REQUIREMENTS
    touch $BASEDIR/ve-sns-webhook/updated
    echo "Requirements installed."
fi
