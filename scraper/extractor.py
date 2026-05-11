from camoufox.async_api import AsyncCamoufox
import asyncio
import random
from datetime import datetime,timedelta
import dateparser

class ReviewsExtractor:
    # ChIJoVAtgOxbwokRLSQFeYiJjOI
    def __init__(self, url: str, language: str = "en", locale: str = "en-US", date_limit = 3):
        self.url = url
        self.language = language
        self.locale = locale
        self.date_limit = date_limit

    async def extract_reviews(self):
        async with AsyncCamoufox(
                humanize=True,
                headless=False,
                locale=self.locale,
            ) as browser:
            
            # visite page
            page = await browser.new_page()
            await page.goto(self.url)
            
            # wait for page loading
            await self.human_delay()
            
            # click sort button
            sort_btn = await self.sort_reviews(page, language=self.language)
            if not sort_btn:
                return
            
            # click on recent button
            recent_btn = await self.recent_reviews(page, language=self.language)
            if not recent_btn:
                return
            
            # scroll reviews
            await self.review_scroll(page)
            print('Finished scrolling reviews.')
            
            # click on show more button for each review
            await self.click_show_more(page)
            print('Finished clicking show more buttons.')
            
            await asyncio.sleep(50000)
            

    async def sort_reviews(self, page, language):
        sort_language = {
            'en' : 'Sort',
            'fr' : 'Trier'
        }
        
        try:
            # get sort button
            sort_btn = page.locator(f'button[data-value="{sort_language[language]}"]').first
            if not sort_btn:
                raise Exception("sort button is None.")
            
            # click on sort button
            await sort_btn.click()
            await self.human_delay()
            
            return True
        except Exception as e:
            print(f"Failed to get sort button: {e}")
            return False
    
    async def recent_reviews(self, page, language):
        recent_language = {
            'en' : 'Newest',
            'fr' : 'Avis les plus récents'
        }
        
        try:
            # get recent button
            recent_btn = page.locator('div[role="menuitemradio"][data-index="1"]', has_text=recent_language[language]).first
            if not recent_btn:
                raise Exception("Recent button is None.")
            
            # click on sort button
            await recent_btn.click()
            await self.human_delay()
            
            return True
            
        except Exception as e:
            print(f"Failed to get recent button: {e}")
            return False
        
    def get_date_limit(self):
        now = datetime.now()
        # Subtract 24 hours
        minus_24h = now - timedelta(days=self.date_limit)
        # Convert to Unix timestamp
        timestamp_minus_24h = minus_24h.timestamp()

        return int(timestamp_minus_24h)
        
    async def review_scroll(self, page):
        
        # get the div to scroll the reviews
        scroll_rev_div = page.locator('div[role="main"] > :nth-child(2)').first
        
        # init params
        old_number_reviews = 0
        new_number_reviews = 0
        date_limit_rev = self.get_date_limit()
        exist_while = False

        # iterate until end of reviews
        while True:

            scroll_number = 0
            reviews_div = []

            # scroll while the number of reviews not changed
            while new_number_reviews == old_number_reviews:
                # scroll to bottom
                await self.human_scroll(page, scroll_rev_div)

                # get the number of reviews
                rev_div = page.locator('div[role="main"]').first
                reviews_div = await rev_div.locator('div[data-review-id][aria-label]').all()

                # update the new reviews number
                new_number_reviews = len(reviews_div)

                # if scroll 10 times without the number of reviews change, its the end
                if scroll_number > 10:
                    exist_while = True
                    break
            
            # update the old reviews number for next scrolls
            old_number_reviews = new_number_reviews

            # if no reviews exist end the while loop
            if exist_while == True:
                break
            
            # exist while loop if limit date reached
            if self.date_limit > 0:
                date_str = await reviews_div[-1].locator('span.rsqaWe').first.text_content()
                parsed_time = self.string_date_to_timestamp(date_str)
                if parsed_time<date_limit_rev:
                    break
    
    async def click_show_more(self, page):
        
        more_language = {
            'en' : 'See more',
            'fr' : 'Voir plus'
        }
        
        rev_div = page.locator('div[role="main"]').first
        reviews_div = await rev_div.locator('div[data-review-id][aria-label]').all()
        for review in reviews_div:
            try:
                plus_button = review.locator(f'button[data-review-id][aria-label="{more_language[self.language]}"]').first
                await plus_button.click(timeout=1000)
                await self.human_delay()
            except:
                pass

    def string_date_to_timestamp(self, date_str):
        parsed_time = dateparser.parse(date_str)
        return int(parsed_time.timestamp())
        
    async def human_delay(self, min_delay=2, max_delay=5):
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
        

    async def human_scroll(self, page, locator, scroll_amount = 5):
        box = await locator.bounding_box()

        if not box:
            return

        for _ in range(scroll_amount):


            if random.random() < 0.1:
                # Random mouse position INSIDE the div
                x = random.randint(
                    int(box["x"] + 10),
                    int(box["x"] + box["width"] - 10)
                )

                y = random.randint(
                    int(box["y"] + 10),
                    int(box["y"] + box["height"] - 10)
                )

                # Human-like mouse move
                await page.mouse.move(
                    x,
                    y,
                    steps=random.randint(3, 5)
                )

            # Random scroll amount
            scroll_amount = random.randint(200, 500)

            # Scroll inside div
            await locator.evaluate(
                "(el, amount) => el.scrollBy(0, amount)",
                scroll_amount
            )

            # Small chance to reverse scroll slightly
            if random.random() < 0.15:
                await locator.evaluate(
                    "(el, amount) => el.scrollBy(0, amount)",
                    -random.randint(30, 120)
                )

            # Pause like a human reading content
            await asyncio.sleep(random.uniform(0.5, 1.8))
                
if __name__ == "__main__":
    url=f"https://www.google.com/maps/place/Suited+NYC/@40.7093301,-74.0104175,17z/data=!4m8!3m7!1s0x89c25bec802d50a1:0xe28c89887905242d!8m2!3d40.7093261!4d-74.0078426!9m1!1b1!16s%2Fg%2F11fs2w9t1n?authuser=0&hl=en&entry=ttu&g_ep=EgoyMDI2MDUwNi4wIKXMDSoASAFQAw%3D%3D"
    extractor = ReviewsExtractor(url)
    asyncio.run(extractor.extract_reviews())