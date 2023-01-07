# Documentation REST-API of the famous Heizungssteuerung

## /
### method: GET
Returns if the service is alive.
([/](../))

## /status
### method: GET
Returns the overall status
([/status](../status))

## /status/sensor
### method: GET
Returns sensor information and measurements
([/status/sensor](../status/sensor))

## /help
### method: GET
Displays the function documentation and the JSON commands
([/help](../help))

## /restapi
### method: GET
Displays this page
([/restapi](../restapi))

## /timer
### method: GET
Returns the timer json object
([/timer](../timer))

### method: PUT
action=reload: Reloads timer file (/timer?action=reload)

## /room
### method: GET
Returns the list of available rooms
([/room](../room))

## /room/ROOM 
### method: GET
Returns all details of the ROOM

## /room/ROOM/status
### method: GET
Returns the status of ROOM (on/off)

## /room/ROOM/mode
### method: GET
Returns the mode of ROOM (on/off/auto)

Mode auto is timer mode

### method: PUT
* mode=auto: sets mode to auto (timer mode)
* mode=off: turns heating off
* mode=on: turns heating on
* mode=window_open: turns heating off and stores previous mode
* mode=window_close: sets heating to the state before window opening

## /room/ROOM/timer
### method: GET
Returns the detailed timer settings for ROOM

### method: PUT
Will set the rooms timer somewhen in the future. Not implemented yet.

## /room/ROOM/shorttimer
### method: GET
Returns the shorttimer settings of ROOM:

* ShortTimer: Remaininf time in seconds
* Status: on/off
* ShorttimerMode: run/off

### method: PUT
#### action=reset
Resets the shorttimer mode

#### action=set
Sets a shorttimer. Needs the following parameters:

* time=INT (time in seconds)
* mode=on/off

## /room/ROOM/temp
### method: GET
Returns measured ROOM temperature

## /room/ROOM/settemp
### method: GET
Returns set temperature of ROOM

### method: PUT
temp=21.5 (float): Set desired ROOM temperature

## /mixer
### method: GET
Returns if a mixer is present. If mixer is present, run state and temp data is returned as well

## /mixer/ff/temp
### method: GET
Returns the measured forward flow temperature

## /mixer/ff/settemp
### method: GET
Returns the set forward flow temperature.

## /mixer/ff/mintemp
### method: GET
Returns the minimum forward flow temperature

### method: PUT
temp=28 (float): sets minimum forward flow temperature

## /mixer/ffmaxtemp
### method: GET
Returns the maximum forward flow temperature

### method: PUT
temp=34 (float): sets maximum forward flow temperature

## /garage
### method: GET
Returns state of garage door, or N/A if no garage door control available, Not yet implemented

### method: PUT
* action=auf: Opens door
* action=zu: Closes door

Not yet implemented.
