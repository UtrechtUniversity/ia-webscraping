#!/bin/bash
set -x -e

# Install R
echo "*** Install R ***"
sudo amazon-linux-extras install R4
echo "*** /Install R ***"

# Create User
echo "*** Create user ***"
USER="${rstudio_user}"
USERPW="${rstudio_user_pwd}"

sudo adduser $USER
sudo sh -c "echo '$USERPW' | passwd $USER --stdin"
echo "*** /Create user ***"

# Install RStudio
echo "*** Install R studio ***"
RSTUDIO_URL="${rstudio_url}"
RSTUDIOPORT="${rstudio_port}"
MIN_USER_ID=400

RSTUDIO_FILE=$(basename $RSTUDIO_URL)
wget $RSTUDIO_URL
sudo yum install --nogpgcheck -y $RSTUDIO_FILE
sudo sh -c "echo 'www-port=$RSTUDIOPORT' >> /etc/rstudio/rserver.conf"
sudo sh -c "echo 'auth-minimum-user-id=$MIN_USER_ID' >> /etc/rstudio/rserver.conf"
sudo perl -p -i -e "s/= 5../= 100/g" /etc/pam.d/rstudio
sudo rstudio-server stop || true
sudo rstudio-server start
echo "*** /Install R studio ***"

# Install Rpackages
echo "*** Install R packages ***"
sudo yum install -y libgit2 curl openssl libcurl-devel openssl-devel libssh2-devel build-essential libcurl4-gnutls-dev libxml2-devel
sudo R --no-save << R_SCRIPT
install.packages(c("devtools", 'ggplot2', 'itertools', 'tm', 'wordcloud','aws.s3','aws.ec2metadata'), "/usr/share/R/library/", repos="http://cran.rstudio.com/")
R_SCRIPT
echo "*** /Install R packages ***"