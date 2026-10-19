Alginment and labeling of alarm and process data
1. Extract binary features from the alarm data:
    FIC301,FIC302,LI405,LI502,PT312,VC303,VC401,VC403,VC404,VC405,VC406,VLV303 are present in the the alarm logs
    Each alarm log contains the timestamp, the corresponding sensor tag and status information, whether they are 
    active or inactive. The alarm log entires are transformed into a binary form: 
    The binary alarm value of alarm Aik is 0 if no active Ai for timestamp k and no previous active Ai; or latest Ai was inactive.
    The binary alarm value of alarm Aik is 1 if no active Ai for timestamp k and latest Ai was active; or active Ai for timestamp k.
    See output files: alarmsfault07092017_proc.csv, alarmsonly11092017_proc.csv, alarmsonly12092017_proc.csv

2. Order alarms in historical orders from least recent to most recent. (The alarm log contains entries with decreasing time stamps)

3. Merge alarm and process data by timestamp

4. Create one input water and air flow rate column based on the opeartion log

5. Label data by health condition based on the opertion log