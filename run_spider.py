from scrapy.crawler import CrawlerProcess
from mlb_crawler.mlb_crawler.spiders.news import MlbSpider
from scrapy.utils.project import get_project_settings

process = CrawlerProcess(get_project_settings())
process.crawl(MlbSpider)
process.start()


# This script is designed to be ran as a cron job that will be executed every 12 hours
# 0 */12 * * * /usr/bin/python3 /path/to/run_spider.py >> /path/to/logfile.log 2>&1
