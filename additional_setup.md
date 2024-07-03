Add the following to configuration.yaml to read data from PLS and get data from presence sensor.

```
sensor:
  - platform: tcp
    name: HiL_sensor
    host: 192.168.10.52
    port: 5001
    timeout: 5
    #payload: "START-S" # This one triggers saving the original data.
    payload: "START"
    scan_interval: 20

  - platform: template
    sensors:
      my_tcp_sensor1:
        friendly_name: HiL_sensor1
        unit_of_measurement: "Lx"
        value_template: "{{float(states('sensor.HiL_sensor').split(',')[0]) * 0.65}}"
      my_tcp_sensor2:
        friendly_name: HiL_sensor2
        unit_of_measurement: "Lx"
        value_template: "{{float(states('sensor.HiL_sensor').split(',')[1]) * 0.5}}"

binary_sensor:
  - platform: template
    sensors:
      my_presence_sensor:
        friendly_name: Window_side_area
        value_template: >-
          {%- if is_state("binary_sensor.presence_sensor_fp2_4a6e_presence_sensor_2", "off") and is_state("binary_sensor.presence_sensor_fp2_4a6e_presence_sensor_3", "off") -%}
          off
          {%- else -%}
          on
          {%- endif -%}

```
