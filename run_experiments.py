import os
import time
import subprocess
import shutil
import shlex

node0_interface = 'ens2f0'
node1_name = 'af28@clnode281.clemson.cloudlab.us'
node2_name = 'af28@clnode255.clemson.cloudlab.us'

#command = "ssh your_username@hostname 'command1; command2; command3'"

commands = 'sudo bash -c \' '
commands += 'cd /mydata/DCPerf; '
commands += "alternatives --set python3 /usr/bin/python3.8; "
commands += "scl enable gcc-toolset-11 bash; "

# Define the commands as individual components
cd_command = "cd /mydata/DCPerf; "
alternatives_command = "alternatives --set python3 /usr/bin/python3.8; "
#scl_command = "scl enable gcc-toolset-11 bash"
scl_command = "scl enable gcc-toolset-11 --"

# \"client_cores\": 16,
# Warmup time is 1200
# Test time is 720
# So I can wait for 1620, profile for 240 seconds

def shell_escape(s):
    """Escapes single quotes in a shell command string."""
    return s.replace("\"", "\"")
    #return s.replace("'", "\\'").replace("\"", "\\\\\\\"")

perf_tracking = 'perf'

def run_taobench(single_socket, memsize, num_ccd, set_get_ratio, access_dist):
    os.system('truncate -s 0 benchpress.log')
    # Make output folder
    output_folder_name = f"memsize_{memsize}_numccd_{num_ccd}_accessdist_{access_dist.replace(':', '_')}_setgetratio_{set_get_ratio.replace(':', '_')}"
    if os.path.isdir(output_folder_name):
        print(f'Skipping run due to folder ({output_folder_name}) already existing')
        return

    print(output_folder_name)
    os.system(f'mkdir {output_folder_name}')

    # \"test_time\": 10,
    # \"warmup_time\": 10,
    if perf_tracking == 'perf':
        server_command = f"./benchpress_cli.py run tao_bench_autoscale -i '{{\"num_servers\": 1, \"interface_name\": \"{node0_interface}\", \"server_hostname\": \"10.10.1.1\", \"memsize\": {memsize}, \"single_socket\": {single_socket}, \"num_ccd\": {num_ccd}, \"set_get_ratio\": \"{set_get_ratio}\", \"access_dist\": \"{access_dist}\ -k perf"}}'"
    else:
        server_command = f"./benchpress_cli.py run tao_bench_autoscale -i '{{\"num_servers\": 1, \"interface_name\": \"{node0_interface}\", \"server_hostname\": \"10.10.1.1\", \"memsize\": {memsize}, \"single_socket\": {single_socket}, \"num_ccd\": {num_ccd}, \"set_get_ratio\": \"{set_get_ratio}\", \"access_dist\": \"{access_dist}\"}}'"
    print(server_command)
    process = subprocess.Popen(shlex.split(server_command), stdout=open(f"{output_folder_name}/top_command_out.txt", "w"))

    # Wait for some time for the client commands to be dumped
    time.sleep(10)

    # Get client commands from benchpress.log
    client1_commands = ''
    client2_commands = ''
    with open('benchpress.log', 'r') as file:
        for line in file:
            if 'Client 1' in line:
                benchpress_command = next(file, '').strip('').strip("\n")
                client1_commands = [cd_command, scl_command, benchpress_command]
                client1_commands = ' '.join(client1_commands)
                client1_commands = shell_escape(client1_commands)

            if 'Client 2' in line:
                benchpress_command = next(file, '').strip('').strip("\n")
                client2_commands = [cd_command, scl_command, benchpress_command]
                client2_commands = ' '.join(client2_commands)
                client2_commands = shell_escape(client2_commands)

    client1_ssh_command = f"ssh -i /users/af28/.ssh/id_ed25519.pub {node1_name} \"sudo bash -c \\\"{client1_commands}\\\"\""
    client2_ssh_command = f"ssh -i /users/af28/.ssh/id_ed25519.pub {node2_name} \"sudo bash -c \\\"{client2_commands}\\\"\""

    print(client1_ssh_command)
    print(client2_ssh_command)
    subprocess.Popen(client1_ssh_command, shell=True)
    subprocess.Popen(client2_ssh_command, shell=True)

    # Wait for 1620
    time.sleep(1620)

    # Start profiling. This should be in the hot period
    #amd_uprof_command = f"/mydata/AMDuProf_Linux_x64_4.2.850/bin/AMDuProfPcm -m ipc,fp,l1,l2,l3,tlb,dc,memory,swpfdc,hwpfdc -c package=0 -C -A package -d 240"
    #print(amd_uprof_command)
    #process = subprocess.Popen(shlex.split(amd_uprof_command), stdout=open(f"{output_folder_name}/uprof_out.txt", "w"))
    #process.communicate()
    cpu_mask = ''
    if num_ccd == 1: # 9/36 cores
        cpu_mask = '0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34'
    elif num_ccd == 2: # 18/36 cores
        cpu_mask = '0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70'
    elif num_ccd == 4: # 36/36 cores
        cpu_mask = '0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,74,76,78,80,82,84,86,88,90,92,94,96,98,100,102,104,106,108,110,112,114,116,118,120,122,124,126,128,130,132,134,136,138,140,142'
    intel_vtune_command = f'vtune -collect uarch-exploration -knob pmu-collection-mode=summary -cpu-mask={cpu_mask} -d 240'
    process = subprocess.Popen(shlex.split(intel_vtune_command), stdout=open(f"{output_folder_name}/vtune_out.txt", "w"))

    time.sleep(300)

    # Test should be done, but add an extra 7 minutes to be sure (noticed during experimenting that there is some idle time at the end...)
    time.sleep(420)

    # Copy benchpress.log to the data output folder and clear its contents
    shutil.copyfile('benchpress.log', f'{output_folder_name}/benchpress.log')
    os.system('truncate -s 0 benchpress.log')

    # Move benchmark_metrics*
    os.system(f'mv benchmark_metrics* {output_folder_name}/')

    # Move vtune output in case it is needed
    #os.system(f'mv *ue {output_folder_name}/')

    # Move client outputs and client benchpresses
    os.system(f'scp -i /users/af28/.ssh/id_ed25519 {node1_name}:/mydata/DCPerf/client1_out.txt /mydata/DCPerf/{output_folder_name}/client1_out.txt')
    os.system(f'scp -i /users/af28/.ssh/id_ed25519 {node2_name}:/mydata/DCPerf/client2_out.txt /mydata/DCPerf/{output_folder_name}/client2_out.txt')

    os.system(f'scp -i /users/af28/.ssh/id_ed25519 {node1_name}:/mydata/DCPerf/benchpress.log /mydata/DCPerf/{output_folder_name}/client1_benchpress.log')
    os.system(f'scp -i /users/af28/.ssh/id_ed25519 {node2_name}:/mydata/DCPerf/benchpress.log /mydata/DCPerf/{output_folder_name}/client2_benchpress.log')

    os.system(f"ssh -i /users/af28/.ssh/id_ed25519 {node1_name} sudo bash -c \"truncate -s 0 client1_out.txt; truncate -s 0 benchpress.log;\"")
    os.system(f"ssh -i /users/af28/.ssh/id_ed25519 {node2_name} sudo bash -c \"truncate -s 0 client2_out.txt; truncate -s 0 benchpress.log;\"")
    
    time.sleep(30)

# Vary number of cores

"""
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
                run_taobench(1, memsize, num_ccd, set_get_ratio, access_dist)

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
                run_taobench(1, memsize, num_ccd, set_get_ratio, access_dist)

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
                run_taobench(1, memsize, num_ccd, set_get_ratio, access_dist)

"""