import pandas as pd
import socket
from time import sleep
from datetime import datetime

from telegraf_format import to_line_protocol

CSV_FILE = "testData4.csv"

TELEGRAF_HOST = "127.0.0.1"
TELEGRAF_PORT = 7654

RECONNECT_DELAY = 1.0

def open_socket():
    """Block until the Telegraf socket connects."""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TELEGRAF_HOST, TELEGRAF_PORT))
            print(f"Connected to Telegraf at {TELEGRAF_HOST}:{TELEGRAF_PORT}")
            return sock
        except OSError as exc:
            print(f"{time.time()}| Cannot connect to Telegraf: {exc}. Retrying...")
            sleep(RECONNECT_DELAY)

def alter_data_frame(frame, lastLap):
    if "Lap_Time" in frame and frame["Lap_Time"] == lastLap:
        frame.pop("Lap_Time")


def main():
    sock = open_socket()

    # Load the CSV file
    print("Loading CSV file...")
    df = pd.read_csv(CSV_FILE, skiprows=14, low_memory=False).iloc[1:].astype(float)
    print(f"{len(df)} rows loaded")

    input("File loaded! Press Enter to proceed. ")

    key_fields=["Time","G_Force_Lat","G_Force_Long","G_Force_Vert","D4_Iq_Command","D3_Id_Command","D2_Flux_Weakening_Output","D3_Power_On_Timer","D2_Torque_Feedback","D1_Commanded_Torque","Speed_Command","Torque_Command","Torque_Limit_Command","Speed_Mode_Enable","D3_Relay_3_Status","D4_Inverter_Run_Mode","D5_Inverter_Command_Mode","D2_Inverter_State","D1_VSM_State","D4_Inverter_Discharge_State","D6_Start_Mode_Active","D4_Iq","D3_Id","D2_Flux_Feedback","D1_Flux_Command","D1_DC_Bus_Voltage","D4_DC_Bus_Current","D3_Phase_C_Current","D1_Phase_A_Current","D4_Delta_Resolver_Filtered","D2_Motor_Speed","D1_Motor_Angle_Electrical","D5_Digital_Input_5","INV_BRAKE_SIG","D2_Digital_Input_2","D1_Digital_Input_1","D6_Digital_Input_6","D7_Digital_Input_7","D8_Digital_Input_8","INV_MOTOR_AIN","INV_THROTTLE_SIG","D6_Analog_Input_6","D4_Torque_Shudder","D3_Motor_Temperature","D1_Control_Board_Temperature","D3_Module_C","D1_Module_A","D2_14V_Master_Fault","D3_HV_Input_Current","D4_DTC_Status","Pack_SOC","Pack_Inst_Voltage","Pack_Open_Voltage","Pack_Current","Pack_Resistance","Avg_Cell_Voltage","DTC_Flags_1","DTC_Flags_2","Cell_68_Temp","Cell_65_Temp","Cell_50_Temp","Cell_63_Temp","Cell_56_Temp","Cell_53_Temp","Cell_44_Temp","Cell_41_Temp","Cell_32_Temp","Cell_29_Temp","Cell_26_Temp","Cell_39_Temp","Cell_20_Temp","Cell_15_Temp","Cell_8_Temp","Cell_2_Temp","Cell_17_Temp","Cell_5_Temp","LOW_BAT_TEMP","HIGH_BAT_TEMP","AVG_BAT_TEMP","HIGH_TEMP_ID","LOW_TEMP_ID","Brake_Pres_Front","Brake_Pres_Rear","Bat_Volts_Dash","INV_FAULT_BYTE_0","INV_FAULT_BYTE_1","INV_FAULT_BYTE_2","INV_FAULT_BYTE_3","INV_FAULT_BYTE_4","INV_FAULT_BYTE_5","INV_FAULT_BYTE_6","INV_FAULT_BYTE_7","Engine_RPM","Drive_Speed","Ground_Speed","Wheel_Slip","Wheel_Speed_FL","Wheel_Speed_FR","Wheel_Speed_RL","Wheel_Speed_RR","Damper_Pos_FL","Damper_Pos_FR","Damper_Pos_RL","Damper_Pos_RR","Dash_Temp","Direction_Command","Steering_Angle","Odometer","APPS_Fault","Lap_Distance","Lap_Time","Lap_Speed","Fastest_Lap_Time","GPS_Sats_Used","GPS_Altitude","GPS_Latitude","GPS_Longitude","GPS_Heading","GPS_Time","GPS_Date","GPS_Speed","GPS_Quality","GPS_HDOP","GPS_Valid"]


    ROWS = len(df)
    session_len = df['Time'][ROWS]
    print(f"\nEstimated run time: {session_len}s, {round(df['Time'][ROWS]/60,1)}min\n")

    neg_diff_count = 0
    lastLap = 0
    start_time = datetime.now()
    for frame in df[key_fields].head(ROWS).to_dict(orient='records'):
        time = frame.pop("Time")

        alter_data_frame(frame,lastLap)

        if time % 10 == 0:
            print(f"Timestamp: {time}s \ {session_len}s")

        # Simulate time passing
        time_diff = time - (datetime.now()-start_time).total_seconds()
        if time_diff <= 0:
            neg_diff_count += 1
        else:
            sleep(time_diff)

        # Build simulated CAN Lines
        frame = {k: v for k, v in frame.items() if v != "" and not pd.isna(v)}
        if not frame:
            continue

        # print(f"{time} : {frame}")
        line_protocol = to_line_protocol(0,frame,"simulated_can_frame")
        # print(line_protocol)

        sock.sendall(line_protocol.encode("utf-8"))

        if "Lap_Time" in frame:
            lastLap = frame["Lap_Time"]

    print(f"Took: {(datetime.now()-start_time).total_seconds()}s to simulate {df['Time'][ROWS]}s")
    print(f"{neg_diff_count}/{ROWS} negative diffs")

    sock.close()



if __name__ == "__main__":
    main();



# CSV Fields:
    # **Time
    #* G Force Lat
    #* G Force Long
    #* G Force Vert
    # D4 Iq Command
    # D3 Id Command
    # D2 Flux Weakening Output
    # D3 Power On Timer
    # D2 Torque Feedback
    # D1 Commanded Torque
    # Speed Command
    # Torque Command
    # Torque Limit Command
    # Speed Mode Enable
    # D3 Relay 3 Status
    # D4 Inverter Run Mode
    # D5 Inverter Command Mode
    # D2 Inverter State
    #* D1 VSM State
    # D4 Inverter Discharge State
    # D6 Start Mode Active
    # D4 Iq
    # D3 Id
    # D2 Flux Feedback
    # D1 Flux Command
    #* D1 DC Bus Voltage
    #* D4 DC Bus Current
    # D3 Phase C Current
    # D1 Phase A Current
    # D4 Delta Resolver Filtered
    #* D2 Motor Speed
    # D1 Motor Angle Electrical
    # D5 Digital Input 5
    # INV BRAKE SIG
    # D2 Digital Input 2
    # D1 Digital Input 1
    # D6 Digital Input 6
    # D7 Digital Input 7
    # D8 Digital Input 8
    # INV MOTOR AIN
    # INV THROTTLE SIG
    # D6 Analog Input 6
    # D4 Torque Shudder
    #* D3 Motor Temperature
    # D1 Control Board Temperature
    # D3 Module C
    # D1 Module A
    # D2 14V Master Fault
    # D3 HV Input Current
    # D4 DTC Status
    #* Pack SOC
    #? Pack Inst Voltage
    #? Pack Open Voltage
    # Pack Current
    # Pack Resistance
    #* Avg Cell Voltage (Sporadic, Dillon said to avoid)
    # DTC Flags 1
    # DTC Flags 2
    # Cell 68 Temp
    # Cell 65 Temp
    # Cell 50 Temp
    # Cell 63 Temp
    # Cell 56 Temp
    # Cell 53 Temp
    # Cell 44 Temp
    # Cell 41 Temp
    # Cell 32 Temp
    # Cell 29 Temp
    # Cell 26 Temp
    # Cell 39 Temp
    # Cell 20 Temp
    # Cell 15 Temp
    # Cell 8 Temp
    # Cell 2 Temp
    # Cell 17 Temp
    # Cell 5 Temp
    # LOW BAT TEMP
    # HIGH BAT TEMP
    # AVG BAT TEMP
    # HIGH TEMP ID
    # LOW TEMP ID
    # Brake Pres Front
    # Brake Pres Rear
    # Bat Volts Dash
    # INV FAULT BYTE 0
    # INV FAULT BYTE 1
    # INV FAULT BYTE 2
    # INV FAULT BYTE 3
    # INV FAULT BYTE 4
    # INV FAULT BYTE 5
    # INV FAULT BYTE 6
    # INV FAULT BYTE 7
    # Engine RPM
    # Drive Speed
    # Ground Speed
    # Wheel Slip
    # Wheel Speed FL
    # Wheel Speed FR
    # Wheel Speed RL
    # Wheel Speed RR
    # Damper Pos FL
    # Dash Temp
    # Direction Command
    # Steering Angle
    # Odometer
    # APPS Fault
    # Lap Distance
    #* Lap Time
    # Lap Speed
    # Fastest Lap Time
    # GPS Sats Used
    # GPS Altitude
    #* GPS Latitude
    #* GPS Longitude
    # GPS Heading
    # GPS Time
    # GPS Date
    # GPS Speed
    # GPS Quality
    # GPS HDOP
    # GPS Valid
    # Inline 1
    # Inline 2
    # Inline 3
    # HIGH_TEMP_TEMP
    # LOW_TEMP_TEMP