import sys
import clr
import time
import os
import System
import MissionPlanner


cache_dir = System.Environment.GetFolderPath(
  System.Environment.SpecialFolder.LocalApplicationData,
)
nidar_dir = os.path.join(cache_dir, "nidar")
if not os.path.exists(nidar_dir):
  os.makedirs(nidar_dir)
file_path = os.path.join(nidar_dir, "tll.csv")
print(f"logging file path: `{file_path}`")


def GetMasterState():
  for port in MainV2.Comports:
    try:
      current_id = port.sysid
    except:
      try:
        current_id = port.sysidcurrent
      except:
        current_id = port.MAV.sysid
    if current_id == 1:
      try:
        return port.MAV.cs
      except:
        return port.currentstate
  return None


if not os.path.exists(file_path):
  with open(file_path, "w") as f:
    f.write("Timestamp,Latitude,Longitude,Altitude\n")


print("started logging ...")


while True:
  master = GetMasterState()
  if master is not None:
    try:
      timestamp = time.time()
      lat = master.lat
      lng = master.lng
      alt = master.alt
      with open(file_path, "a") as f:
        f.write("%f,%f,%f,%f\n" % (timestamp, lat, lng, alt))
        f.flush()
        os.fsync(f.fileno())
      print("LOGGED: %f" % timestamp)
    except Exception as e:
      print("DATA ERROR: " + str(e))
  else:
      print("Waiting for Vehicle SYSID 1...")
  Script.Sleep(100)
