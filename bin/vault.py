#!/usr/bin/env python
import socket
import json
import subprocess
import os
hostname = socket.gethostname()
site = hostname.split('.')[0].split('-')[-1]
with open('update_secret','r') as file:
    image =  file.read()
    value =  image.split()[6]
os.environ["VAULT_ADDR"]="https://api.vault.secrets.{}.data.sfdc.net:443".format(site)
def update_Image():
    subprocess.call(["vault", "login","-method=cert", "-ca-cert=/etc/pki_service/ca/cacerts.pem","-client-cert=/etc/pki_service/pra/pra-dsm-client/certificates/pra-dsm-client.pem", "-client-key=/etc/pki_service/pra/pra-dsm-client/keys/pra-dsm-client-key.pem","name=kv_pra-vault-rw"])
    subprocess.call(["vault","kv","get","kv/pra-vault/pra-common/secret"])
    subprocess.call(["vault", "kv", "patch", "kv/pra-vault/pra-common/secret","pra_openstack_image_id={}".format(value)])
if __name__ == "__main__":
 update_Image()
