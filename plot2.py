import pandas as pd
import glob
import numpy as np 
import re
import matplotlib.pyplot as plt

#output_folder_name = f"memsize_{memsize}_numcores_{num_cores}_accessdist_{access_dist.replace(':', '_')}_setgetratio_{set_get_ratio.replace(':', '_')}_ways_{str(ways)}_bw_{str(bw)}"

def get_metric_list(folder, metric):
    #print(output_folder_name + '/benchmark_metrics_tao*/topdown-intel.sys.csv')
    file = glob.glob(folder + '/benchmark_metrics_tao*/topdown-intel.sys.csv')[0]

    df = pd.read_csv(file)

    start_time = 1400
    end_time = 1720

    filtered_df = df[(df['time'] >= start_time) & (df['time'] <= end_time)]
    metric_values = filtered_df[metric]
    return np.array(metric_values)

def get_total_qps(folder):
    out_file = open(folder+'/top_command_out.txt', 'r')

    for line in out_file:
        if 'total_qps' in line:
            return float(re.search(r"[-+]?\d*\.\d+|\d+", line).group())

# Vary number of cores
topdown_metric_list =['metric_IPC', 'metric_L1D MPI (includes data+rfo w/ prefetches)']

cores = []
frontend_bound = []
backend_bound = []
retiring_bound = []
bad_speculation_bound = []
ipc = []
qps_per_core = []
l3_mpi = []

memsizes = [64]
num_cores_list = [9, 18, 27, 36]
set_get_ratios = ['0_1']
access_dists = ['R_R']
wayss = [12]
bws = [100]

for memsize in memsizes:
    for num_cores in num_cores_list:
        for set_get_ratio in set_get_ratios:
            for access_dist in access_dists:
                for ways in wayss:
                    for bw in bws:
                        output_folder_name = f"memsize_{memsize}_numcores_{num_cores}_accessdist_{access_dist.replace(':', '_')}_setgetratio_{set_get_ratio.replace(':', '_')}_ways_{str(ways)}_bw_{str(bw)}"
                        print(output_folder_name)
                        qps = get_total_qps(output_folder_name)
                        qps_per_core.append(qps/num_cores)
                        print("total_qps -> " + str(qps))

                        for metric in topdown_metric_list:
                            metric_val = np.mean(get_metric_list(output_folder_name, metric))
                            print(metric+ " -> " + str(metric_val))

                        backend_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Backend_Bound(%)")))
                        bad_speculation_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Bad_Speculation(%)")))
                        frontend_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Frontend_Bound(%)")))
                        retiring_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Retiring(%)")))
                        ipc.append(np.mean(get_metric_list(output_folder_name, "metric_IPC")))
                        l3_mpi.append(np.mean(get_metric_list(output_folder_name, "metric_LLC data read MPI (demand+prefetch)")))
                        cores.append(num_cores)

# Create the figure and axes
fig, ax = plt.subplots()
bar_width = 3
ax.bar(cores, backend_bound, width=bar_width, label='Backend Bound')
ax.bar(cores, frontend_bound, width=bar_width, bottom=backend_bound, label='Frontend Bound')
ax.bar(cores, bad_speculation_bound, width=bar_width, bottom=np.array(backend_bound) + np.array(frontend_bound), label='Bad Speculation')
ax.bar(cores, retiring_bound, width=bar_width, bottom=np.array(backend_bound) + np.array(frontend_bound) + np.array(bad_speculation_bound), label='Retiring')
ax.set_xlabel('# of Cores')
ax.set_ylabel('%')
ax.set_title('Taobench CPI Stacks vs # of Cores')
ax.set_xticks(cores)
ax.legend()
plt.savefig('cores_vs_stalls.png', format='png', dpi=300)
fig, ax = plt.subplots()
ax.bar(cores, qps_per_core,width=bar_width)
ax.set_xticks(cores)
ax.set_xlabel('# of Cores')
ax.set_ylabel('Queries Per Second Per Core')
ax.set_title('Per-core Throughput vs # of Cores')
plt.savefig('qps_per_core.png', format='png', dpi=300)
fig, ax = plt.subplots()
ax.bar(cores, ipc,width=bar_width)
ax.set_xticks(cores)
ax.set_xlabel('# of Cores')
ax.set_ylabel('IPC (while unhalted)')
ax.set_title('IPC vs # of Cores')
plt.savefig('ipc_vs_cores.png', format='png', dpi=300)

fig, ax = plt.subplots()
ax.bar(cores, np.array(l3_mpi)*1000, width=bar_width)
ax.set_xticks(cores)
ax.set_xlabel('# of Cores')
ax.set_ylabel('L3 Miss Per 1K Inst. (Demand + Prefetch)')
ax.set_title('L3 MPKI vs # of Cores')
plt.savefig('l3_mpki_vs_cores.png', format='png', dpi=300)


# Vary number of LLC ways
way = []
cores = []
frontend_bound = []
backend_bound = []
retiring_bound = []
bad_speculation_bound = []
ipc = []
qps_list = []
l3_mpi = []

memsizes = [64]
num_cores_list = [36]
set_get_ratios = ['0_1']
access_dists = ['R_R']
wayss = [4, 8, 12]
bws = [100]

for memsize in memsizes:
    for num_cores in num_cores_list:
        for set_get_ratio in set_get_ratios:
            for access_dist in access_dists:
                for ways in wayss:
                    for bw in bws:
                        output_folder_name = f"memsize_{memsize}_numcores_{num_cores}_accessdist_{access_dist.replace(':', '_')}_setgetratio_{set_get_ratio.replace(':', '_')}_ways_{str(ways)}_bw_{str(bw)}"

                        qps = get_total_qps(output_folder_name)
                        qps_list.append(qps)

                        backend_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Backend_Bound(%)")))
                        bad_speculation_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Bad_Speculation(%)")))
                        frontend_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Frontend_Bound(%)")))
                        retiring_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Retiring(%)")))
                        ipc.append(np.mean(get_metric_list(output_folder_name, "metric_IPC")))
                        l3_mpi.append(np.mean(get_metric_list(output_folder_name, "metric_LLC data read MPI (demand+prefetch)")))
                        cores.append(num_cores)
                        way.append(ways)

# Create the figure and axes
fig, ax = plt.subplots()
bar_width = 1.5
ax.bar(way, backend_bound, width=bar_width, label='Backend Bound')
ax.bar(way, frontend_bound, width=bar_width, bottom=backend_bound, label='Frontend Bound')
ax.bar(way, bad_speculation_bound, width=bar_width, bottom=np.array(backend_bound) + np.array(frontend_bound), label='Bad Speculation')
ax.bar(way, retiring_bound, width=bar_width, bottom=np.array(backend_bound) + np.array(frontend_bound) + np.array(bad_speculation_bound), label='Retiring')
ax.set_xlabel('# of LLC Ways')
ax.set_ylabel('%')
ax.set_title('Taobench CPI Stacks vs # of LLC Ways')
ax.set_xticks(way)
ax.legend()
plt.savefig('ways_vs_stalls.png', format='png', dpi=300)
fig, ax = plt.subplots()
ax.bar(way, qps_list,width=bar_width)
ax.set_xticks(way)
ax.set_xlabel('# of LLC Ways')
ax.set_ylabel('Queries Per Second')
ax.set_title('Throughput vs # of LLC Ways')
plt.savefig('qps_vs_ways.png', format='png', dpi=300)
fig, ax = plt.subplots()
ax.bar(way, ipc,width=bar_width)
ax.set_xticks(way)
ax.set_xlabel('# of LLC Ways')
ax.set_ylabel('IPC (while unhalted)')
ax.set_title('IPC vs # of LLC Ways')
plt.savefig('ipc_vs_ways.png', format='png', dpi=300)
fig, ax = plt.subplots()
ax.bar(way, np.array(l3_mpi)*1000, width=bar_width)
ax.set_xticks(way)
ax.set_xlabel('# of LLC Ways')
ax.set_ylabel('L3 Miss Per 1K Inst. (Demand + Prefetch)')
ax.set_title('L3 MPKI vs # of Ways')
plt.savefig('l3_mpki_vs_ways.png', format='png', dpi=300)

# Vary number of LLC ways
way = []
cores = []
frontend_bound = []
backend_bound = []
retiring_bound = []
bad_speculation_bound = []
ipc = []
qps_list = []
l3_mpi = []
bw_list = []

memsizes = [64]
num_cores_list = [36]
set_get_ratios = ['0_1']
access_dists = ['R_R']
wayss = [12]
bws = [30, 50, 80, 100]

for memsize in memsizes:
    for num_cores in num_cores_list:
        for set_get_ratio in set_get_ratios:
            for access_dist in access_dists:
                for ways in wayss:
                    for bw in bws:
                        output_folder_name = f"memsize_{memsize}_numcores_{num_cores}_accessdist_{access_dist.replace(':', '_')}_setgetratio_{set_get_ratio.replace(':', '_')}_ways_{str(ways)}_bw_{str(bw)}"

                        qps = get_total_qps(output_folder_name)
                        qps_list.append(qps)

                        backend_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Backend_Bound(%)")))
                        bad_speculation_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Bad_Speculation(%)")))
                        frontend_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Frontend_Bound(%)")))
                        retiring_bound.append(np.mean(get_metric_list(output_folder_name, "metric_TMA_Retiring(%)")))
                        ipc.append(np.mean(get_metric_list(output_folder_name, "metric_IPC")))
                        l3_mpi.append(np.mean(get_metric_list(output_folder_name, "metric_LLC data read MPI (demand+prefetch)")))
                        cores.append(num_cores)
                        way.append(ways)
                        bw_list.append(bw)

# Create the figure and axes
fig, ax = plt.subplots()

#ax.set_xticks([1,2,3,4])
#ax.set_xticklabels('30', '50', '80', '100')
bar_width = .66

ax.bar([1,2,3,4], backend_bound, width=bar_width, label='Backend Bound')
ax.bar([1,2,3,4], frontend_bound, width=bar_width, bottom=backend_bound, label='Frontend Bound')
ax.bar([1,2,3,4], bad_speculation_bound, width=bar_width, bottom=np.array(backend_bound) + np.array(frontend_bound), label='Bad Speculation')
ax.bar([1,2,3,4], retiring_bound, width=bar_width, bottom=np.array(backend_bound) + np.array(frontend_bound) + np.array(bad_speculation_bound), label='Retiring')
ax.set_xlabel('Memory Bandwidth')
ax.set_ylabel('%')
ax.set_title('Taobench CPI Stacks vs Memory Bandwidth')
ax.set_xticks([1,2,3,4])
ax.set_xticklabels(['30', '50', '80', '100'])

ax.legend()
plt.savefig('bw_vs_stalls.png', format='png', dpi=300)
fig, ax = plt.subplots()
ax.bar([1,2,3,4], qps_list,width=bar_width)
ax.set_xticks([1,2,3,4])
ax.set_xticklabels(['30', '50', '80', '100'])
ax.set_xlabel('Memory Bandwidth')
ax.set_ylabel('Queries Per Second')
ax.set_title('Throughput vs Memory Bandwidth')
plt.savefig('qps_vs_bw.png', format='png', dpi=300)
fig, ax = plt.subplots()
ax.bar([1,2,3,4], ipc,width=bar_width)
ax.set_xticks([1,2,3,4])
ax.set_xticklabels(['30', '50', '80', '100'])

ax.set_xlabel('Memory Bandwidth')
ax.set_ylabel('IPC (while unhalted)')
ax.set_title('IPC vs Memory Bandwidth')
plt.savefig('ipc_vs_bw.png', format='png', dpi=300)
fig, ax = plt.subplots()
ax.bar([1,2,3,4], np.array(l3_mpi)*1000, width=bar_width)
ax.set_xticks([1,2,3,4])
ax.set_xticklabels(['30', '50', '80', '100'])

ax.set_xlabel('Memory Bandwidth')
ax.set_ylabel('L3 Miss Per 1K Inst. (Demand + Prefetch)')
ax.set_title('L3 MPKI vs Memory Bandwidth')
plt.savefig('l3_mpki_vs_bw.png', format='png', dpi=300)
