#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging.handlers
import logging
import os
import sys

path = os.path.dirname(__file__)

logging.getLogger().setLevel(logging.NOTSET)
logging.captureWarnings(False)

# Silence scheduling messages
logging.getLogger("apscheduler.scheduler").setLevel(logging.ERROR)

console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("[{levelname:s}] {message:s}", style="{"))
logging.getLogger().addHandler(console)

if not os.path.exists(os.path.join(os.path.dirname(__file__), "res/logs/")):
    os.makedirs(os.path.join(os.path.dirname(__file__), "res/logs/"))
file = logging.handlers.RotatingFileHandler(filename=os.path.join(path, "res/logs/app.log"),
                                            maxBytes=1 << 20, backupCount=10)
file.setLevel(logging.DEBUG)
file.setFormatter(logging.Formatter("[{levelname:s}]({asctime:s} {name:s}) {message:s}", style="{"))
logging.getLogger().addHandler(file)

logger = logging.getLogger(__file__)
logger.info("Initialising program")

from apscheduler.schedulers.blocking import BlockingScheduler

from modules.organiser.organiser import Organiser


# Create an organiser and schedule it to update indefinitely
organiser = Organiser()
organiser.update()

scheduler = BlockingScheduler()
scheduler.add_job(organiser.update, trigger="cron", minute="*/15", hour="*", day="*", month="*", day_of_week="*")

try:
    scheduler.start()

except (KeyboardInterrupt, SystemExit) as cause:
    logger.exception(cause)

finally:
    scheduler.shutdown()
    logging.shutdown()
