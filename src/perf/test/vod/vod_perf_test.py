# -*- coding=utf-8 -*-
# author: yanyang.xie@thistech.com
import uuid
import random

from init_script_env import *
from perf.model.vex_perf_test import VEXPerfTestBase
from perf.parser.manifest import VODManifestChecker
from utility import time_util

test_type_options = ['VOD_T6', 'OTHER:VOD']

index_url_format = 'http://%s/%s/king/index.m3u8?ProviderId=%s&AssetId=abcd1234567890123456&StreamType=%s&sid=%s&DeviceId=X1&PartnerId=hello&dtz=2015-04-09T18:39:05Z'
index_url_format_https = 'https://%s/%s/king/index.m3u8?ProviderId=%s&AssetId=abcd1234567890123456&StreamType=%s&sid=%s&DeviceId=X1&PartnerId=hello&dtz=2015-04-09T18:39:05Z'

default_vex_cluster_host='mm.vod.comcast.net'

class VODPerfTest(VEXPerfTestBase):
    def __init__(self, config_file, current_process_index=0, **kwargs):
        '''
        @param config_file: configuration file, must be a properties file
        @param current_process_index: used to generate current concurrent request number , should less than total process number
        @param log_file: log file absolute path
        '''
        self.test_case_vex_cluster_host = default_vex_cluster_host
        super(VODPerfTest, self).__init__(config_file, current_process_index=current_process_index, **kwargs)
    
    def set_component_private_default_value(self):
        self._set_attr('export_concurrent_number', True, True)
        self._set_attr('client_response_asset_tag', 'vod')
        self._set_attr('test_type_options', test_type_options)

        if self._has_attr('test_case_https') is True: 
            self._set_attr('index_url_format', index_url_format_https)
        else:
            self._set_attr('index_url_format', index_url_format)

        self._set_attr('warm_up_time_gap', 1)  # in warm up stage, time gap in each requests bundle 
        self._set_attr('test_require_sap', False)
        self._set_attr('fake_file_dir', os.path.dirname(os.path.realpath(__file__)))
        
        if hasattr(self, 'client_response_check_percent'):
            self.client_response_check_percent = float(self.client_response_check_percent)
            if self.client_response_check_percent <= 0 or self.client_response_check_percent > 1:
                self.client_response_check_when_running = False
                self.check_percent_factor = 1000000
            else:    
                self.check_percent_factor = int(1 / self.client_response_check_percent)
        else:
            self.check_percent_factor = 1
        
        # for X-Playback-Session-Id
        self._set_attr('test_client_x_playback_send', False, False)
        self._set_attr('test_client_x_playback_send_index_time_gap', 500, False)
            
    def generate_index_url(self):
        content_name = self._get_random_content()
        
        sid = str(uuid.uuid4())
        return self.index_url_format % (self.test_case_vex_cluster_host, content_name, content_name, self.test_case_type, sid)
    
    def generate_task_headers(self):
        headers = {}
        # add money-trace header
        # X-MoneyTrace:trace-id=91a6bb69-04a4-48e1-b691-f8196e91216f;parent-id=894b9bd6-7521-4726-b653-1ddcee1e0c6d;span-id=cf7e938a-72f1-4ad1-b970-83d93c6243c1
        money_trace_value = "trace-id=%s;parent-id=%s;span-id=%s" %(uuid.uuid4(),random.randint(0,100000000),random.randint(0,100000000))
        headers['X-MoneyTrace'] = money_trace_value
        
        if self._has_attr('test_client_x_playback_send') is True:
            headers['X-Playback-Session-Id'] = str(uuid.uuid4())

        return headers
    
    def schedule_bitrate(self, task, bitrate_url_list):
        for i, bitrate_url in enumerate(bitrate_url_list):
            b_task = task.clone()
            delta_milliseconds = self.test_bitrate_serial_time * (i + 1) if self.test_bitrate_serial else self.test_bitrate_serial_time
            start_date = time_util.get_datetime_after(time_util.get_local_now(), delta_milliseconds=delta_milliseconds)
            b_task.set_bitrate_url(bitrate_url)
            b_task.set_start_date(start_date)
            self.logger.debug('Schedule bitrate request at %s. task:%s' % (start_date, b_task))
            self.task_consumer_sched.add_date_job(self.do_bitrate, start_date, args=(b_task,))
    
    def do_index_subsequent_step(self, task):
        if self._has_attr('test_client_x_playback_send') is True:
            new_task = task.clone()
            if new_task.headers.has_key('X-Playback-Session-Id'):
                new_task.headers.pop('X-Playback-Session-Id')
                start_date = time_util.get_datetime_after(time_util.get_local_now(), delta_milliseconds=self.test_client_x_playback_send_index_time_gap)   
                self.logger.debug("X-playback is enabled, send the second index at %s, task: %s" %(start_date, new_task))
                self.task_consumer_sched.add_date_job(self.do_bitrate, start_date, args=(new_task,))
    
    def do_bitrate_subsequent_step(self, task, response_text):
        if self._has_attr('send_psn_message') is False and self._has_attr('client_response_check_when_running') is False:
            return
        
        self.logger.debug('Bitrate response for task[%s]:\n%s' % (task, response_text,))
        
        checker = None
        if self._has_attr('client_response_check_when_running') is True and self.bitrate_counter.total_count % self.check_percent_factor == 0:
            try:
                checker = VODManifestChecker(response_text, task.get_bitrate_url(), psn_tag=self.psn_tag, ad_tag=self.client_response_ad_tag, sequence_tag=self.client_response_media_tag, asset_id_tag=self.client_response_asset_tag)
                self.check_response(task, checker)
            except Exception, e:
                self.logger.error("failed to check. task:%s, exception:%s" %(task, e))
        
        if self._has_attr('send_psn_message') is True:
            if checker is None:
                checker = VODManifestChecker(response_text, task.get_bitrate_url(), psn_tag=self.psn_tag, ad_tag=self.client_response_ad_tag, sequence_tag=self.client_response_media_tag, asset_id_tag=self.client_response_asset_tag)
            
            psn_gap_list = [1 + int(self.client_response_content_segment_time * self.client_response_ad_mid_roll_ts_number * float(i)) for i in self.psn_message_sender_position]
            if self._has_attr('psn_send') is True:
                self.send_psn(task, checker.psn_tracking_position_id_dict, psn_gap_list)
            elif self._has_attr('psn_fake_send') is True:
                self.send_psn(task, self.psn_fake_tracking_position_id_dict, psn_gap_list)
            
            if self._has_attr('psn_endall_send') is True:
                self.send_endall_psn(task)
        
    def check_response(self, task, manifest_checker):
        self.logger.debug('Check bitrate client response. task: %s' % (task))
        error_message = manifest_checker.check(self.client_response_media_sequence, self.client_response_content_segment_number,
                self.client_response_endlist_tag, self.client_response_drm_tag, self.client_response_ad_mid_roll_position, self.client_response_ad_pre_roll_ts_number,
                self.client_response_ad_mid_roll_ts_number, self.client_response_ad_post_roll_ts_number,)
        if error_message is not None and error_message != '':
            if self._has_attr('client_response_error_dump') is True:
                self.logger.error('%s, Manifest:%s' % (error_message, manifest_checker.manifest))
            else:
                self.logger.error('%s' % (error_message))
            
            self.error_record_queue.put('%-17s: %s' % (task.get_client_ip(), error_message), False, 2)
            self._increment_counter(self.bitrate_counter, self.bitrate_lock, is_error_response=True)
    
    def dispatch_task_with_max_request(self):
        self.logger.info('Start to do vod performance with max current request %s of this process' % (self.current_processs_concurrent_request_number))
        self.dispatch_task_sched.add_interval_job(self._fetch_task_and_add_to_consumer, seconds=1)
        #self.dispatch_task_sched.add_interval_job(self.periodic_update_config_in_db, seconds=60)
    
    def _fetch_task_and_add_to_consumer(self):
        # Fetch task from task queue, and add it to task consumer
        self.logger.debug('Put %s tasks into task schedule.' % (self.current_processs_concurrent_request_number))
        for i in range(0, self.current_processs_concurrent_request_number):
            try:
                task = self.task_queue.get(True, 6)
                start_date = time_util.get_datetime_after(time_util.get_local_now(), delta_seconds=1)
                task.set_start_date(start_date)
                self.logger.debug('Task will be execute at %s. task:%s' % (start_date, task))
                self.task_consumer_sched.add_date_job(self.do_index, start_date, args=(task,))
            except Exception, e:
                self.logger.error('Failed to fetch task from task queue', e)
    
    def _generate_warm_up_list(self):
        warm_up_period_minute = self._has_attr('test_case_warmup_period_minute')
        if not warm_up_period_minute:
            return []
        
        warm_up_list = []
        if warm_up_period_minute and warm_up_period_minute > 1:
            warm_up_minute_list = self._generate_warm_up_minute_list(self.current_processs_concurrent_request_number, warm_up_period_minute)
            warm_up_minute_list = self._enlarge_warm_up_list(warm_up_minute_list, warm_up_period_minute)
            self.logger.info('Warm-up period is %s minute, warm-up list is:%s' % (warm_up_period_minute, warm_up_minute_list))
        else:
            self.logger.debug('Warm-up period is not set or its value <1, not do warm up')
            return []
        
        # to VOD, export warm up rate by seconds
        for t in warm_up_minute_list:
            for i in range(0, 1 * 60):
                warm_up_list.append(t)
        
        return warm_up_list

    def _enlarge_warm_up_list(self, warm_up_minute_list, warm_up_period_minute):
        if len(warm_up_minute_list) >= warm_up_period_minute:
            return warm_up_minute_list
        
        n, m =  divmod(warm_up_period_minute, len(warm_up_minute_list))
        new_warm_up_minute_list = []
        for i in warm_up_minute_list:
            new_warm_up_minute_list += [i] * n
        
        if m > 0:
            new_warm_up_minute_list += [warm_up_minute_list[-1]] * m
        return new_warm_up_minute_list
    
    def _generate_warm_up_minute_list(self, total_number, warm_up_period_minute):
        increase_step = total_number / warm_up_period_minute if total_number > warm_up_period_minute else 1

        warm_up_minute_list = []
        tmp_number = increase_step
        while True:
            if tmp_number <= total_number:
                warm_up_minute_list.append(tmp_number)
                tmp_number += increase_step
            else:
                break
        return warm_up_minute_list

if __name__ == '__main__':
    current_process_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    pert_test = VODPerfTest(config_file, current_process_index, golden_config_file=golden_config_file)
    pert_test.run()
