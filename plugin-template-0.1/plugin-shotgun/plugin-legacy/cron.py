# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
import os, sys
import time
import datetime
import yaml
import subprocess
import shlex
import codecs
import traceback
import random  # DEBUG
from threading import Thread
import requests
import logging
from logging import DEBUG

logging.basicConfig()
logging.getLogger().setLevel(DEBUG)
logger = logging.getLogger('legacy.cron')

RUNNING = {}


def parse_config(configPath):
    config = None
    with open(configPath) as f:
        try:
            config = yaml.safe_load(f)
        except Exception as e: # pragma: not covered
            print(str(e), file=sys.stderr) # pragma: not covered
    return config


class CronRunner:
    # TODO - Make cron emailer?
    # TODO - Need secrets for passwords in Global Configurations
    
    def __init__(self, plugname, cfg_file=None, testing=False, print_capturer=None):
        self.testing = testing
        self.print_capturer = print_capturer
        self.msgDiverter = None
        if self.print_capturer:
            self.msgDiverter = codecs.open(self.print_capturer, 'w', 'utf-8')
        self.ckey = "Cron Jobs"
        self.plugname = plugname
        self.config_file = '/plugin/ca.control'
        if cfg_file:
            self.config_file = cfg_file
        self.conf = parse_config(self.config_file)
        self.last_atime, self.last_mtime = self.get_last_times(self.config_file)
        self.last_mtime = 0.0
        self.today = self.get_today()
        self.cron_jobs = self.get_crons()
        self.checkTime = time.time()
        if not self.testing:
            self.runIfOnLoad() # pragma: not covered
            self.next_hour = self.get_next_hour() # pragma: not covered

    def pr_e(self, msg):
        if not self.print_capturer:
            logger.error(msg) # pragma: not covered
        else:
            self.msgDiverter.write('%s\n' % msg)

    def pr_o(self, msg): # pragma: not covered
        if not self.print_capturer: # pragma: not covered
            logger.info(msg) # pragma: not covered
        else: # pragma: not covered
            self.msgDiverter.write('%s\n' % msg) # pragma: not covered

    def get_last_times(self, fp):
        atime = '0.0'
        mtime = '0.0'
        try:
            info = os.stat(fp)
            atime = str(info.st_atime)
            mtime = str(info.st_mtime)
        except:
            self.pr_e("Cron Jobs for %s could not get atime or mtime from "
                                 "config file: '%s'" % (self.plugname, fp))
        return atime, mtime

    def numbered_months(self, months):
        all_months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] 
        if not months or months[0] == '*':
            return all_months 
        num_months = []
        translations = {
                        'january': 1, 'jan': 1,
                        'february': 2, 'feb': 2,
                        'march': 3, 'mar': 3,
                        'april': 4, 'apr': 4,
                        'may': 5,
                        'june': 6, 'jun': 6,
                        'july': 7, 'jul': 7,
                        'august': 8, 'aug': 8,
                        'september': 9, 'sep': 9, 'sept': 9,
                        'october': 10, 'oct': 10,
                        'november': 11, 'nov': 11,
                        'december': 12, 'dec': 12
                       }
        for m in months:
            try:
                m = int(m)
                if m not in num_months:
                    if m in all_months:
                        num_months.append(int(m))
                    else:
                        self.pr_e("%s's Cron Job configuration has an error. Month "
                                  "out of range: '%s'" % (self.plugname, m))
                continue
            except:
                pass
            n = translations.get(m.lower(),-1)
            if n == -1:
                self.pr_e("%s's Cron Job configuration has an error. Could not "
                          "understand month: '%s'" % (self.plugname, m))
            elif n not in num_months:
                num_months.append(n)
        num_months.sort()
        return num_months
        

    def get_now_timestamp(self):
        return datetime.datetime.timestamp(datetime.datetime.today()) # pragma: not covered

    def get_enabled_state(self):
        status_line = ''
        enabled_state = False
        try:
            status_file = open('/hoststorage/status/mode', 'r')
            status_line = status_file.readline().strip()
            status_file.close()
        except OSError as e:
            self.pr_e("Cron could not read the enabled/disabled state.")
        print("STATUS LINE = %s" % status_line)
        if status_line == 'enabled':
            enabled_state = True
        return enabled_state
        
    def get_next_hour(self):
        if self.get_enabled_state() == False:
            self.pr_e("Refusing to start any new cron jobs")
            return [] 
        nowTimestamp = self.get_now_timestamp() 
        self.today = self.get_today()
        next_hour = []
        byCronName = {}
        for cronName in self.cron_jobs:
            byCronName[cronName] = []
            cmd = self.cron_jobs[cronName].get("Command")
            if cmd in [None,'']:
                self.pr_e("In %s's Cron Job configuration the job '%s' has no "
                          "command" % (self.plugname, cronName))
                continue
            exec_on = self.cron_jobs[cronName].get("Execute On")
            if exec_on in [None,'']:
                self.pr_e("In %s's Cron Job configuration the job '%s' has no "
                          "scheduled executions" % (self.plugname, cronName))
                continue
            if not isinstance(exec_on, dict):
                epochs = self.make_close_epochs(exec_on)
                if epochs:
                    for epoch in epochs:
                        if epoch not in byCronName[cronName]:
                            if self.within_hour(epoch, nowTimestamp):
                                next_hour.append([epoch, cmd, False, cronName])
                                byCronName[cronName].append(epoch)
            else:
                for k in exec_on:
                    if k == 'DateTimes':
                        for dt in exec_on[k]:
                            epochs = self.make_close_epochs(dt)
                            if epochs:
                                for epoch in epochs:
                                    if epoch not in byCronName[cronName]:
                                        if self.within_hour(epoch, nowTimestamp):
                                            next_hour.append([epoch, cmd, False, cronName])
                                            byCronName[cronName].append(epoch)
                    elif k == "Yearly": 
                        months = exec_on[k].get('Months',['*'])
                        months = self.numbered_months(months)
                        days = exec_on[k].get('Days',['*']) 
                        ymds = self.get_filtered_dates(months, days)
                        if len(ymds) > 0:
                            hours = exec_on[k].get('Hours',[0])
                            minutes = exec_on[k].get('Minutes',[0])
                            seconds = exec_on[k].get('Seconds',[0])
                            all_seconds = self.get_ymd_seconds(ymds, hours, minutes, seconds)
                            epochs = self.make_timestamps(ymds, all_seconds)
                            if epochs:
                                for epoch in epochs:
                                    if epoch not in byCronName[cronName]:
                                        if self.within_hour(epoch, nowTimestamp):
                                            next_hour.append([epoch, cmd, False, cronName])
                                            byCronName[cronName].append(epoch)
        return next_hour

    def get_today(self): # pragma: not covered
        return datetime.datetime.today() # pragma: not covered

    def get_tomorrow(self): # pragma: not covered
        return self.today + datetime.timedelta(days=1) # pragma: not covered

    def get_close_hours(self, hours):
        possible_hours = [int(self.today.hour)]
        if int(self.today.hour) == 23:
            possible_hours.append(0)
        else:
            possible_hours.append(int(self.today.hour) + 1)
        final_hours = []
        for hour in hours:
            if '*' in str(hour):
                new_hours = self.handle_multiple(str(hour), 'hour')
                for n in new_hours:
                    n = int(n)
                    if n in possible_hours and n not in final_hours:
                        final_hours.append(n)
            else:
                try:
                    hour = int(hour)
                except:
                    self.pr_e("%s's Cron Job configuration has an error. "
                              "Could not understand hour: '%s'" % 
                                                  (self.plugname, hour))
                    continue
                if hour in possible_hours and hour not in final_hours:
                    final_hours.append(hour)
        return final_hours

    def get_all_subhrs(self, elements, timeType):
        final = []
        minimum = 0
        maximum = 59
        for m in elements:
            if '*' in str(m):
                new = self.handle_multiple(str(m), timeType)
                for nm in new:
                    nm = int(nm)
                    if nm not in final:
                        final.append(nm)
            else:
                try:
                    m = int(m)
                except:
                    self.pr_e("%s's Cron Job configuration has an error. "
                              "Could not understand %s: '%s'" % 
                                          (self.plugname, timeType, m))
                    continue
                m = int(m)
                if m >= minimum and m <= maximum:
                    if m not in final:
                        final.append(int(m))
        final.sort()
        return final


    def get_ymd_seconds(self, ymds, hours, minutes, seconds):
        hours = self.get_close_hours(hours)
        minutes = self.get_all_subhrs(minutes, 'minute')
        seconds = self.get_all_subhrs(seconds, 'second')
        timeStrs = self.make_hms(hours, minutes, seconds)
        return timeStrs
        

    def get_filtered_dates(self, months, days):
        translations = {
                        'monday': 0, 'mon': 0,
                        'tuesday': 1, 'tues': 1,
                        'wednesday': 2, 'wed': 2,
                        'thursday': 3, 'thur': 3,
                        'friday': 4, 'fri': 4,
                        'saturday': 5, 'sat': 5,
                        'sunday': 6, 'sun': 6
                       }
        all_days = False
        lom = False
        daybyname = [] 
        daybynum = []
        for d in days:
            res = translations.get(str(d).lower(),None)
            if res != None:
                if res not in daybyname:
                    daybyname.append(res)
            else:
                if str(d).lower() == 'lastofmonth':
                    lom = True
                elif d == '*':
                    all_days= True  
                else:
                    try:
                        nd = int(d)
                        if nd not in daybynum:
                            daybynum.append(nd)
                    except:
                        self.pr_e("%s's Cron Job configuration has an error. "
                                   "Could not understand day: '%s'" % 
                                   (self.plugname, d))
        year = self.today.year
        mo = int(self.today.month)
        tomorrow = self.get_tomorrow()
        tomo = int(tomorrow.month)
        ddm = self.ensure_double_digit(mo)
        d1 = self.ensure_double_digit(int(self.today.day))
        final_dates = []
        remaining = []
        if mo in months:
            remaining.append('%s-%s-%s' % (year, ddm, d1))
        if tomo != mo:
            if tomorrow.year != year and 1 in months:
                remaining.append('%s-01-01' % tomorrow.year)
            elif tomo in months:
                ddm = self.ensure_double_digit(tomo)
                remaining.append('%s-%s-01' % (year, ddm))
        elif tomo in months:
            d2 = self.ensure_double_digit(int(tomorrow.day))
            remaining.append('%s-%s-%s' % (year, ddm, d2))
        if all_days:
            return remaining 
        final = []
        for r in remaining:
            dobj = datetime.datetime.strptime(r, "%Y-%m-%d") 
            if int(dobj.weekday()) in daybyname:
                final.append(r)
            elif int(dobj.day) in daybynum:
                final.append(r) 
            elif lom:
                tobj = dobj + datetime.timedelta(days=1)
                if tobj.month != dobj.month:
                    final.append(r)
        return final

    def ensure_only_1_whitespace(self, dateStr):
        dateStr = dateStr.strip()
        while '  ' in dateStr:
            dateStr = dateStr.replace('  ',' ')
        dateStr = dateStr.replace(', ',',')
        dateStr = dateStr.replace(' ,',',')
        dateStr = dateStr.replace(': ',':')
        dateStr = dateStr.replace(' :',':')
        dateStr = dateStr.replace('- ','-')
        dateStr = dateStr.replace(' -','-')
        return dateStr

    def min_max_for_type(self, timeType):
        maximum = 59
        minimum = 0
        if timeType == 'hour':
            maximum = 23
            minimum = 0
        elif timeType == 'month':
            maximum = 12
            minimum = 1
        elif timeType == 'day':
            maximum = 31
            minimum = 1
        elif timeType == 'year':
            maximum = int(self.today.year) + 100
            minimum = int(self.today.year)
        return minimum, maximum

    def handle_multiple(self, timeStr, timeType):
        minimum, maximum = self.min_max_for_type(timeType)
        if '*' not in timeStr and ',' not in timeStr and '/' not in timeStr:
            try:
                timeStr = int(timeStr)
            except:
                self.pr_e("%s's Cron Job configuration has an error. In %s "
                          "field is a non-integer: '%s'" 
                           % (self.plugname, timeType, timeStr))
                return 'invalid'
            return [int(timeStr)]
        if ',' in timeStr:
            retTimes = []
            temp_times = timeStr.split(',')
            for t in temp_times:
                try:
                    t = int(t)
                except:
                    self.pr_e("%s's Cron Job configuration has an error. Comma"
                              "-separated values contains a non-integer: '%s'" 
                              % (self.plugname, timeStr)) 
                    return 'invalid'
                if t < minimum or t > maximum:
                    self.pr_e("%s's Cron Job configuration has an error. The "
                              "comma-separated list of numbers in datetime "
                              "string for %s contains a number that is out of "
                              "range: '%s'" % (self.plugname, timeType, timeStr)) 
                    return 'invalid'
                else:
                    retTimes.append(t)
            return retTimes
 
        repeater = 1
        if '/' in timeStr:
            repeater = timeStr.split('/')[1]
            if repeater in [None,'']:
                self.pr_e("%s's Cron Job configuration has an error. No "
                          "number follows the */ in '%s'" 
                          % (self.plugname, timeStr))
                return 'invalid'
            try:
                repeater = int(repeater)
                assert repeater > 1
            except:
                self.pr_e("%s's Cron Job configuration has an error. Element "
                          "that follows the */ in '%s' is not a number or is "
                          "less than 1" % (self.plugname, timeStr)) 
                return 'invalid'
            if timeType.lower() == 'year':
                baseYr = timeStr.split('/')[0]
                if baseYr == '*' and repeater > 1:
                    # Tell them this is not going to work the way they want - it will still execute every year
                    self.pr_e("%s's Cron Job configuration has a value which "
                              "could produce unexpected results. Using */"
                              "<number> format in a year field will cause the "
                              "cron job to be executed every year. Use format "
                              "'<yyyy>/<number> to ensure it only executes "
                              "every <number> years after the <yyyy> base year."
                              "You have: '%s'" %  (self.plugname, timeStr)) 
                else:
                    try:
                        baseYr = int(baseYr)
                        assert baseYr > 0
                        assert len(str(baseYr)) == 4
                    except:
                        self.pr_e("%s's Cron Job configuration has an error. "
                                  "Element that precedes the '/' in year field "
                                  "'%s' is not a valid number for 4-digit year" % 
                                                         (self.plugname, timeStr)) 
                        return 'invalid'
                
                    minimum = baseYr
                    
       
        printInvalid = False
        if timeType == 'year':
            if repeater > maximum - int(self.today.year):
                printInvalid = True
        elif repeater < minimum or repeater > maximum:
            printInvalid = True
        if printInvalid:
            self.pr_e("%s's Cron Job configuration has an error. The "
                      "'repeat-every' number in datetime string for %s is out "
                      "of range: '%s'" % (self.plugname, timeType, timeStr))
            return 'invalid'
        ctr = minimum
        retlist = []
        outOfBounds = False
        while not outOfBounds:
            if timeType.lower() != 'year' or ctr >= self.today.year:
                retlist.append(ctr)
            ctr+=repeater
            if ctr > maximum:
                outOfBounds = True
        return retlist
           

    def ensure_double_digit(self, timeStr):
        timeStr = str(timeStr)
        if len(timeStr) == 1:
            timeStr = '0%s' % timeStr
        return timeStr


    def make_hms(self, hours, minutes, seconds):
        timeStrs = []
        for hour in hours:
           hourStr = self.ensure_double_digit(hour)
           for minute in minutes:
               minStr = self.ensure_double_digit(minute)
               for second in seconds:
                   secStr = self.ensure_double_digit(second)
                   timeStrs.append('%s:%s:%s' % (hourStr, minStr, secStr)) 
        return timeStrs

    def make_timestamps(self, dates, timeStrs):
        timestamps = []
        for d in dates:
            for t in timeStrs:
               wholeStr = '%s %s' % (d, t)
               timestamp =  time.mktime(datetime.datetime.strptime(wholeStr, 
                                            "%Y-%m-%d %H:%M:%S").timetuple()) 
               timestamps.append(timestamp)
        return timestamps
        

    def make_close_epochs(self, dt):
        # Translate datetime to epoch
        # If year, month, day, hour, minute or second has * or */<number>, then it means allow all or allow every <number>
        if dt in [None,'']:
            return None
        dt = self.ensure_only_1_whitespace(dt.strip())
        split1 = dt.split(' ')
        dateStr = split1[0]
        hours = ['00']
        minutes = ['00']
        seconds = ['00']
        if len(split1) > 1:
            timeStr = split1[1]
            timesplit = timeStr.split(':')
            hours = '00'
            minutes = '00'
            seconds = '00'
            if len(timesplit) == 1:
                hours = timesplit[0]
            elif len(timesplit) == 2:
                hours = timesplit[0]
                minutes = timesplit[1]
            elif len(timesplit) == 3:
                hours = timesplit[0]
                minutes = timesplit[1]
                seconds = timesplit[2]
            hours = self.handle_multiple(hours, 'hour')
            minutes = self.handle_multiple(minutes, 'minute')
            seconds = self.handle_multiple(seconds, 'second')
            if 'invalid' in [hours, minutes, seconds]:
                self.pr_e("Ignoring invalid datetime in Cron Jobs "
                          "configuration for '%s': '%s'" % 
                                            (self.plugname, dt))
                return None

        years = []
        months = []
        days = []
        datesplit = dateStr.split('-')
        try:
            years = self.handle_multiple(datesplit[0], 'year')
            months = self.handle_multiple(datesplit[1], 'month')
            days = self.handle_multiple(datesplit[2], 'day')
            if 'invalid' in [years, months, days]:
                raise ValueError 
        except:
            self.pr_e("Ignoring invalid date in Cron Jobs configuration for "
                                       "'%s': '%s'" % (self.plugname, dt))
            return None
        years.sort()
        months.sort()
        days.sort()
        tomorrow = self.get_tomorrow()
        dates = []
        for year in years:
            if int(year) not in [int(self.today.year), int(tomorrow.year)]:
                break
            for month in months:
                if int(month) not in [int(self.today.month), int(tomorrow.month)]:
                    continue
                for day in days:
                    if int(day) not in [int(self.today.day), int(tomorrow.day)]:
                        continue
                    else:
                        dates.append('%s-%s-%s' % (year, month, day))
        timeStrs = self.make_hms(hours, minutes, seconds)
        timestamps = self.make_timestamps(dates, timeStrs)
        return timestamps

    def within_hour(self, epoch, nowTime):
        if epoch:
            calc = epoch - nowTime
            if calc <= 3600 and calc > 0:
                return True
        return False

    def get_crons(self):
        typical_job_label = 'CronJob'
        typical_job_ctr = 1
        out_cron = {}
        cron_cfg = self.conf.get(self.ckey, {})
        for k in cron_cfg:
            if k not in ['Command','Execute On']:
                # Then it is an arbitrary job name
                out_cron[k] = cron_cfg[k]
            else:
                label = '%s %s' % (typical_job_label, typical_job_ctr)
                if label not in out_cron:
                    out_cron[label] = {k: cron_cfg[k]}
                    typical_job_ctr+=1
                else:
                    out_cron[label][k] = cron_cfg[k]
        return out_cron
    
    def runIfOnLoad(self):
        onesToRun = []
        anyRan = False
        for k in self.cron_jobs:
            exec_on = {}
            cmd = None
            runNow = 'false'
            if k == "Execute On":
                exec_on = self.cron_jobs.get("Execute On",{})
                cmd = self.cron_jobs.get("Command", None)
                runNow = str(exec_on.get("Start", False))
            elif k != "Command":
                exec_on = self.cron_jobs[k].get("Execute On",{})
                cmd = self.cron_jobs[k].get("Command", None)
                runNow = str(exec_on.get("Start", False))
            else:
                continue
            if runNow.lower() == 'true':
                onesToRun.append([k, cmd])
        for onStartJob in onesToRun:
            assumedName = onStartJob[0]
            cmd = onStartJob[1]
            if cmd:
                job_id = str(self.new_job_id({'cai': k}))
                registered = self.register_job(job_id)
                self.pr_o("%s's Cron Job '%s' running immediately due to " 
                          "'Start' time configuration" 
                          % (self.plugname, assumedName))
                logger.info("Cron job %s's on-start command is '%s'" % (assumedName, cmd)) 
                RUNNING[job_id] = subprocess.Popen(shlex.split(cmd))
                anyRan = True
            else:
                self.pr_e("%s's Cron Job configuration has an error with '%s'. "
                          "A Job is supposed to start on load but there is "
                          "no associated 'Command'" 
                          % (self.plugname, assumedName))
        return anyRan
                    
    def new_job_id(self, req):
        # TODO - make this grab a job id from CN
        job_id = req.get('job_id')
        if not job_id:
            # TODO - fetch a new job id from CN -- CN registers the job in its job list
            job_id = random.randint(0, 100000) # DEBUG UNTIL TODO IMPLEMENTED
        return job_id

    def check_termination_requests(self, timeout=0.05):
        url = "http://localhost:5000/terminationrequests/"
        ctr = 0
        data = None
        while data == None:
            try:
                response = requests.post(url, json={'context': {}}, timeout=timeout)
                data = response.json()
            except:
                ctr+=1
                timeout = timeout * 2
            if ctr > 4:
                return {'ack': 'timeout'}
        return data.get('job_ids',[]) 
        
    def register_job(self, job_id, timeout=0.05):
        url = "http://localhost:5000/registercronjob/"
        body = {'job_id': job_id}
        ctr = 0
        data = None
        while data == None:
            try:
                response = requests.post(url, json=body, timeout=timeout)
                data = response.json()
            except:
                ctr+1
                timeout = timeout * 2
            if ctr > 4:
                return {'ack': 'timeout'}
        return data
        
    def register_termination(self, job_id):
        url = "http://localhost:5000/registercrontermination/"
        body = {'job_id': job_id}
        ctr = 0
        data = None
        while data is None:
            try:
                response = requests.post(url, json=body)
                data = response.json()
            except:
                ctr += 1
            if ctr > 4:
                return {'ack': 'timeout'}
        return data
        
    def check_job_statuses(self):
        kill_job_ids = []
        # TODO: Don't want to always do this check, do we?
        if (time.time() - self.checkTime) >= 2:
            kill_job_ids = self.check_termination_requests()
            self.checkTime = time.time()

        deads = []
        for job_id in RUNNING:
            stillgoing = False
            try:
                stillgoing = RUNNING[job_id].poll()
            except:
                self.pr_e("Could not get status for job with id '%s'" % job_id) 
            if stillgoing != None:
                deads.append(job_id)
            elif job_id in kill_job_ids:
                try:
                    RUNNING[job_id].terminate()
                    deads.append(job_id)
                except:
                    logger.error("Issues when terminating cron job subprocess:"
                                 " %s.\nTraceback: %s" % (job_id, 
                                 traceback.format_exc()))

        for job_id in deads:
            try:
                # Double-check whether it is really dead
                stillgoing = False
                try:
                    stillgoing = RUNNING[job_id].poll()
                except:
                    stillgoing = None
                    self.pr_e("Could not get status for job with id '%s'" 
                                                                % job_id) 
                if stillgoing != None:
                    del RUNNING[job_id]
                    rterm = self.register_termination(job_id)
                    if rterm.get('ack') == 'ok':
                        logger.info("Cron job %s has been terminated" % job_id)
                    else:
                        logger.error("Unsuccessful job termination of cron "
                                     "job %s" % job_id)
            except:
                logger.error("Unsuccessful job termination of cron job %s\n"
                             "Traceback: %s" % (job_id, traceback.format_exc()))


    def cron(self):
        nowTimestamp = self.get_now_timestamp()
        ctr = 0
        for timecmd in self.next_hour:
            if not timecmd[2]:
                if timecmd[0] <= nowTimestamp:
                    self.next_hour[ctr][2] = True
                    cronName = timecmd[3]
                    job_id = str(self.new_job_id({'cai': cronName}))
                    registered = self.register_job(job_id)
                    print("REGISTERED: %s" % registered)
                    RUNNING[job_id] = subprocess.Popen(shlex.split(timecmd[1]))
            ctr+=1
     
        self.check_job_statuses()
            
    def cfg_updated(self):
        atime, mtime = self.get_last_times(self.config_file) 
        if '0.0' not in [atime,mtime]:
            if mtime == self.last_mtime:
                return False
            else:
                self.last_mtime = mtime
                return True
        else:
            return False
            

def main(plugname, config_file):
    time.sleep(1) # Allow Flask time to start up
    cronRunner = CronRunner(plugname, cfg_file=config_file)
    ctr = 0
    startTime = time.time()
    while 1:
        loopStart = time.time()
        if time.time() - startTime >= 60:
            if cronRunner.cfg_updated():
                cronRunner.conf = parse_config(cronRunner.config_file)
            startTime = time.time()
            cronRunner.cron_jobs = cronRunner.get_crons()
            cronRunner.next_hour = cronRunner.get_next_hour()
        cronRunner.cron()
        time.sleep(.1)
        endDur = time.time() - loopStart
        ctr+=1

