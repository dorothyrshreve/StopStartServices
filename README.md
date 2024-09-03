# StopStartServices
Starts or stops a list of services on an ArcGIS Server.

## Parameters
- Username: the username used to administer the server
- Password: the password used to administer the server
- Server URL: the full url to access the server
- Start Services: radio button to indicate services should be turned on
- Stop Services: radio button to indicate services should be turned off
- Service(s) to stop or start: list of services in the Server that can be turned on or off. The selection will not generate if tool cannot log into the server.

## Notes
- must have valid server url + administrative username / password to run tool
- server urls should not have https and should not include 6443
    - example: inppwrogis01.nps.doi.net
    - example: inpyosegis02.nps.doi.net


