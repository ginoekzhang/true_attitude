
# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time

import board

# pylint:disable=no-member
from adafruit_lsm6ds import AccelRange, GyroRange, Rate
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX as LSM6DS
from adafruit_lis3mdl import LIS3MDL

# from adafruit_lsm6ds.lsm6ds33 import LSM6DS33 as LSM6DS
# from adafruit_lsm6ds.lsm6dso32 import LSM6DSO32 as LSM6DS
# from adafruit_lsm6ds.ism330dhcx import ISM330DHCX as LSM6DS

i2c = board.I2C()  # uses board.SCL and board.SDA
#i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
dof6 = LSM6DS(i2c)
dof3 = LIS3MDL(i2c)

dof6.accelerometer_range = AccelRange.RANGE_8G
print("Accelerometer range set to: %d G" % AccelRange.string[dof6.accelerometer_range])


dof6.gyro_range = GyroRange.RANGE_2000_DPS
print("Gyro range set to: %d DPS" % GyroRange.string[dof6.gyro_range])

dof6.accelerometer_data_rate = Rate.RATE_1_66K_HZ
# sensor.accelerometer_data_rate = Rate.RATE_12_5_HZ
print("Accelerometer rate set to: %d HZ" % Rate.string[dof6.accelerometer_data_rate])

dof6.gyro_data_rate = Rate.RATE_1_66K_HZ
print("Gyro rate set to: %d HZ" % Rate.string[dof6.gyro_data_rate])

while True:
    print(
        "Accel X:%.2f Y:%.2f Z:%.2f ms^2 Gyro X:%.2f Y:%.2f Z:%.2f rad/s Mag X:%.2f Y:%.2f Z:%.2f uT"
        % (dof6.acceleration + dof6.gyro + dof3.magnetic)
    )
    time.sleep(0.05)
