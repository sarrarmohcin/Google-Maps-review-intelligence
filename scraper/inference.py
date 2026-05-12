from groq import Groq
from dotenv import load_dotenv
import os
import json


class ReviewAnalyzer:
    
    SYSTEM_PROMPT = """
        You are an NLP system specialized in restaurant and coffee shop review analysis.

        Your tasks:
        1. Detect overall sentiment.
        2. Extract mentioned aspects.
        3. Determine sentiment for each aspect.
        4. Identify the main complaint if any.
        5. Generate a short summary.

        Rules:
        - Return ONLY valid JSON.
        - Never explain reasoning.
        - Never output <think>.
        - Never output markdown.
        - Never output text before JSON.
        - Never output text after JSON.
        - Never omit fields.
        - If no complaint exists return: "main_complaint": null
        - If no summary exists return: "summary": null
        - If no overall_sentiment exists return: "overall_sentiment": neutral
        - If no aspects exists return: "aspects": []
        - Use lowercase labels.
        - Supported sentiments:
        - positive
        - negative
        - neutral

        Aspect examples:
        - coffee
        - service
        - wifi
        - ambiance
        - staff
        - cleanliness
        - pricing
        - food

        JSON schema:
        {
        "overall_sentiment": "positive",
        "aspects": [
            {
            "aspect": "service",
            "sentiment": "negative"
            }
        ],
        "main_complaint": "slow service",
        "summary": "Customers liked the coffee but disliked the slow service."
        }
    """

    def __init__(self):
        load_dotenv()
        grop_key = os.getenv("GROQ_KEY")

        self.client = Groq(
            api_key=grop_key,
        )
    
    def inference(self, review_text):
        
        USER_PROMPT = f"""
            Analyze this review:

            {review_text}
        """

        response = self.client.chat.completions.create(
            model="qwen/qwen3-32b",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": USER_PROMPT
                }
            ]
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        return data



if __name__ == "__main__":
    analyzer = ReviewAnalyzer()
    review_text = "The coffee was great but the service was terrible. I had to wait 20 minutes for my order and the staff was rude."
    result = analyzer.inference(review_text)
    print(json.dumps(result, indent=2))

