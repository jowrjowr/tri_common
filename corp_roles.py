import enum

# from ccp snowedin
# these are the roles that can be returned by the roles endpoint

class Corp_roles(enum.Enum):
   Director = 1
   Personnel_Manager = 128
   Accountant = 256
   Security_Officer = 512
   Factory_Manager = 1024
   Station_Manager = 2048
   Auditor = 4096
   Hangar_Take_1 = 8192
   Hangar_Take_2 = 16384
   Hangar_Take_3 = 32768
   Hangar_Take_4 = 65536
   Hangar_Take_5 = 131072
   Hangar_Take_6 = 262144
   Hangar_Take_7 = 524288
   Hangar_Query_1 = 1048576
   Hangar_Query_2 = 2097152
   Hangar_Query_3 = 4194304
   Hangar_Query_4 = 8388608
   Hangar_Query_5 = 16777216
   Hangar_Query_6 = 33554432
   Hangar_Query_7 = 67108864
   Account_Take_1 = 134217728
   Account_Take_2 = 268435456
   Account_Take_3 = 536870912
   Account_Take_4 = 1073741824
   Account_Take_5 = 2147483648
   Account_Take_6 = 4294967296
   Account_Take_7 = 8589934592
   Diplomat = 17179869184
   Config_Equipment = 2199023255552
   Container_Take_1 = 4398046511104
   Container_Take_2 = 8796093022208
   Container_Take_3 = 17592186044416
   Container_Take_4 = 35184372088832
