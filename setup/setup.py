"""
Copyright (c) 2021 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""


import yaml, time, requests, sys


print('Heroku deployment starting')


# get configuration data
config = yaml.safe_load(open("credentials.yaml"))
heroku_username = config['heroku_username']
heroku_password = config['heroku_password']
heroku_region = config['heroku_region']
github_url = config['github_url']
github_version = config['github_version']
webex_bot_token = config['webex_bot_token']
webex_bot_email = config['webex_bot_email']
webex_room_id = config['webex_room_id']


# set API information
base_url = 'https://api.heroku.com'
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/vnd.heroku+json; version=3'
}


# get access token
token_request = requests.post(base_url + '/oauth/authorizations', headers=headers, auth=(heroku_username, heroku_password))
print('--- token_request: ' + str(token_request.status_code))
token = token_request.json()['access_token']['token']


# updating header to include authorization
headers['Authorization'] = 'Bearer ' + token


# create and deploy bot app to Heroku
payload_appsetup = {
    "app": {
        "region": heroku_region
    },
    "source_blob": {
        "url": github_url + "/tarball/" + github_version,
        "version": github_version
      }
}
appsetup_request = requests.post(base_url + '/app-setups', headers=headers, json=payload_appsetup)
print('--- appsetup_request: ' + str(appsetup_request.status_code))
appsetup_id = appsetup_request.json()['id']
app_name = appsetup_request.json()['app']['name']


# poll status until app is successfully setup
while True:
    time.sleep(5)
    appsetup_status_request = requests.get(base_url + '/app-setups/' + appsetup_id, headers=headers)
    appsetup_status = appsetup_status_request.json()['status']
    print('--- appsetup_status_request: ' + str(appsetup_status_request.status_code) + ', status: ' + appsetup_status)
    if appsetup_status == "succeeded":
        app_url = appsetup_status_request.json()['resolved_success_url']
        print('The app is deployed to: ' + app_url)
        break
    elif appsetup_status == "failed":
        failure_message = appsetup_status_request.json()['failure_message']
        print('Something went wrong: ' + str(failure_message))
        sys.exit()


# configure config vars on app
payload_configvars = {
    "WT_BOT_TOKEN": webex_bot_token
}
if webex_bot_email != '':
    payload_configvars['WT_BOT_EMAIL'] = webex_bot_email
if webex_room_id != '':
    payload_configvars['WT_ROOM_ID'] = webex_room_id
configvars_request = requests.patch(base_url + '/apps/' + app_name + '/config-vars', headers=headers, json=payload_configvars)
print('--- configvars_request: ' + str(configvars_request.status_code))


# restart dyno
if configvars_request.status_code == 200:
    dynorestart_request = requests.delete(base_url + '/apps/' + app_name + '/dynos', headers=headers)
    print('--- dynorestart_request: ' + str(dynorestart_request.status_code))
    while True:
        time.sleep(10)
        dynostatus_request = requests.get(base_url + '/apps/' + app_name + '/dynos/web.1/', headers=headers)
        dyno_status = dynostatus_request.json()['state']
        print('--- dynostatus_request: ' + str(dynostatus_request.status_code) + ', status: ' + dyno_status)
        if dyno_status == "up":
            print('Webex bot successfully deployed and running.')
            print("To see the application logs, go to the Heroku dashboard, or if the Heroku CLI is installed, issue the command 'heroku logs -- tail -a " + app_name + "'.")
            break