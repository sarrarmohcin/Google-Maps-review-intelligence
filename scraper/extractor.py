from camoufox.async_api import AsyncCamoufox
import asyncio
import random
from datetime import datetime,timedelta,timezone
import dateparser
from scraper.parser import parse_reviews_response, relative_to_datetime
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from scraper.inference import ReviewAnalyzer
import json

class ReviewsExtractor:

    def __init__(self, business_id:str, url: str, language: str = "en", locale: str = "en-US", date_limit = 3):
        
        # Ensure keys are present before initializing
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        # verify if credentials are available
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        self.business_id = business_id
        self.url = url
        self.language = language
        self.locale = locale
        self.date_limit = date_limit
        self.info = None
        self.data = []
        
    async def main(self):
        # extract reviews
        await self.extract_reviews()
        
        # Remove items from self.data where review_text is empty or None
        self.data = [item for item in self.data if item.get("review_text")]
        
        # add the business name to each review
        self.data = [{**item, "business_id": self.business_id} for item in self.data]
        
        # update business info
        await self.update_info()
        
        # inference reviews
        inference = ReviewAnalyzer()
        for review in self.data:
            review_text = review.get("review_text", "")
            if review_text:
                inference_result = inference.inference(review_text)
                inference_data = {
                    "overall_sentiment": inference_result.get("overall_sentiment", ""),
                    "aspects": inference_result.get("aspects", []),
                    "main_complaint": inference_result.get("main_complaint", ""),
                    "summary": inference_result.get("summary", "")
                }
                
                review.update(inference_data)
        
        # store data to supabase
        await self.store_data()
        
    async def extract_info(self, page):
        # extratc rating
        rating_language = {
            'en' : 'stars',
            'fr' : 'étoiles'
        }
        
        review_language = {
            'en' : ['reviews', 'review'],
            'fr' : ['avis', 'avis']
        }
        
        rating = 0
        try:
            rating_div = page.locator(f'div[role="img"][aria-label*="{rating_language[self.language]}"]').first
            rating_text = await rating_div.get_attribute("aria-label")
            rating_text = rating_text.replace(rating_language[self.language], "").strip()
            rating = float(rating_text)
        except Exception as e:
            rating = 0
        

        # extract total reviews number
        reviews_number = 0
        try:
            reviews_number_div = await rating_div.evaluate_handle("el => el.nextElementSibling")
            reviews_number_text = ""
            if reviews_number_div:
                reviews_number_text = await reviews_number_div.text_content()
            
            reviews_number_text = reviews_number_text.replace(review_language[self.language][0], '').replace(review_language[self.language][1], '').strip()
            reviews_number = int(reviews_number_text)
        except Exception as e:
            reviews_number = 0
        
        return {
            "rating": rating,
            "reviews_number": reviews_number
        }
    
    async def update_info(self):
        try:
            response = (
                self.supabase.table("gm_places")
                .update({
                    "rating": self.info["rating"],
                    "reviews": self.info["reviews_number"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                .eq("id", self.business_id)
                .execute()
            )
            print(f"Updated business info: {response}")
        except Exception as e:
            print(f"Insert update: {e}")
                
                
    async def store_data(self):
        if not self.data:
            return

        for i, row in enumerate(self.data):

            try:
                response = self.supabase.table(
                    "gm_reviews"
                ).upsert(
                    row,
                    on_conflict="review_id"
                ).execute()

                print(f"Upserted row {i}: {response}")

            except Exception as e:
                print(f"Upsert error at row {i}: {e}")

    async def extract_reviews(self):
        async with AsyncCamoufox(
                humanize=True,
                headless=False,
                locale=self.locale,
            ) as browser:
            
            # visite page
            page = await browser.new_page()
            page.on("response", lambda response: self.handle_response(response))
            await page.goto(self.url)
            
            # wait for page loading
            await self.human_delay()
            
            # extract info
            info = await self.extract_info(page)
            self.info = info
                        
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
        
            
    async def handle_response(self, response):
        if "listugcposts" in response.url:
            content = await response.text()
            reviews = parse_reviews_response(content, self.language)
            self.data.extend([review.to_dict() for review in reviews])
        

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
                parsed_time = relative_to_datetime(date_str, self.language)
                if parsed_time<date_limit_rev:
                    break


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
    url=f"https://www.google.com/maps/place/Caf%C3%A9+Tranquille/@48.8782772,2.3564293,17z/data=!4m8!3m7!1s0x47e66f6d0b160aff:0x11073147c1c5f162!8m2!3d48.8782772!4d2.3564293!9m1!1b1!16s%2Fg%2F11ss88jt20?authuser=0&hl=en&entry=ttu&g_ep=EgoyMDI2MDUwNi4wIKXMDSoASAFQAw%3D%3D"
    extractor = ReviewsExtractor(1, url)
    asyncio.run(extractor.main())
    ''' 
    # For testing without running the scraper
    with open("scraper/data.json", "r") as file:
        data = json.load(file)
    extractor.data = data
    asyncio.run(extractor.store_data())
    '''
