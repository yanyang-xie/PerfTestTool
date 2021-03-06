# -*- coding=utf-8 -*-
# author: yanyang.xie@thistech.com

'''
Distributed load test script
'''
from fabric.context_managers import settings, cd, lcd
from fabric.contrib.files import exists
from fabric.operations import run, put, local
from fabric.tasks import execute

from init_script_env import *
from perf.model.vex_distribute import DistributeEnv
from utility import fab_util, vex_util

class DistributePerfTest(DistributeEnv):
    def __init__(self, config_file, **kwargs):
        '''
        @param config_file: configuration file, must be a properties file
        '''
        super(DistributePerfTest, self).__init__(config_file, **kwargs)
        self.project_dir, self.package_path = here.split('src')
        self.project_source_dir = self.project_dir + os.sep + 'src'
        fab_util.set_roles(perf_test_machine_group, self.test_machine_hosts,)
    
    def rm_perf_test_log(self):
        perf_test_remote_result_dir = getattr(self, 'test_result_report_dir') if hasattr(self, 'test_result_report_dir') else ''
        perf_test_name = getattr(self, 'test_case_name') if hasattr(self, 'test_case_name') else perf_test_remote_result_default_dir
        perf_test_remote_result_dir = vex_util.get_test_result_tmp_dir(perf_test_remote_result_dir, perf_test_name)
        run('rm -rf %s' % (perf_test_remote_result_dir), pty=False)
    
    def stop_perf_test(self):
        fab_util.fab_shutdown_service(load_test_sigle_process_script_file)
    
    def start_perf_test(self):
        self.upload_test_script()
        with cd(perf_test_remote_script_dir + self.package_path):
            run('nohup python %s >/dev/null 2>&1' % (load_test_multiple_script_file_name), shell=False, pty=True, quiet=False)
    
    def execute_task(self, method):
        if method not in ['rm_perf_test_log', 'stop_perf_test']:
            self.zip_perf_test_script()
        
        with settings(parallel=True, roles=[perf_test_machine_group, ]):
            execute(getattr(self, method))
    
    def check_perf_test_status(self):
        pids = fab_util.fab_get_pids(load_test_sigle_process_script_file)
        if pids is None or pids == '':
            print 'Performance test script %s is not running' %(load_test_sigle_process_script_file)
            exit(3)
    
    def upload_test_script(self):
        # create script folder in remote machine
        if exists(perf_test_remote_script_dir):
            run('rm -rf %s' % (perf_test_remote_script_dir))
        run('mkdir -p %s' % (perf_test_remote_script_dir))
        
        # upload zipped file to remote and then unzip
        with lcd(perf_test_script_zip_file_dir):
            put(perf_test_script_zip_name, perf_test_remote_script_dir)
        
        with cd(perf_test_remote_script_dir):
            run('unzip -o %s -d %s' % (perf_test_script_zip_name, perf_test_remote_script_dir), quiet=True)
    
    def zip_perf_test_script(self):
        with lcd(self.project_source_dir):
            if os.path.exists(perf_test_script_zip_file_name):
                os.remove(perf_test_script_zip_file_name)
            zip_command = 'zip -r %s perf utility' % (perf_test_script_zip_file_name)
            local(zip_command, capture=True)

if __name__ == '__main__':
    distribute_test = DistributePerfTest(config_file, golden_config_file=golden_config_file)
    task_name = sys.argv[1] if len(sys.argv) > 1 else 'restart'
    
    if task_name == 'stop':
        distribute_test.execute_task('stop_perf_test')
    elif task_name == 'start':
        distribute_test.execute_task('stop_perf_test')
        distribute_test.execute_task('rm_perf_test_log')
        distribute_test.execute_task('start_perf_test')
    elif task_name == 'status':
        distribute_test.execute_task('check_perf_test_status')
    else:
        print 'Not support the method'
        exit(1)
