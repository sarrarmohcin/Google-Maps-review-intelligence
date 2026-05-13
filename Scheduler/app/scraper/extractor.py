from camoufox.async_api import AsyncCamoufox
import asyncio
import random
from datetime import datetime,timedelta
from scraper.parser import parse_reviews_response, relative_to_datetime
#from scraper.inference import ReviewAnalyzer
from orm.connection import SessionLocal
from orm.models import Place
from producer.kafka_producer import KafkaProducerHandler
import os

class ReviewsExtractor:

    def __init__(self, business_id:str, url: str, language: str = "en", locale: str = "en-US", date_limit = 30):
        
        # databse session
        self.db = SessionLocal()
        
        # init kafka producer
        self.producer = KafkaProducerHandler()
        
        self.business_id = business_id
        self.url = url
        self.language = language
        self.locale = locale
        # day limit for reviews, default to 30 days
        self.date_limit = date_limit
        self.info = None
        self.data = []
        
        
    async def main(self):
        # extract reviews
        await self.extract_reviews()
        
        if not self.data:
            print("No reviews extracted.")
            return
        
        print(f"Extracted {len(self.data)} reviews.")
        
        # Remove items from self.data where review_text is empty or None
        self.data = [item for item in self.data if item.get("review_text")]
        
        # add the business name to each review
        self.data = [{**item, "business_id": self.business_id} for item in self.data]
        
        
        # update business info
        await self.update_info()

        # send data to kafka
        self.producer.send_message(
            topic="reviews",
            messages=self.data
        )
        
    
        
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
            
            place = (
                self.db.query(Place)
                .filter(Place.id == self.business_id)
                .first()
            )

            place.rating = self.info["rating"]
            place.reviews = self.info["reviews_number"]

            self.db.commit()

            print(f"Updated business info")
        except Exception as e:
            print(f"Insert update: {e}")
                

    async def extract_reviews(self):
        async with AsyncCamoufox(
                humanize=True,
                headless=False,
                locale=self.locale,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-gpu"
                ]
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
            
            await page.screenshot(path=f"screenshots/{self.business_id}_info.png", full_page=True)
            
            # 1. Récupérer l'intégralité du code HTML de la page
            html_content = await page.content()
            
            # Définir le dossier de stockage (ex: /app/storage)
            output_dir = "/app/storage"
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, f"place_{self.business_id}.html")
            
            # 2. Stocker le contenu dans un fichier HTML
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                        
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
            sort_btn = page.locator(f'button[data-value="{sort_language[language]}"]').has_text(f"{sort_language[language]}").first
            
            await sort_btn.wait_for(state="attached")
            
            await sort_btn.scroll_into_view_if_needed()
            
            # click on sort button
            await sort_btn.evaluate("button => button.click()")
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
