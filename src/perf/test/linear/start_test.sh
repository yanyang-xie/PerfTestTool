#!/bin/sh

perf_test_task="start"

perf_test_script_dir=${perf_test_script_dir:-`(cd "$(dirname "$0")"; pwd)`}
perf_test_script_dir=${perf_test_script_dir:-$1}
echo "Perftest script dir is: ${perf_test_script_dir}"

perf_test_scipt_file="${perf_test_script_dir}/execute_distributed_test.py"
echo "Perftest script is: ${perf_test_scipt_file}"

if [ ! -f "$perf_test_scipt_file" ]; then
    echo "Not found the performance test script ${perf_test_scipt_file}" >&2
    exit 1
fi

echo "python ${perf_test_scipt_file} ${perf_test_task}"
python ${perf_test_scipt_file} ${perf_test_task}

if [[ $? != 0 ]];then
	echo "Do performance test failed. ${ret}" >&2
	exit 2
fi

echo "Finish to ${perf_test_task}"
