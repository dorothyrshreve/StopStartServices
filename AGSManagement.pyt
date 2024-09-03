# -*- coding: utf-8 -*-

import arcpy
import requests
import json

all_service_dict = {}
action_service_dict = {}
ags_token = 'NO TOKEN YET'
service_action = 'Start'

def msg(txt):
    try:
        print(txt)
        arcpy.AddMessage(txt)
    except:
        print(' - not text -')
        arcpy.AddMessage(' - not text - ')

def makeRequest(url, payload):

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    try:
        response = requests.request("POST",
                                    url,
                                    headers=headers,
                                    data=payload,
                                    verify=False)
    except:
        msg(' -- something weird happened.')
        return None
    
    responseBody=json.loads(response.text.encode('utf8'))

    if 'status' in list(responseBody.keys()):
        if responseBody['status'] != 'success':
            msg(' -- cannot complete request')
            msg(responseBody)
        else:
            msg(' -- success!')
        return None
        
    else:
        return responseBody

def generateToken(username, password,full_server):
    ''' attempts to get a token to access the server '''

    payload = {'username':username,
               'password':password,
               'client':'requestip',
               'expiration':10,
               'f':'json'}
    token_url = f"https://{full_server}:6443/arcgis/admin/generateToken"

    tokenResponseBody = makeRequest(token_url, payload)

    if tokenResponseBody is None:
        msg(' - no responseBody found...')
        return None

    if 'token' not in list(tokenResponseBody.keys()):
        msg(' - cannot generate token, will not be able to access ArcGIS Server')
        msg(tokenResponseBody)
        return None
    
    return tokenResponseBody['token']

def findServicesInFolder(folderBody):
    ''' generate dictionary of services in folder, the service name is the key '''

    if 'services' not in list(folderBody.keys()):
        msg(' -- no services in folder')
        return None

    this_service_dict = {}
    for service in folderBody['services']:
        this_service_dict[f"{service['folderName']}/{service['serviceName']}"] = [service['folderName'], service['serviceName'], service['type']]
        
    return this_service_dict


def generateServicesList(full_server, ags_token):

    this_service_dict = {}
    
    # generate list of services at Root
    services_url = f"https://{full_server}:6443/arcgis/admin/services?detail=false&f=json&token={ags_token}"
    servicesBody = makeRequest(services_url, '')

    if not servicesBody:
        msg(' - unable to get service Body')
        return None

    root_dict = findServicesInFolder(servicesBody)
    if root_dict: this_service_dict.update(root_dict)

    # stop if there are no folders to investigate
    if 'folders' not in list(servicesBody.keys()):
        return this_service_dict
    
    # generate list of services in folders
    ct = 5
    for folder in servicesBody['folders']:
        folder_url = services_url.replace("services", f"services/{folder}")
        folderBody = makeRequest(folder_url, '')

        folder_dict = findServicesInFolder(folderBody)
        if folder_dict: this_service_dict.update(folder_dict)
        if ct < 0: break
        else: ct -= 1

    return this_service_dict

def generateActionServicesList(service_names, service_list):
    # get a list of services that will be turned on or off with this tool
    temp_dict = {}
        
    for x in service_names:
        temp_dict[x] = service_list[x]

    return temp_dict

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "AGSManagementToolbox"
        self.alias = "AGSManagementToolbox"

        # List of tool classes associated with this toolbox
        self.tools = [StartStopServices]


class StartStopServices:
    
    def __init__(self):
        """Start or stop one or more services on the ArcGIS Server."""
        self.label = "StartStopServices"
        self.description = "Stop or Start Services on ArcGIS Server"

    def getParameterInfo(self):
        """Define the tool parameters."""

        global all_service_dict
        global action_service_dict
        global username
        global password
        global full_server
        global ags_token
        global service_action

        username_param = arcpy.Parameter(
            displayName="Username",
            name='username',
            datatype='GPString',
            parameterType='Required',
            direction="Input"
        )

        password_param = arcpy.Parameter(
            displayName="Password",
            name='password',
            datatype='GPString',
            parameterType='Required',
            direction="Input"
        )

        server_param = arcpy.Parameter(
            displayName="Server URL",
            name='server',
            datatype='GPString',
            parameterType='Required',
            direction="Input"
        )

        ags_token_param = arcpy.Parameter(
            displayName='AGS Token',
            name='ags_token',
            datatype='GPString',
            parameterType='Required',
            direction='Input'   
        )

        start_services_param = arcpy.Parameter(
            displayName='Start Services',
            name='start_services',
            datatype='GPBoolean',
            parameterType='Optional',
            direction='Input'
        )

        stop_services_param = arcpy.Parameter(
            displayName='Stop Services',
            name='stop_services',
            datatype='GPBoolean',
            parameterType='Optional',
            direction='Input'
        )

        services_names = arcpy.Parameter(
            displayName='Service(s) to stop or start',
            name='servicesNames',
            datatype='GPString',
            parameterType='Optional',
            direction='Input',
            multiValue=True
        )

        services_list = arcpy.Parameter(
            displayName='service list',
            name='service_list',
            datatype='GPString',
            parameterType='Optional',
            direction='Input',
            multiValue=True
        )

        services_list.enabled = False
        ags_token_param.enabled = False

        username = ''
        username_param.value=username
        
        ags_token_param.value = ags_token
        
        password = ''
        password_param.value= password
        
        full_server = 'inppwrogis01.nps.doi.net'
        server_param.value=full_server
        
        start_services_param.value=True
        stop_services_param.value=False
        

        params = [username_param, password_param, server_param, ags_token_param, start_services_param, stop_services_param, services_names, services_list]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        global all_service_dict
        global action_service_dict
        global username
        global password
        global full_server
        global ags_token
        global service_action

        last_run = True
        for p in parameters:
            if not p.hasBeenValidated: last_run = False
        if last_run: return

        # make the start and stop boxes go switchy
        if service_action == 'Start' and parameters[5].valueAsText=='true':
            parameters[4].value=False
            service_action = 'Stop'

        if service_action == 'Stop' and parameters[4].valueAsText=='true':
            parameters[5].value=False
            service_action = 'Start'

        # get a list of services that will be turned on or off with this tool
        if parameters[-2].values and all_service_dict:
            action_service_dict = generateActionServicesList(parameters[-2].values, all_service_dict)
            parameters[-1].values = list(action_service_dict.keys())


        # can't generate a token without username, password, and server inputs
        if (parameters[0].valueAsText == '' or # username
            parameters[1].valueAsText == '' or # password
            parameters[2].valueAsText == ''):   # server
            parameters[3].value = 'NO TOKEN YET'
            return

        # do not generate tokens or service list unnecessarily
        if (parameters[0].hasBeenValidated and
            parameters[1].hasBeenValidated and 
            parameters[2].hasBeenValidated and
            parameters[3].hasBeenValidated):
            return
        
        # generate token
        if (parameters[0].valueAsText != username or 
            parameters[1].valueAsText != password or
            parameters[2].valueAsText != full_server):

            username = parameters[0].valueAsText
            password = parameters[1].valueAsText
            full_server = parameters[2].valueAsText

            ags_token = generateToken(username, password, full_server)
        
        # if token generation did not work do not proceed
        if ags_token is None or ags_token == 'NO TOKEN YET':
            parameters[3].value = 'NO TOKEN YET'
            parameters[-2].filter.list =[]
            parameters[-2].value = ''
            parameters[-1].value = ''
            return
        
        parameters[3].value = ags_token   ## Houston we have lift off

        # generate a list of services if there is a token and a working server

        if ags_token != 'NO TOKEN YET' and full_server:
            temp_dict = {}
            temp_dict = generateServicesList(full_server, ags_token)


            # display just the names of the services in the list
            if temp_dict:
                parameters[-2].filter.type = 'ValueList'
                parameters[-2].filter.list = list(temp_dict.keys())

            all_service_dict = temp_dict.copy()
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        msg(f" ~ alright we're gonna {service_action} these services:")
        
        payload = 'services={services=['

        for service in action_service_dict:
            msg(f" -- {service}")
            folder = action_service_dict[service][0]
            service_type = action_service_dict[service][2]
            service_name = service.split("/")[-1]

            payload = payload + "{'folderName':'" +folder+ "','serviceName':'"+service_name+ "','type':'" +service_type+ "'},"
        
        payload = payload[:-1] + "]}&f=json&token=" +ags_token

        msg(f' ~ {service_action} existing ags map services')

        url = f"https://{full_server}:6443/arcgis/admin/services/{service_action}Services"

        final_request = makeRequest(url, payload)

        if final_request: msg(final_request)
        else: msg('DONE')

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
