import requests, json
import ssl
import socket
import sys

####################################################
## These vars will be initialized in parse_args() ##
####################################################
server = None
client = None
role = None
pki_cert_root = None
client_cert = None
client_key = None
ca_cert = None


def parse_args():

    global server, client, role, pki_cert_root, client_cert, client_key, ca_cert
    server = socket.gethostname()+':8443'
    client = 'smsapi'
    role = 'smsapi'
    pki_cert_root = '/etc/pki_service'

    client_cert = pki_cert_root + '/' + client + '/client/certificates/client.pem'
    client_key = pki_cert_root + '/' + client + '/client/keys/client-key.pem'
    ca_cert = pki_cert_root + '/ca/cacerts.pem'


def testAPIv1():
    test_key_created = False
    payload = '{}'
    key_id = ''
    url = 'https://' + server + '/v1/volumekeys'

    print "CLIENT: " + client
    print "ROLE: " + role
    print "URL: " + url

    print "########################################"
    print "Testing create key without client certs."
    print "########################################"
    resp = requests.post(url, timeout=10, json=payload, verify=ca_cert)
    if resp.status_code == 403:
        print "Test successful!\n\n"
    else:
        print "Test error. Status code: " + str(resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, url, 1)

    print "###########################################"
    print "Testing create key with valid client certs."
    print "###########################################"
    resp = requests.post(url, json=payload, timeout=10, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 201:
        data = json.loads(resp.content)
        key_id = data.get('KeyId')
        test_key_created = True
        print "KeyId: " + key_id
        print "Test successful!\n\n"
    else:
        print "Unable to create new key! Exiting...\n\n"
        cleanup_and_exit(test_key_created, url, 1)

    url = url + '/' + key_id

    print "####################"
    print "Retrieving test key"
    print "####################"
    resp = requests.get(url, timeout=10, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 200:
        print resp.content
        print "Retrieved key successfully!\n\n"
    else:
        print "Unable to retrieve key " + key_id + " Status code: " + str(resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, url, 1)

    print "#######################"
    print "Retrieving key versions"
    print "#######################"
    resp = requests.get(url + "/versions", timeout=10, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 200:
        print resp.content
        print "Retrieved key versions successfully!\n\n"
    else:
        print "Unable to retrieve key versions for " + key_id + " Status code: " + str(
            resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, url, 1)

    print "##################"
    print "Rotate key test #1"
    print "##################"
    payload = {'MaxVersion': 1}
    headers = {'content-type': 'application/json'}
    resp = requests.post(url + '/versions', data=json.dumps(payload), headers=headers, timeout=10,
                         cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 201:
        print "Test successful!\n\n"
    else:
        print "Unable to rotate key! " + str(resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, url, 1)

    print "##################"
    print "Rotate key test #2"
    print "##################"
    payload = {'MaxVersion': 2}
    headers = {'content-type': 'application/json'}
    resp = requests.post(url + '/versions', data=json.dumps(payload), headers=headers, timeout=10,
                         cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 201:
        print "Test successful!\n\n"
    else:
        print "Unable to rotate key! " + str(resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, url, 1)

    print "##################"
    print "Rotate key test #3"
    print "##################"
    payload = {'MaxVersion': 3}
    headers = {'content-type': 'application/json'}
    resp = requests.post(url + '/versions', data=json.dumps(payload), headers=headers, timeout=10,
                         cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 201:
        print "Test successful!\n\n"
    else:
        print "Unable to rotate key! " + str(resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, url, 1)

    print "###############"
    print "Retire key test"
    print "###############"
    resp = requests.delete(url + '/versions/2', timeout=10, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 204:
        print "Test successful!\n\n"
    else:
        print "Unable to retire key " + key_id + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, url, 1)

    cleanup_and_exit(test_key_created, url, 0)


def testAPIv2():
    test_key_created = False
    payload = '{}'
    key_id = ''
    version_id = ''
    url = 'https://' + server + '/v2/keys'
    test_url = ''
    clean_url = ''

    print "CLIENT: " + client
    print "ROLE: " + role
    print "URL: " + url

    print "########################################"
    print "Testing create key without client certs."
    print "########################################"
    test_url = url
    payload = {'Owner': {'Role': role}, 'Type': 'RSA4096'}
    headers = {'content-type': 'application/json'}
    resp = requests.post(test_url, data=json.dumps(payload), headers=headers, timeout=100, verify=ca_cert)
    if resp.status_code == 403:
        print "Test successful!\n\n"
    else:
        print "Test error. Status code: " + str(resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "###########################################"
    print "Testing create key with valid client certs."
    print "###########################################"
    test_url = url
    payload = {'Owner': {'Role': role}, 'Type': 'RSA4096'}
    headers = {'content-type': 'application/json'}
    resp = requests.post(test_url, data=json.dumps(payload), headers=headers, timeout=100,
                         cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 201:
        data = json.loads(resp.content)
        key_id = data.get('KeyId')
        version_id = data.get('CurrentVersionId')
        test_key_created = True
        clean_url = url + '/' + key_id
        print "KeyId: " + key_id
        print "Create key test is successful!\n\n"
    else:
        print "Unable to create new key! Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "####################"
    print "DescribeKey test"
    print "####################"
    test_url = url + '/' + key_id
    resp = requests.get(test_url, timeout=100, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 200:
        print resp.content
        print "Describe key test is successful!\n\n"
    else:
        print "Unable to describe key " + key_id + " Status code: " + str(resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "#######################"
    print "Describe key version"
    print "#######################"
    test_url = url + '/' + key_id + '/versions/' + version_id
    resp = requests.get(test_url, timeout=100, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 200:
        print resp.content
        print "Describe key version test is successful!\n\n"
    else:
        print "Unable to describe key version for " + key_id + "with version: " + version_id + " Status code: " + str(
            resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "##################"
    print "Rotate key"
    print "##################"
    test_url = url + '/' + key_id + '/versions/'
    payload = {'MaxVersion': 1}
    headers = {'content-type': 'application/json'}
    resp = requests.post(test_url, data=json.dumps(payload), headers=headers, timeout=100,
                         cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 201:
        data = json.loads(resp.content)
        version_id = data.get('VersionId')
        print "Rotate key test is successful!\n\n"
    else:
        print "Unable to rotate key! " + str(resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "##################"
    print "Retire key version"
    print "##################"
    test_url = url + '/' + key_id + '/versions/' + version_id
    resp = requests.delete(test_url, timeout=100, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 204:
        print "Retire key version test is successful!\n\n"
    else:
        print "Unable to retire key version! " + key_id + "with version: " + version_id + " Status code: " + str(
            resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "##################"
    print "Reactivate key version"
    print "##################"
    test_url = url + '/' + key_id + '/versions/' + version_id
    payload = {'Retired': False}
    headers = {'content-type': 'application/json'}
    resp = requests.patch(test_url, data=json.dumps(payload), headers=headers, timeout=100,
                          cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 200 or resp.status_code == 204:
        print "Reactivate key version test is successful!\n\n"
    else:
        print "Unable to reactivate key version! " + key_id + "with version: " + version_id + " Status code: " + str(
            resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "##################"
    print "Get public key"
    print "##################"
    test_url = url + '/' + key_id + '/versions/' + version_id + '/publickey'
    resp = requests.get(test_url, timeout=100, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 200:
        print "Get public key test is successful!\n\n"
    else:
        print "Unable to get public key! " + key_id + "with version: " + version_id + " Status code: " + str(
            resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "##################"
    print "Associate certificate test"
    print "##################"
    test_url = url + '/' + key_id + '/versions/' + version_id + '/certificate'
    payload = {
        'Certificate': '-----BEGIN CERTIFICATE-----\nMIIDiDCCAnACCQCxWJDaQg6LwjANBgkqhkiG9w0BAQsFADCBhTELMAkGA1UEBhMC\nVVMxEzARBgNVBAgMCldhc2hpbmd0b24xETAPBgNVBAcMCEJlbGxldnVlMRMwEQYD\nVQQKDApTYWxlc2ZvcmNlMSAwHgYDVQQLDBdJbmZyYXN0cnVjdHVyZSBTZWN1cml0\neTEXMBUGA1UEAwwOc2FsZXNmb3JjZS5jb20wHhcNMTgwMjE5MDg0MzQzWhcNMjgw\nMjE3MDg0MzQzWjCBhTELMAkGA1UEBhMCVVMxEzARBgNVBAgMCldhc2hpbmd0b24x\nETAPBgNVBAcMCEJlbGxldnVlMRMwEQYDVQQKDApTYWxlc2ZvcmNlMSAwHgYDVQQL\nDBdJbmZyYXN0cnVjdHVyZSBTZWN1cml0eTEXMBUGA1UEAwwOc2FsZXNmb3JjZS5j\nb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDJon1RiEyD9DVA+nIJ\nUXPM2KsVLuaqDRsepaP/6Cwp8ooicTe7PjpWOKJNzUkxFIe16z7cL5twMr0GSBhG\nE4ByiKQTYW0NzB6oZejSCax0eYv5QmDEzTbEblDtS3axhmi0O9CWrswUYAztyfyW\nLMVqrFhfa/GM8P9op9tgkE729ASHwsDDiD6zJ4O6dmpg9C3Tk6SjGZW7hcwrTCjV\nud/iXKROZSFwQLJGF03Yf2wDO2gW1CY53Am5oUSRnxOyfL3r6b3C7HMazDTfmI9J\nWKb6kgw0lykGC85Yk2n2Jv97IWEggGvOVOIBUlji6OpJULVhjCOnzubzj5/93jje\nFXbXAgMBAAEwDQYJKoZIhvcNAQELBQADggEBAFNQwz7/URiJbloXZd0c19dsmLBq\nlCwaixGEx1c08JzAqVGF9+lqdkJ+7U47bmGkZJVYMLXEJW0nFudBKIRc2Natke0k\nrJQyQdPwH4sClF7UarFcP0LWT24Q4WxWvU+mhAOzlwksGuKZHh0G5uodgNHOUygb\nhZ0Pp/IHOwEtNKYHYlQFkuY3Spk+2FkWNFpqihmI7+tNek4HPG5wAatJ8dwz7Bwr\nw4jL6DvxbpesTOSz7/vGXtJ7Y/wr2/l36OwBsR7z+30fZJJ2YE4kslLnrqYjwKNO\nCrr3m1jbWNsVlh8x56SJsltNJae+cZ+FL5R4xErp3fxP8O3AITAO3hD2fxc=\n-----END CERTIFICATE-----'}
    headers = {'content-type': 'application/json'}
    resp = requests.put(test_url, data=json.dumps(payload), headers=headers, timeout=100,
                        cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 201:
        print "AssociateCertificate is successful!\n\n"
    else:
        print "Unable to associate certificate! " + key_id + "with version: " + version_id + " Status code: " + str(
            resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "##################"
    print "Get certificate"
    print "##################"
    test_url = url + '/' + key_id + '/versions/' + version_id + '/certificate'
    resp = requests.get(test_url, timeout=100, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 200:
        print "Get certificate test is successful!\n\n"
    else:
        print "Unable to get certificate! " + key_id + "with version: " + version_id + " Status code: " + str(
            resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "##################"
    print "Disassociate certificate"
    print "##################"
    test_url = url + '/' + key_id + '/versions/' + version_id + '/certificate'
    resp = requests.delete(test_url, timeout=100, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 204:
        print "Disassociate certificate test is successful!\n\n"
    else:
        print "Unable to disassociate certificate! " + key_id + "with version: " + version_id + " Status code: " + str(
            resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "##################"
    print "Sign test"
    print "##################"
    test_url = url + '/' + key_id + '/versions/' + version_id + '/sign'
    payload = {'Algorithm': 'RSA', 'Data': 'ZGF0YSB0byBzaWdu'}  # 'data to sign'
    headers = {'content-type': 'application/json'}
    resp = requests.post(test_url, data=json.dumps(payload), headers=headers, timeout=100,
                         cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 200:
        print "Sign test is successful!\n\n"
    else:
        print "Unable to sign data! " + key_id + "with version: " + version_id + " Status code: " + str(
            resp.status_code) + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    print "###############"
    print "Retire key test"
    print "###############"
    test_url = url + '/' + key_id
    resp = requests.delete(test_url, timeout=100, cert=(client_cert, client_key), verify=ca_cert)
    if resp.status_code == 204:
        print "Retire key test is successful!\n\n"
        test_key_created = False
    else:
        print "Unable to retire key " + key_id + " Exiting...\n\n"
        cleanup_and_exit(test_key_created, clean_url, 1)

    cleanup_and_exit(test_key_created, clean_url, 0)


def main():
    parse_args()
    testAPIv1()
    testAPIv2()
    sys.exit(0)


def cleanup_and_exit(test_key_created, url, exit_code):
    if test_key_created:
        print "#################"
        print "Deleting test key"
        print "#################"
        resp = requests.delete(url, timeout=100, cert=(client_cert, client_key), verify=ca_cert)
        print " Status code: " + str(resp.status_code) + "url: " + url
        if resp.status_code == 204:
            print "Deleted key successfully!\n\n"
        else:
            print "Warning: unable to delete test key! This may happen if you run test locally without smscanary cert.\n\n"

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()