from apscheduler.scheduler import Scheduler
from migrastorage import fileStorage

sched = Scheduler()

@sched.interval_schedule(minutes=1)
def cleanup_job():
    fileStorage().cleanup(3600) #delete everything over an hour old.

#@sched.cron_schedule(day_of_week='mon-fri', hour=17)
#def scheduled_job():
#    print 'This job is run every weekday at 5pm.'

sched.start()