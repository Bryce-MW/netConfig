#! /usr/bin/python3

https_name = "/etc/apache2/sites-enabled/000-default-le-ssl.conf.new"
http_name = "/etc/apache2/sites-enabled/000-default.conf.new"

https_top = "<IfModule mod_ssl.c>"
https_bot = "</IfModule>"
https_conf = """
<VirtualHost *:443>
    ProxyPreserveHost On

    SSLProxyEngine on
    <Location />
       ProxyPass {proto}://{ip}:{port}/
       ProxyPassReverse {proto}://{ip}:{port}/
    </Location>

{local_config}

    ServerName {host_name}

SSLCertificateFile /etc/letsencrypt/live/brycemw.ca/fullchain.pem
SSLCertificateKeyFile /etc/letsencrypt/live/brycemw.ca/privkey.pem
Include /etc/letsencrypt/options-ssl-apache.conf
</VirtualHost>
"""

http_conf = """
<VirtualHost *:80>
    ProxyPreserveHost On

    SSLProxyEngine on
    ProxyPass / {proto}://{ip}:{port}/
    ProxyPassReverse / {proto}://{ip}:{port}/

    ServerName {host_name}
RewriteEngine on
RewriteCond %{{SERVER_NAME}} ={host_name}
RewriteRule ^ https://%{{SERVER_NAME}}%{{REQUEST_URI}} [END,NE,R=permanent]
</VirtualHost>
"""

#name port ipaddresses.address
#netbox.ipam.getservices

import ipaddress
import CloudFlare
from importlib.machinery import SourceFileLoader
apikeys = SourceFileLoader("apikeys", "/etc/bryce/.secrets/apikeys.py").load_module()
cf_email, cf_token, netbox_token = apikeys.cf_email, apikeys.cf_token, apikeys.netbox_token
cf = CloudFlare.CloudFlare(email=cf_email, token=cf_token)
zone_name = "brycemw.ca"
zone_info = cf.zones.get(params={'name': zone_name})
zone_id = zone_info[0]['id']
from netbox import NetBox
netbox = NetBox(host='10.10.16.237', port=443, use_ssl=True, auth_token=netbox_token)

with open(http_name, "w") as http_file, open(https_name, "w") as https_file:
  https_file.write(https_top + "\n")
  for service in netbox.ipam.get_services():
    name = service["name"]
    if name != "HTTP" and name != "HTTPS":
      continue
    port = service["port"]
    ip = service["ipaddresses"][0]["address"]
    dns_name = netbox.ipam.get_ip_addresses(address=ip)[0]["dns_name"]
    vm = service['device'] is None
    if not vm:
      dev_id = service['device']['id']
    else:
      dev_id = service['virtual_machine']['id']

    record = {'name':dns_name, 'type':'CNAME', 'content':'fmt.brycemw.ca', 'proxied': True}
    try:
      cf.zones.dns_records.post(zone_id, data=record)
    except CloudFlare.exceptions.CloudFlareAPIError as ignored:
      pass
    print("Added", dns_name, name+":"+str(port), "with IP", ip)

    local_config = ""
    try:
      if not vm:
        local_config = netbox.dcim.get_devices(id=dev_id)[0]['config_context']['http_proxy']['custom_apache']
      else:
        local_config = netbox.virtualization.get_virtual_machine(id=dev_id)[0]['config_context']['http_proxy']['custom_apache']
    except KeyError as ignored:
      local_config = ""

    http_file.write(http_conf.format(ip=ipaddress.ip_interface(ip).ip, port=str(port), proto=name.lower(), host_name=dns_name))
    https_file.write(https_conf.format(ip=ipaddress.ip_interface(ip).ip, port=str(port), proto=name.lower(), host_name=dns_name, local_config=local_config))

  https_file.write(https_bot + "\n")
