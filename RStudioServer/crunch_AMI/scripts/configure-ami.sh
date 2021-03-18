#!/bin/bash
set -x -e

echo "*** start ami configuration ***"

# Install R
echo "*** Install R ***"
sudo amazon-linux-extras install R4
echo "*** /Install R ***"

# Install R studio
RSTUDIO_FILE=$(basename $RSTUDIO_URL)
wget $RSTUDIO_URL
sudo yum install --nogpgcheck -y $RSTUDIO_FILE

# Install Rpackages
echo "*** Install R packages ***"
sudo yum install -y libgit2 curl openssl libcurl-devel openssl-devel libssh2-devel build-essential libcurl4-gnutls-dev libxml2-devel gsl-devel
sudo R --no-save << R_SCRIPT
install.packages(c("devtools", 'ggplot2', 'itertools', 'tm', 'wordcloud', 'doParallel', 'psych', 'reshape', 'topicmodels','aws.s3','aws.ec2metadata'), "/usr/share/R/library/", repos="http://cran.rstudio.com/")
R_SCRIPT
echo "*** /Install R packages ***"

# apt-get update

# echo "*** install: curl, wget, unzip, git ***"
# # Skip restart prompt of 'libssl1.1' by running following command
# echo '* libraries/restart-without-asking boolean true' | debconf-set-selections
# apt-get -y install curl wget unzip git
# apt-get -y install software-properties-common
# add-apt-repository -y ppa:deadsnakes/ppa
# apt-get update

# echo "*** install python${PYV} ***"
# apt-get -y install python$PYV python$PYV-venv python$PYV-dev python3-pip

# echo "*** install awscli ***"
# pip3 install -U wheel awscli --no-cache-dir

# echo "make automl directory structure"
# mkdir -p /s3bucket/input
# mkdir -p /s3bucket/output
# mkdir -p /s3bucket/user
# mkdir /repo

# echo "clone repo"
# cd /repo
# git clone --depth 1 --single-branch --branch $BRANCH $GITREPO .

# echo "create python environment"
# python3 -m venv venv

# echo "install python packages"
# /repo/venv/bin/pip3 install -U pip
# xargs -L 1 /repo/venv/bin/pip3 install --no-cache-dir < requirements.txt
