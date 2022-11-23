# Table of Contents

- [Table of Contents](#table-of-contents)
- [steuerung](#steuerung)
  - [steuerung Objects](#steuerung-objects)
      - [get\_oekofen\_pumpe](#get_oekofen_pumpe)
      - [get\_tor](#get_tor)
      - [set\_tor](#set_tor)
      - [get\_rooms](#get_rooms)
      - [get\_room\_status](#get_room_status)
      - [set\_room\_status](#set_room_status)
      - [get\_room\_timer](#get_room_timer)
      - [reload\_timer](#reload_timer)
      - [get\_timer](#get_timer)
      - [get\_alive](#get_alive)
      - [get\_status](#get_status)
      - [get\_room\_mode](#get_room_mode)
      - [set\_room\_mode](#set_room_mode)
      - [toggle\_room\_mode](#toggle_room_mode)
      - [get\_room\_shorttimer](#get_room_shorttimer)
      - [set\_room\_shorttimer](#set_room_shorttimer)
      - [reset\_room\_shorttimer](#reset_room_shorttimer)
      - [get\_room\_temp](#get_room_temp)
      - [get\_room\_norm\_temp](#get_room_norm_temp)
      - [set\_room\_norm\_temp](#set_room_norm_temp)
      - [get\_counter\_values](#get_counter_values)
      - [short\_timer](#short_timer)
      - [timer\_operation](#timer_operation)
      - [broadcast\_value](#broadcast_value)
      - [set\_pumpe](#set_pumpe)
      - [set\_status](#set_status)

<a id="steuerung"></a>

# steuerung

<a id="steuerung.steuerung"></a>

## steuerung Objects

```python
class steuerung(Resource)
```

<a id="steuerung.steuerung.get_oekofen_pumpe"></a>

#### get\_oekofen\_pumpe

```python
def get_oekofen_pumpe()
```

Get status from Oekofen heating pump
Retries, if no response

<a id="steuerung.steuerung.get_tor"></a>

#### get\_tor

```python
def get_tor()
```

This function returns the state of the garage door if available. The return format is a JSON-String.
The function can be called via JSON-Command-String: ```'{"command" : "getTor"}'```

```python
open: '{"Answer":"getTor","Result":"auf"}'
closed: '{"Answer":"getTor","Result":"zu"}'
error: '{"Answer":"getTor","Result":"Error","Value":"Tor? Welches Tor?"}'
```

<a id="steuerung.steuerung.set_tor"></a>

#### set\_tor

```python
def set_tor(val)
```

This function triggers the switch of the Garagentor. When it's open, it closes and vice versa.
The return of the function is either a success or a error message.

Control commands look as follows:
```json
open: '{"command" : "setTor" , "Request":"auf"}'
closed: '{"command" : "setTor" , "Request":"zu"}'
```

Answer:
```json
Success: '{"Answer":"setTor","Request":"xxx","Result":"Success"}'
Error: '{"Answer":"setTor","Request":"xxx","Result":"Error"})'
No door in system: '{"Answer":"setTor","Request":"xxx","Result":"Error","Value":"Tor? Welches Tor?"}'
Door already in requested state: '{"Answer":"setTor","Request":"xxx","Result":"Tor ist doch schon xxx, Doldi."}'
```

<a id="steuerung.steuerung.get_rooms"></a>

#### get\_rooms

```python
def get_rooms()
```

function to return available rooms
Command:
```json
'{"command" : "getRooms"}'
```

Answer:
```json
'{"answer":"getRooms","available_rooms":["Z1", "Z2"]}'
```

<a id="steuerung.steuerung.get_room_status"></a>

#### get\_room\_status

```python
def get_room_status(room)
```

function to get status status of a single room

<a id="steuerung.steuerung.set_room_status"></a>

#### set\_room\_status

```python
def set_room_status(room)
```

function to set status status of a single room

<a id="steuerung.steuerung.get_room_timer"></a>

#### get\_room\_timer

```python
def get_room_timer(room)
```

function to read the timer settings per room

<a id="steuerung.steuerung.reload_timer"></a>

#### reload\_timer

```python
def reload_timer()
```

This function reloads the timer file

<a id="steuerung.steuerung.get_timer"></a>

#### get\_timer

```python
def get_timer()
```

This function returns the timer file

<a id="steuerung.steuerung.get_alive"></a>

#### get\_alive

```python
def get_alive()
```

function to see, if we are alive

<a id="steuerung.steuerung.get_status"></a>

#### get\_status

```python
def get_status()
```

function to determine status of system

<a id="steuerung.steuerung.get_room_mode"></a>

#### get\_room\_mode

```python
def get_room_mode(room)
```

Returning mode of room

<a id="steuerung.steuerung.set_room_mode"></a>

#### set\_room\_mode

```python
def set_room_mode(room, mode)
```

Setting mode of room

<a id="steuerung.steuerung.toggle_room_mode"></a>

#### toggle\_room\_mode

```python
def toggle_room_mode(room)
```

Setting mode of room to the next one

<a id="steuerung.steuerung.get_room_shorttimer"></a>

#### get\_room\_shorttimer

```python
def get_room_shorttimer(room)
```

Returns value of room's shorttimer to override Mode settings for a defined time in seconds

<a id="steuerung.steuerung.set_room_shorttimer"></a>

#### set\_room\_shorttimer

```python
def set_room_shorttimer(room, time, mode)
```

Sets value of room's shorttimer, sets mode accordingly
After setting, set_status is called to apply change immediately

<a id="steuerung.steuerung.reset_room_shorttimer"></a>

#### reset\_room\_shorttimer

```python
def reset_room_shorttimer(room)
```

Reets value of room's shorttimer, sets mode accordingly
After setting, set_status is called to apply change immediately

<a id="steuerung.steuerung.get_room_temp"></a>

#### get\_room\_temp

```python
def get_room_temp(room)
```

Returns measured temperature of room

<a id="steuerung.steuerung.get_room_norm_temp"></a>

#### get\_room\_norm\_temp

```python
def get_room_norm_temp(room)
```

Returns normal set temperature of room
Normal temperature is the value when in on-mode

<a id="steuerung.steuerung.set_room_norm_temp"></a>

#### set\_room\_norm\_temp

```python
def set_room_norm_temp(room, temp)
```

Sets normal set temperature of room
Normal temperature is the value when in on-mode

<a id="steuerung.steuerung.get_counter_values"></a>

#### get\_counter\_values

```python
def get_counter_values(counter)
```

This functions reads some values from the energy counter and retruns them as json string.

<a id="steuerung.steuerung.short_timer"></a>

#### short\_timer

```python
def short_timer()
```

Starts the short timer thread

<a id="steuerung.steuerung.timer_operation"></a>

#### timer\_operation

```python
def timer_operation()
```

Starts the timer_operation Thread.

<a id="steuerung.steuerung.broadcast_value"></a>

#### broadcast\_value

```python
def broadcast_value()
```

Starts the UDP sensor broadcasting daemon thread

<a id="steuerung.steuerung.set_pumpe"></a>

#### set\_pumpe

```python
def set_pumpe()
```

This Function starts Pumpenthread.

<a id="steuerung.steuerung.set_status"></a>

#### set\_status

```python
def set_status()
```

This function controls the heating circuits. The circuits are normally
controlled by the timer.json file and the room temperature.
A heating circuit is switched on, when we are within the on-time and the room
temperature is below the set room temperature.
It will be checked, if a manual mode (on/off) is selectedm this overrides automatic mode,
this includes the Shorttimer function.
Last but not least, is is checked, if the main heating pump is running. If not, all
heating circuitsare turned off.

