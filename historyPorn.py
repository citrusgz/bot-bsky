from atproto import Client
from atproto_client.models.app.bsky.embed.images import Image, Main as ImagesEmbed
import requests
from bs4 import BeautifulSoup
import os
import time
import json


with open('credentials.json', 'r') as f:
    credentials = json.load(f)
BLUESKY_USERNAME = credentials['username']
BLUESKY_PASSWORD = credentials['password']
LATEST_POST_FILE = 'latest_post.txt'

def get_latest_post():
    url = 'https://www.reddit.com/r/HistoryPorn/new/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch Reddit page. Status code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    post = soup.find('shreddit-post')
    while post and post.find_previous_sibling('shreddit-post'):
        post = post.find_previous_sibling('shreddit-post')
    if not post:
        print("No posts found on the page.")
        return None

    title_element = post.find('a', id=lambda x: x and 'post-title' in x)
    if not title_element:
        print("Failed to extract post title.")
        return None
    title = title_element.text.strip()

    post_url = post.get('permalink')
    if not post_url:
        print("Failed to extract post URL.")
        return None
    post_url = 'https://www.reddit.com' + post_url

    image_url = None
    image_element = post.find('img', id='post-image')
    if image_element and image_element.get('src'):
        image_url = image_element['src']

    return {
        'title': title,
        'url': post_url,
        'image_url': image_url
    }

def download_image(image_url):
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        temp_image_path = 'temp_image.jpg'
        with open(temp_image_path, 'wb') as f:
            f.write(response.content)
        return temp_image_path
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def upload_image_to_bluesky(client, image_path):
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        upload = client.upload_blob(image_data)
        return upload.blob
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

def read_latest_post_title():
    if os.path.exists(LATEST_POST_FILE):
        with open(LATEST_POST_FILE, 'r') as f:
            return f.read().strip()
    return None

def write_latest_post_title(title):
    with open(LATEST_POST_FILE, 'w') as f:
        f.write(title)

def main():
    while True:
        print("Fetching the latest post from /r/HistoryPorn...")
        post = get_latest_post()
        if not post:
            print("No posts found.")
            time.sleep(600)
            continue

        latest_title = read_latest_post_title()
        if post['title'] == latest_title:
            print("The latest post is the same as the previous one. Skipping.")
        else:
            print(f"New post found: {post['title']}")
            write_latest_post_title(post['title'])

            if post['image_url']:
                print("Downloading the image...")
                image_path = download_image(post['image_url'])
                if image_path:
                    print("Logging in to Bluesky...")
                    client = Client()
                    client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)

                    print("Uploading the image to Bluesky...")
                    image_blob = upload_image_to_bluesky(client, image_path)
                    if image_blob:
                        print("Creating the post on Bluesky...")
                        image_embed = ImagesEmbed(
                            images=[
                                Image(
                                    image=image_blob,
                                    alt="Image from /r/HistoryPorn"
                                )
                            ]
                        )
                        client.send_post(text=post['title'], embed=image_embed)
                        print("Post successfully created on Bluesky!")
                    else:
                        print("Failed to upload the image. Skipping.")
                else:
                    print("Failed to download the image. Skipping.")
            else:
                print("The post does not contain a valid image. Skipping.")

        time.sleep(600)

if __name__ == '__main__':
    main()
