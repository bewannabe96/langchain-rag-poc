import base64
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import httpx
import requests
from bs4 import BeautifulSoup
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


class Summarizer:
    def __init__(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", (
                    "You will be generating description of place where your descript will be used for search.\n"
                    "You are encouraged to summarize images more than description provided.\n"
                    "\n"
                    "These are points you should focus specifically:\n"
                    "- type of the place (i.e. restaurant, cafe, bakery, bookstore, etc.)\n"
                    "- mood (i.e. cozy, modern, dark, etc.)\n"
                    "- location\n"
                    "- what the place offer"
                    "- what people can do"
                    "\n"
                    "Please follow the below restrictions:\n"
                    "- Always respond in English.\n"
                    "- Write in 100-200 words.\n"
                    "- Write in a descriptive rather than a suggestive tone.\n"
                )),
                ("user", (
                    "These are information of the place:\n"
                    "\n"
                    "[Name] {name}\n"
                    "[Type] {type}\n"
                    "[Region] {location}\n"
                    "\n"
                    "[Descriptions of Place Images]\n"
                    "{image_descriptions}\n"
                    "\n"
                    "[Description]\n"
                    "{description}\n"
                ))
            ]
        )

        self.llm = ChatOpenAI(model="gpt-4o")
        self.chain = prompt | self.llm

    def summarize_content(self, content_id: str, embed_image_count=None):
        crawl_data = self._crawl(content_id)

        encoded_images = []
        total_image_size = 0
        image_uris = crawl_data["image_uris"] if embed_image_count is None else crawl_data["image_uris"][:embed_image_count]
        for url in image_uris:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)

            query_params.update({'fmt': 'jpg', 'fit': 'outside', 'w': '512', 'h': '512'})

            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse(parsed_url._replace(query=new_query))

            image_data = base64.b64encode(httpx.get(new_url).content).decode("utf-8")
            total_image_size += len(image_data)

            encoded_images.append(image_data)

        image_descriptions = self._describe_image(encoded_images)

        response = self.chain.invoke({
            "name": crawl_data["name"],
            "type": crawl_data["type"],
            "location": crawl_data["location"],
            "image_descriptions": "\n".join([f"- {description}" for description in image_descriptions]),
            "description": crawl_data["description"],
        })

        return response.content

    def _crawl(self, content_id: str):
        response = requests.get(f'https://app.daytrip.io/ko/daylog/{content_id}')
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')

        name = soup.select_one('main > header > div > h1').text
        location, space_type = soup.select_one('main > header > div > p').text.split(' • ')
        description = '\n'.join([line for line in soup.select_one('main > section > p').strings])
        images_div = soup.select_one('main > header > div > div > div')
        image_uris = [img['src'] for img in images_div.find_all('img') if 'src' in img.attrs]

        return {
            "name": name,
            "type": space_type,
            "location": location,
            "image_uris": image_uris,
            "description": description,
        }

    def _describe_image(self, base64_encoded_images: list[str]):
        image_descriptions = []
        for encoded_image in base64_encoded_images:
            messages = [
                SystemMessage((
                    "You are an AI that generates descriptions for image.\n"
                    "Given a image, provide a brief description of what you see.\n"
                    "\n"
                    "Always respond in English."
                )),
                HumanMessage(content=[
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                ]),
            ]

            response = self.llm.invoke(messages)
            image_descriptions.append(response.content.replace("\n", ""))

        return image_descriptions
