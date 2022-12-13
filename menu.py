import scrapy
from scrapy.crawler import CrawlerProcess


class RecipeSpider(scrapy.Spider):
    name = 'recipe'
    custom_settings = {
        'DOWNLOD_DELAY': 0.5,
        'FEEDS': {
            'menu.csv': {
                'format': 'csv',
                'overwrite': True
            }
        },
    }
    allowed_domains = ['www.chinasichuanfood.com']
    start_urls = ['https://www.chinasichuanfood.com/recipe-index']
    links_scraped = []

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.crawl)

    def crawl(self, response):
        more_link = response.css('.entry-content p a ::attr(href)').extract()
        cat = response.css(
            '#wp-block-categories-1 > option.level-0 ::attr(value)').extract()
        cat_link = [f'https://www.chinasichuanfood.com/?cat={c}' for c in cat]
        links = list(set([*more_link, *cat_link]))
        for link in links:
            yield scrapy.Request(url=link, callback=self.get_recipe)

    def get_recipe(self, response):
        links = response.css('li.listing-item a ::attr(href)').extract()
        for link in list(set(links)):
            if link not in self.links_scraped:
                yield scrapy.Request(url=link, callback=self.parse_recipe)
                self.links_scraped.append(link)

    def parse_recipe(self, response):
        item = {}
        # name, category, and date modified
        recipe = response.css('.wprm-recipe-container')
        if len(recipe) != 0:
            item['Recipe Title'] = recipe.css('h2 ::text').get()
        else:
            item['Recipe Title'] = response.css('h1.entry-title ::text').get()
        item['Category'] = response.css('p#breadcrumbs a ::text')[-1].get()
        item['Date Modified'] = response.css(
            'time.entry-modified-time ::text').get()
        # rating and votes
        rating = recipe.css('.wprm-recipe-rating-details ::text').extract()
        if len(rating) == 4:
            item['Rating'] = float(rating[0])
            item['Votes'] = int(rating[2])
        # durations: preparation, cook, and total time
        durations = recipe.css('.wprm-recipe-time-container')
        for dur in durations:
            rdur = dur.css('span ::text').extract()
            item[rdur[0]] = ''.join(rdur[1:])
        # tags: course, cuisine, keywords
        tags = recipe.css('.wprm-recipe-tag-container')
        for tag in tags:
            rtag = tag.css('span ::text').extract()
            item[rtag[0]] = rtag[1] if len(rtag) == 2 else None
        # number of serving
        item['Servings'] = recipe.css('.wprm-recipe-servings ::text').get()
        # nutritions
        item['Calories'] = ' '.join(recipe.css(
            '.wprm-recipe-nutrition-with-unit span ::text').extract())
        # url
        item['URL'] = response.url
        yield item
        self.get_more_link(response)

    def get_more_link(self, response):
        more_recipe = response.css('h2 + div.feast-category-index')
        more_links = more_recipe.css(
            'li.listing-item a ::attr(href)').extract()
        links = []
        for link in more_links:
            if link not in self.links_scraped:
                links.append(link)
        for link in list(set(links)):
            if link not in self.links_scraped:
                yield scrapy.Request(url=link, callback=self.parse_recipe)
                self.links_scraped.append(link)

    def write_recipe(self, response):
        pass


if __name__ == '__main__':
    process = CrawlerProcess({
        'USER_AGENT': ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) '
                       'Gecko/20100101 Firefox/107.0')
    })
    process.crawl(RecipeSpider)
    process.start()
