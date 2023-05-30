import scrapy
from ..items import MlbNewsItem


class MlbSpider(scrapy.Spider):
    '''This spider will retrieve news articles for all teams across the MLB from mlb.com
       Output: The link of the article JSON format to temp.json
    '''

    name = 'mlb_news_spider'
    allowed_domains = ['mlb.com']

    custom_settings = {
        'FEED_FORMAT': 'json',
        'FEED_URI': 'mlb_news.json'
    }
    teams = ['whitesox', 'guardians', 'tigers', 'royals', 'twins' , 'cubs' , 'reds' , 'brewers' , 'pirates', \
     'cardinals', 'orioles', 'redsox', 'yankees', 'rays', 'bluejays', 'braves', 'marlins', 'mets', \
     'phillies', 'nationals', 'astros', 'angels', 'athletics', 'mariners', 'rangers', 'diamondbacks', \
     'rockies', 'dodgers', 'padres', 'giants']

    def start_requests(self):
        for team in self.teams:
            url = f'https://mlb.com/{team}/news'
            yield scrapy.Request(url=url, callback=self.parse, meta={'team': team})
    

    def parse(self, response):
        # Extract links to individual news articles
        for href in response.css('div.article-item__bottom a::attr(href)').getall():
            yield response.follow(href, self.parse_article, meta=response.meta)

    def parse_article(self, response):
        # Extract article data
        item = MlbNewsItem()
        item['team'] = response.meta['team']
        item['link'] = response.url
        item['headline'] = response.css('h1.Styles__HeadlineContainer-sc-19rm04l-0::text').get()
        item['date'] = response.xpath('//*[@id="root"]/main/article/header/div[1]/text()').get()
        item['content'] = ' '.join(response.xpath('//*[@id="root"]/main/article/section/div[*]/div/p/text()').getall())
        yield item
        