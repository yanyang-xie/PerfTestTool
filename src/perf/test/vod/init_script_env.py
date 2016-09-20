import os
import string
import sys

sys.path.append(os.path.join(os.path.split(os.path.realpath(__file__))[0], "../../.."))
from utility import common_util, vex_util, fab_util

def read_configurations():
    here = os.path.dirname(os.path.realpath(__file__))
    config_file = here + os.sep + 'config.properties'
    golden_config_file = here + os.sep + 'config-golden.properties'
    
    if not os.path.exists(config_file):
        print 'Configuration file \'%s\' does not exist'
        exit(1)
    
    # print 'Read configurtion files and setup fabric env'
    config_dict = common_util.load_properties(config_file)
    if os.path.exists(golden_config_file):
        config_dict.update(common_util.load_properties(golden_config_file))
    return config_dict

def set_fabric_env(config_dict):
    user = common_util.get_config_value_by_key(config_dict, 'test.machine.username', 'root')
    port = common_util.get_config_value_by_key(config_dict, 'test.machine.port', '22')
    pub_key = common_util.get_config_value_by_key(config_dict, 'test.machine.pubkey')
    password = common_util.get_config_value_by_key(config_dict, 'test.virtual.machine.password')
    test_machines = common_util.get_config_value_by_key(config_dict, 'test.machine.hosts')
    
    if pub_key is None and password is None:
        print 'pubkey and password must have one'
        exit(1)
    
    fab_util.set_roles(perf_test_machine_group, ['%s@%s:%s' % (user, host, port) for host in string.split(test_machines, ',')])   
    fab_util.set_key_file(pub_key)

config_dict = read_configurations()
perf_test_remote_script_dir = '/tmp/perf-test-script'
perf_test_remote_result_dir = common_util.get_config_value_by_key(config_dict, 'test.result.report.dir', '/tmp/load-test-result')
perf_test_name = common_util.get_config_value_by_key(config_dict, 'test.case.name', '')
perf_test_remote_result_dir = vex_util.get_test_result_tmp_dir(perf_test_remote_result_dir, perf_test_name)

perf_test_machine_group = 'perf_test_machines'
perf_test_script_zip_name = 'perf-test.zip'
perf_test_script_zip_file_dir = '/tmp'
perf_test_script_zip_file_name = perf_test_script_zip_file_dir + os.sep + perf_test_script_zip_name

load_test_multiple_script_file_name = 'execute_multi_test.py'
load_test_sigle_process_script_file = 'vod_perf_test.py'
