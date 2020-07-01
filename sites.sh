
#! /bin/bash

. /root/.bashrc

/etc/bryce/sites.py &> /etc/bryce/log

if [[ -s /etc/apache2/sites-enabled/000-default.conf.new && -s /etc/apache2/sites-enabled/000-default-le-ssl.conf.new ]];
then
  mv /etc/apache2/sites-enabled/000-default.conf.new /etc/apache2/sites-enabled/000-default.conf
  mv /etc/apache2/sites-enabled/000-default-le-ssl.conf.new /etc/apache2/sites-enabled/000-default-le-ssl.conf
  /usr/sbin/apachectl -k graceful
else
  echo "Something went wrong"
  cat /etc/bryce/log
fi
