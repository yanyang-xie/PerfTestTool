# -*- coding=utf-8 -*-
# author: yanyang.xie@gmail.com

import Queue
import logging
import os
import string
import sys
import threading

from utility import common_util, logger_util
from utility.counter import Counter

sys.path.append(os.path.join(os.path.split(os.path.realpath(__file__))[0], "../.."))

class PerfTestBase(object):
    '''
    Basic module for performance test
    '''
    def __init__(self, config_file, log_file, **kwargs):
        '''Initialized configuration and logs with a properties file and log file
        @param golden_config_file: will replace parameters in config file
        
        '''
        self.config_file = config_file
        self.log_file = log_file
        self.log_level = 'DEBUG'
        
        if not os.path.exists(self.config_file) or not os.path.isfile(self.config_file):
            raise Exception('Configuration file %s do not exist' % (self.config_file))
            sys.exit(1)
            
        self.parameters = common_util.load_properties(self.config_file)
        self.parameters.update(kwargs)
        
        if kwargs.has_key('golden_config_file'):
            golden_config_file = kwargs.get('golden_config_file')
            if os.path.exists(golden_config_file) and os.path.isfile(golden_config_file):
                self.parameters.update(common_util.load_properties(golden_config_file))
        
        if self.parameters.has_key('log.level'):
            self.log_level = self.parameters.get('log.level')
        self.init_log()

    def init_log(self):
        logger_util.setup_logger(self.log_file, log_level=self.log_level)
        self.logger = logging.getLogger()

    def _has_attr(self, attr_name):
        if not hasattr(self, attr_name):
            return False
        else:
            return getattr(self, attr_name, None)

    def _set_attr(self, attr_name, attr_value):
        setattr(self, attr_name, attr_value)

class APIPerfTestBase(PerfTestBase):
    def __init__(self, config_file, log_file, **kwargs):
        '''
        @param config_file: configuration file, must be a properties file
        @param log_file: log file absolute path
        '''
        super(APIPerfTestBase, self).__init__(config_file, log_file, **kwargs)
        self.init_environment()
    
    def init_environment(self, **kwargs):
        # setup your environment, such as counter, lock, recorder
        pass
    
    def generate_url_list(self):
        pass
    
    def do_load_test(self):
        pass
        

class VEXPerfTestBase(APIPerfTestBase):
    def __init__(self, config_file, log_file, **kwargs):
        
        '''
        @param config_file: configuration file, must be a properties file
        @param log_file: log file absolute path
        '''
        super(VEXPerfTestBase, self).__init__(config_file, log_file, **kwargs)
        self.result_dir = 'result_dir'
    
    def init_environment(self):
        self.init_configred_parameters()
        self.init_vex_counter()
        self.init_lock()
        self.init_recorder()
        self.init_result_dir()
    
    def init_configred_parameters(self):
        ''' Read configured parameters and then set general parameters as object attribute '''
        print '#' * 100
        print 'Initial general performance test parameters from configuration file %s' % (self.config_file)
        set_attr = lambda attr_name, config_name, default_value = None: self._set_attr(attr_name, common_util.get_config_value_by_key(self.parameters, config_name, default_value))
        
        set_attr('user', 'user', 'root')
    
    def init_vex_counter(self, **kwargs):
        default_counter_list = '0,200,500,1000,2000,3000,4000,5000,6000,12000'
        generate_counter = lambda couter_key, default: Counter(
                            [int(i) for i in string.split(
                                common_util.get_config_value_by_key(self.parameters, couter_key, default), ',')
                            ])
        self.index_response_counter = generate_counter('index.counter', default_counter_list)
        self.bitrate_response_counter = generate_counter('bitrate.counter', default_counter_list)
    
    def init_lock(self):
        self.index_lock = threading.RLock()
        self.bitrate_lock = threading.RLock()
    
    def init_recorder(self):
        self.bitrate_recorder = Queue.Queue()  # will be exported to local after delta report
        self.error_recorder = Queue.Queue()
    
    def init_result_dir(self):
        test_case_name = common_util.get_config_value_by_key(self.parameters, 'test_case_name')
        # result_dir = common_util.get_process_result_tmp_dir(process_number, constants.result_dir, test_case_name)
    
    def demo(self):
        self.index_response_counter.increment(200)
        print self.index_response_counter.dump()
        print self.logger
        print dir(self.logger)
        print self.logger.level
        print self.logger.name
        self.logger.info('1234')
        self.logger.debug('debug')
           
    
