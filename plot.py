import matplotlib
import re

total_qps = {}
ipc = {}
frontend_stall = {}
bad_speculation = {}
backend_stall = {}

def get_results(single_socket, memsize, num_ccd, set_get_ratio, access_dist):
    output_folder_name = f"memsize_{memsize}_numccd_{num_ccd}_accessdist_{access_dist.replace(':', '_')}_setgetratio_{set_get_ratio.replace(':', '_')}"
    out_file = open(output_folder_name+'/top_command_out.txt', 'r')

    if output_folder_name not in list(total_qps.keys()):
        for line in out_file:
            if 'total_qps' in line:
                total_qps[output_folder_name] = float(re.search(r"[-+]?\d*\.\d+|\d+", line).group())
                break
    
    vtune_file = open(output_folder_name+'/vtune_out.txt', 'r')

# Experiment 1
# See how memory footprint affects performance
memsizes = [100, 50, 1]
num_ccds = [4]
set_get_ratios = ['0_1']
access_dists = ['R_R']

for memsize in memsizes:
    for num_ccd in num_ccds:
        for set_get_ratio in set_get_ratios:
            for access_dist in access_dists:
                get_results(1, memsize, num_ccd, set_get_ratio, access_dist)

# Experiment 2
# See how access distribution affects scaling
memsizes = [100]
num_ccds = [1, 2, 4]
set_get_ratios = ['0_1']
access_dists = ['R_R', 'G_G']

for memsize in memsizes:
    for num_ccd in num_ccds:
        for set_get_ratio in set_get_ratios:
            for access_dist in access_dists:
                get_results(1, memsize, num_ccd, set_get_ratio, access_dist)

# Experiment 3
# See how R/W ratio affects scaling
memsizes = [100]
num_ccds = [1, 2, 4]
set_get_ratios = ['0_1', '1_99', '1_9', '3_7']
access_dists = ['G_G']

for memsize in memsizes:
    for num_ccd in num_ccds:
        for set_get_ratio in set_get_ratios:
            for access_dist in access_dists:
                get_results(1, memsize, num_ccd, set_get_ratio, access_dist)

for key in list(total_qps.keys()):
    print(total_qps[key])
print(float(re.search(r"[-+]?\d*\.\d+|\d+", '"total_qps": 1696069.1344827588,').group()))


import numpy as np
import matplotlib.pyplot as plt

exps = ['memsize_100_numccd_4_accessdist_R_R_setgetratio_0_1', 'memsize_50_numccd_4_accessdist_R_R_setgetratio_0_1', 'memsize_1_numccd_4_accessdist_R_R_setgetratio_0_1']
yvals = [total_qps[exp]/1000000 for exp in exps]
exp_names = ['100GB', '50GB', '1GB']
print('Other exp details: All cores, uniform random key distribution, all reads')
plt.bar(exp_names, yvals)
plt.ylabel('Queries Per Second (M)')
plt.xlabel('Memory Size')
plt.title('QPS for Various DRAM Capacity')
plt.savefig('qps.png')

